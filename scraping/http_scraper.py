import httpx
from bs4 import BeautifulSoup
from typing import Optional
from fake_useragent import UserAgent


ua = UserAgent()

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en;q=0.7",
}


async def fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    headers = {**HEADERS, "User-Agent": ua.random}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


async def fetch_json(url: str, timeout: int = 15) -> Optional[dict]:
    headers = {**HEADERS, "User-Agent": ua.random, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


async def scrape_uzex() -> list:
    results = []
    html = await fetch_html("https://uzex.uz/ru/companies")
    if not html:
        return results
    soup = BeautifulSoup(html, "lxml")
    for item in soup.select(".company-item, .card, .company-row")[:20]:
        name_el = item.select_one("h3, .name, .title")
        if name_el:
            results.append({
                "company_name": name_el.get_text(strip=True),
                "source": "uzex.uz",
            })
    return results


async def scrape_uztrade() -> list:
    results = []
    html = await fetch_html("https://uztrade.uz/companies")
    if not html:
        return results
    soup = BeautifulSoup(html, "lxml")
    for item in soup.select(".company-item, .card, .org-card")[:20]:
        name_el = item.select_one("h3, .name, .title")
        if name_el:
            results.append({
                "company_name": name_el.get_text(strip=True),
                "source": "uztrade.uz",
            })
    return results


async def check_soliq_uz(tin: str = "") -> Optional[dict]:
    html = await fetch_html(f"https://my.soliq.uz/ru/search?tin={tin}", timeout=10)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    name_el = soup.select_one(".company-name, .org-name, h3")
    if name_el:
        return {
            "verified": True,
            "company_name": name_el.get_text(strip=True),
            "source": "soliq.uz",
        }
    return {"verified": False, "source": "soliq.uz"}


async def tavily_search(query: str, api_key: str, max_results: int = 5) -> list:
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
    except Exception:
        pass
    return []


async def check_website(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            return resp.status_code < 500
    except Exception:
        return False


async def scrape_company_email(company_url: str) -> Optional[str]:
    html = await fetch_html(company_url, timeout=15)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select("a[href^='mailto:']"):
        return a["href"].replace("mailto:", "").strip()
    text = soup.get_text()
    import re
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    for e in emails:
        if not e.startswith(("info@", "contact@", "admin@", "support@")):
            return e
    return None
