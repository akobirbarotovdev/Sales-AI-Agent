import asyncio
import random
from typing import Optional


BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

BROWSER_AVAILABLE = None


async def _check_browser():
    global BROWSER_AVAILABLE
    if BROWSER_AVAILABLE is not None:
        return BROWSER_AVAILABLE
    try:
        from playwright.async_api import async_playwright
        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            timeout=15000,
        )
        await browser.close()
        await p.stop()
        BROWSER_AVAILABLE = True
    except Exception:
        BROWSER_AVAILABLE = False
    return BROWSER_AVAILABLE


async def scrape_yellowpages(query: str, location: str = "Toshkent") -> list:
    if not await _check_browser():
        return []
    try:
        from playwright.async_api import async_playwright
        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
            timeout=10000,
        )
        context = await browser.new_context(
            user_agent=random.choice(BROWSER_USER_AGENTS),
            viewport={"width": random.randint(1280, 1440), "height": random.randint(720, 900)},
            locale="uz-UZ",
            timezone_id="Asia/Tashkent",
        )
        page = await context.new_page()
        search_url = f"https://yellowpages.uz/search/?q={query}&city={location}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(random.uniform(2000, 3000))
        companies = await page.query_selector_all(".company-item, .result-item, .card")
        results = []
        for company in companies[:10]:
            try:
                name_el = await company.query_selector("h3, .company-name, .title")
                phone_el = await company.query_selector(".phone, [class*=tel]")
                name = await name_el.inner_text() if name_el else ""
                phone = await phone_el.inner_text() if phone_el else ""
                results.append({"company_name": name.strip(), "phone": phone.strip(), "source": "yellowpages.uz"})
            except Exception:
                continue
        await browser.close()
        await p.stop()
        return results
    except Exception:
        return []


async def scrape_2gis(category: str, city: str = "Toshkent") -> list:
    if not await _check_browser():
        return []
    try:
        from playwright.async_api import async_playwright
        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
            timeout=10000,
        )
        context = await browser.new_context(
            user_agent=random.choice(BROWSER_USER_AGENTS),
            viewport={"width": random.randint(1280, 1440), "height": random.randint(720, 900)},
            locale="uz-UZ",
            timezone_id="Asia/Tashkent",
        )
        page = await context.new_page()
        search_url = f"https://2gis.uz/{city}/search/{category}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(random.uniform(2000, 3000))
        items = await page.query_selector_all(".mini-card__title, .search-snippet-view__title")
        results = []
        for item in items[:10]:
            try:
                name = await item.inner_text()
                results.append({"company_name": name.strip(), "source": "2gis.uz"})
            except Exception:
                continue
        await browser.close()
        await p.stop()
        return results
    except Exception:
        return []
