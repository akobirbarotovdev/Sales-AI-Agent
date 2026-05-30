import json
import os
from agents.base import BaseAgent
from config import settings
from utils.helpers import extract_json


PRODUCT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "product_config.json")


def _load_product() -> dict:
    try:
        with open(PRODUCT_CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {
            "product_name": "IT Maxsulot",
            "product_description": "Biznes yechim",
            "product_benefits": ["Samaradorlikni oshirish"],
            "company_name": "Kompaniya",
            "contact_email": "info@company.uz",
        }


PRODUCT = _load_product()


EMAIL_DRAFT_SYSTEM = f"""You are an Email Draft Agent. Create personalized sales emails for B2B leads in Uzbekistan.

Company info: {PRODUCT['company_name']}
Product: {PRODUCT['product_name']}
Description: {PRODUCT['product_description']}
Key benefits: {', '.join(PRODUCT.get('product_benefits', []))}
Website: {PRODUCT.get('website', '')}

Email MUST include:
1. 'Salom [Ism]' - personal greeting, no surname
2. Reference to their company and specific activity - proof of research
3. Specific problem/pain point identified during research
4. How {PRODUCT['product_name']} solves their specific problem (ONE clear solution)
5. Call to action: '15 daqiqalik qo'ng'iroqqa tayyormisiz?'

Email MUST NOT include:
- Generic compliments
- Product lists (only ONE solution)
- Pricing or discounts
- Long introductions

Tone: Professional, warm, direct. Uzbek market appropriate.

Output JSON:
{{
  "subject": "email subject line",
  "body": "full email body text"
}}
"""


class EmailDraftAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="email_draft",
            model=settings.haiku_model,
            timeout=settings.haiku_timeout,
        )

    def run(self, lead: dict) -> dict:
        research = lead.get("research_data", {})
        if isinstance(research, str):
            try:
                research = json.loads(research)
            except Exception:
                research = {}
        name = research.get("full_name", lead.get("contact_person", ""))
        company = lead.get("company_name", "")
        activity = research.get("company_activity", "")
        pain_point = research.get("pain_point", "")
        news = research.get("recent_news", "")

        prompt = f"""Create a personalized sales email in Uzbek language for:

Contact Person: {name or 'Unknown'}
Company: {company}
Activity: {activity or 'N/A'}
Pain Point: {pain_point or 'N/A'}
Recent News: {news or 'N/A'}
Industry: {lead.get('industry', 'N/A')}
Score: {lead.get('score', 0)}/100

Write about how {PRODUCT['product_name']} ({PRODUCT['product_description']}) can help them.
Keep under 150 words. Output JSON with 'subject' and 'body' keys."""

        result = self._call_llm(EMAIL_DRAFT_SYSTEM, prompt, max_tokens=1000)
        draft = extract_json(result)
        if not isinstance(draft, dict) or not draft.get("body"):
            product_name = PRODUCT['product_name']
            draft = {
                "subject": f"{product_name} — {company} uchun taklif",
                "body": f"Salom {name},\n\n{company} faoliyati haqida bilaman... "
                        f"Aynan sizga {product_name} mos keladi deb o'ylayman.\n\n"
                        f"15 daqiqalik qo'ng'iroqqa tayyormisiz?",
            }

        return {
            **lead,
            "email_subject": draft.get("subject", ""),
            "email_draft": draft.get("body", ""),
        }
