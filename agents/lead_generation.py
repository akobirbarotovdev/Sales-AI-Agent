import json
import asyncio
import random
from agents.base import BaseAgent
from config import settings
from scraping.http_scraper import scrape_uzex, scrape_uztrade, tavily_search, check_soliq_uz
from scraping.playwright_scraper import scrape_yellowpages, scrape_2gis
from database import lead_exists
from utils.helpers import extract_json


UZBEK_COMPANIES = [
    {"company_name": "UZINFOCOM", "industry": "IT", "location": "Toshkent", "website": "https://uzinfocom.uz"},
    {"company_name": "DigitalSoft", "industry": "IT", "location": "Toshkent", "website": "https://digitalsoft.uz"},
    {"company_name": "WebPark", "industry": "IT", "location": "Toshkent", "website": "https://webpark.uz"},
    {"company_name": "ProSystem Technology", "industry": "IT", "location": "Samarqand", "website": "https://prosystem.uz"},
    {"company_name": "DataStream", "industry": "Telekom", "location": "Toshkent", "website": "https://datastream.uz"},
    {"company_name": "Smart Consulting", "industry": "Konsalting", "location": "Toshkent"},
    {"company_name": "GreenTech Solutions", "industry": "Qishloq xo'jaligi", "location": "Toshkent"},
    {"company_name": "BuildPro", "industry": "Qurilish", "location": "Toshkent"},
    {"company_name": "TradeMaster", "industry": "Savdo", "location": "Toshkent"},
    {"company_name": "LogisticPro", "industry": "Logistika", "location": "Toshkent"},
    {"company_name": "EduSoft", "industry": "Ta'lim", "location": "Toshkent"},
    {"company_name": "MedTech", "industry": "Tibbiyot", "location": "Toshkent"},
]

LEAD_GEN_SYSTEM = """You are a Lead Generation Agent. Your job is to find potential B2B leads in Uzbekistan.
Given a search query, generate realistic potential leads with company names, industries, and possible contact info.

For each lead, provide:
- company_name: Full company name
- industry: Business sector
- location: City/region
- website: Company website URL (if known)
- source: Where this lead might be found

Output as JSON array of lead objects only, no other text.
"""


class LeadGenerationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="lead_generation",
            model=settings.haiku_model,
            timeout=settings.haiku_timeout,
        )

    async def run(self, query: str) -> list:
        all_leads = []

        scraping_tasks = [
            self._scrape_yellowpages(query),
            self._scrape_2gis(query),
            scrape_uzex(),
            scrape_uztrade(),
            self._tavily_search_leads(query),
        ]

        scraping_results = await asyncio.gather(*scraping_tasks, return_exceptions=True)

        for result in scraping_results:
            if isinstance(result, list):
                all_leads.extend(result)

        ai_leads = self._generate_ai_leads(query)
        all_leads.extend(ai_leads)

        if not all_leads:
            all_leads = self._fallback_leads(query)

        seen = set()
        unique_leads = []
        for lead in all_leads:
            key = lead.get("company_name", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                if not lead_exists(company=lead.get("company_name", "")):
                    unique_leads.append(lead)

        return unique_leads[:30]

    async def _scrape_yellowpages(self, query: str) -> list:
        try:
            return await scrape_yellowpages(query)
        except Exception:
            return []

    async def _scrape_2gis(self, query: str) -> list:
        try:
            return await scrape_2gis(query)
        except Exception:
            return []

    async def _tavily_search_leads(self, query: str) -> list:
        if not settings.tavily_api_key:
            return []
        leads = []
        search_queries = [
            f"O'zbekiston {query} kompaniyalar 2025 2026",
            f"Uzbekistan {query} companies CEO contact",
            f"Тошкент {query} компаниялари раҳбарлари",
        ]
        for sq in search_queries:
            results = await tavily_search(sq, settings.tavily_api_key, max_results=3)
            for r in results:
                title = r.get("title", "")
                url = r.get("url", "")
                if title and "kompaniya" in title.lower() or "company" in title.lower() or "MChJ" in title:
                    leads.append({
                        "company_name": title.split(" — ")[0].split(" - ")[0].strip()[:100],
                        "website": url,
                        "source": "tavily",
                        "industry": query,
                        "location": "Toshkent",
                    })
            await asyncio.sleep(random.uniform(0.5, 1.5))
        return leads

    def _generate_ai_leads(self, query: str) -> list:
        if settings.simulation_mode:
            return self._simulate_leads(query)

        prompt = f"""Generate a list of up to 10 realistic B2B companies in Uzbekistan that match this search: "{query}"

For each company, provide: company_name, industry, location, website.
Focus on real, well-known Uzbek companies when possible.
Output as JSON array only."""

        result = self._call_llm(LEAD_GEN_SYSTEM, prompt, max_tokens=2000)
        leads = extract_json(result, expect_list=True)
        if not isinstance(leads, list):
            return self._simulate_leads(query)
        for lead in leads:
            lead["source"] = lead.get("source", "ai_generated")
        return leads

    def _simulate_leads(self, query: str) -> list:
        query_lower = query.lower()
        matched = []
        for c in UZBEK_COMPANIES:
            if query_lower in c["industry"].lower() or query_lower in c["company_name"].lower():
                matched.append({**c, "source": "simulation"})
        if not matched:
            matched = UZBEK_COMPANIES[:6]
        return [{**m, "source": "simulation"} for m in matched]

    def _fallback_leads(self, query: str) -> list:
        return [
            {"company_name": f"{query.title()} MChJ", "industry": query, "location": "Toshkent", "source": "fallback"},
            {"company_name": f"{query.title()} Service", "industry": query, "location": "Toshkent", "source": "fallback"},
            {"company_name": f"Global {query.title()}", "industry": query, "location": "Toshkent", "source": "fallback"},
        ]
