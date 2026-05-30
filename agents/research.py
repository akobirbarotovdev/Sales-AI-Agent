import json
from agents.base import BaseAgent
from config import settings
from scraping.http_scraper import fetch_html, scrape_company_email
from utils.helpers import extract_json


RESEARCH_SYSTEM = """You are a Research Agent. Your job is to deeply research each lead and find:
1. Full name and position of the decision-maker (CEO, Director, etc.)
2. Work email (personal, not info@/contact@/admin@)
3. LinkedIn profile URL
4. Company's main activity (what they sell/service)
5. Recent news, growth signs, plans
6. Identified pain point or problem
7. Competitor existence and type

Be thorough and specific. Use the provided web data or generate realistic research based on available information.
Output as JSON."""


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="research",
            model=settings.haiku_model,
            timeout=settings.haiku_timeout,
        )

    async def run(self, lead: dict) -> dict:
        company = lead.get("company_name", "")
        website = lead.get("website", "")

        research = self._research_with_ai(company, website)

        # A real, scraped email always wins over an AI-guessed one. We only ever
        # send cold emails to addresses we actually found on the company site —
        # mailing AI-invented addresses just burns the sending domain.
        scraped_email = None
        if website:
            scraped_email = await scrape_company_email(website)

        if scraped_email:
            research["work_email"] = scraped_email
            research["email_source"] = "scraped"
        elif research.get("work_email"):
            research["email_source"] = "ai_guess"
        else:
            research["email_source"] = "none"

        return {
            **lead,
            "research_data": research,
            "source_primary": lead.get("source", "scraped"),
        }

    def _research_with_ai(self, company: str, website: str = "") -> dict:
        prompt = f"""Research this Uzbekistan company: "{company}"
Website: {website or 'Not available'}

Find all possible information about:
1. The CEO/Director/decision-maker's full name and position
2. Work email address (NOT info@, contact@, admin@ - must be personal)
3. LinkedIn profile of the decision-maker
4. What the company does (main products/services)
5. Recent news, achievements, or plans
6. Potential pain points or challenges they might face
7. Who their competitors are

Output as JSON with these keys:
- full_name: decision maker name
- position: job title
- work_email: email address
- linkedin_url: linkedin profile
- company_activity: what company does
- recent_news: news or achievements
- pain_point: identified problem
- competitor_info: competitors

Be specific and realistic for the Uzbek market context."""

        result = self._call_llm(RESEARCH_SYSTEM, prompt, max_tokens=1500)
        parsed = extract_json(result)
        if isinstance(parsed, dict):
            return parsed
        return {
            "full_name": "",
            "position": "",
            "work_email": "",
            "linkedin_url": "",
            "company_activity": "",
            "recent_news": "",
            "pain_point": "",
            "competitor_info": "",
        }
