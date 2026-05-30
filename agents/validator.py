import json
from agents.base import BaseAgent
from config import settings
from scraping.http_scraper import check_website, fetch_html
from utils.helpers import extract_json


VALIDATOR_SYSTEM = """You are a Validator Agent. Your job is to validate lead contact information.

Check the following:
1. Email format - is it a valid, non-generic email? (NOT info@, contact@, admin@, support@)
2. Is the email likely personal/business? Should be name@company.uz type
3. Phone format - should start with +998
4. Website - is it reachable and working
5. Contact completeness - do we have enough info to contact?
6. Duplicate check - is this already in our database?

Output JSON:
{
  "validated": true/false,
  "validation_status": "passed" | "failed",
  "email_valid": true/false,
  "phone_valid": true/false,
  "website_working": true/false,
  "is_personal_email": true/false,
  "is_duplicate": false,
  "issues": ["list of issues"],
  "score_penalty": 0-15
}
"""


class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="validator",
            model=settings.haiku_model,
            timeout=settings.haiku_timeout,
        )

    async def run(self, lead: dict) -> dict:
        email = lead.get("email", "") or lead.get("research_data", {}).get("work_email", "")
        phone = lead.get("phone", "")
        website = lead.get("website", "")
        company = lead.get("company_name", "")

        website_working = False
        if website:
            website_working = await check_website(website)

        lead["website_working"] = website_working

        prompt = f"""Validate these contact details:

Company: {company}
Email: {email or 'Not provided'}
Phone: {phone or 'Not provided'}
Website: {website or 'Not provided'} (working: {website_working})
Contact Person: {lead.get('contact_person', '') or lead.get('research_data', {}).get('full_name', 'Not provided')}

Check:
1. Email is valid format and not generic (info@, contact@, admin@, support@ are INVALID)
2. Phone starts with +998
3. Website is working
4. Contact person name exists
5. Overall completeness
6. Duplicate detection

Output JSON as specified."""

        result = self._call_llm(VALIDATOR_SYSTEM, prompt, max_tokens=800)
        validation = extract_json(result)
        if not isinstance(validation, dict):
            validation = {
                "validated": False,
                "validation_status": "failed",
                "email_valid": bool(email),
                "phone_valid": bool(phone),
                "website_working": website_working,
                "is_personal_email": False,
                "is_duplicate": False,
                "issues": ["Validation parsing failed"],
                "score_penalty": 5,
            }

        # Deterministic guard: we only let a lead pass validation when its email
        # was actually scraped from the company site. AI-guessed addresses
        # ("ai_guess"/"none") never proceed to drafting/sending — mailing them
        # produces bounces and gets the sending domain blacklisted, which kills
        # every future campaign. This rule overrides whatever the LLM decided.
        email_source = lead.get("research_data", {}).get("email_source", "")
        if isinstance(lead.get("research_data"), str):
            try:
                email_source = json.loads(lead["research_data"]).get("email_source", "")
            except Exception:
                email_source = ""
        if not self.simulation and email_source != "scraped":
            validation["validation_status"] = "failed"
            validation["email_valid"] = False
            issues = validation.get("issues") or []
            issues.append("Email tasdiqlanmagan (saytdan topilmadi) — yuborish xavfli")
            validation["issues"] = issues

        score_penalty = validation.get("score_penalty", 0) if validation.get("validation_status") == "failed" else 0
        if not email:
            score_penalty = max(score_penalty, 5)

        current_score = lead.get("score", 0)
        lead["score"] = max(0, current_score - score_penalty)
        lead["validation_status"] = validation.get("validation_status", "failed")
        lead["validation_details"] = json.dumps(validation)

        if validation.get("validation_status") == "passed" and lead.get("status") == "approved":
            lead["status"] = "validated"

        return lead
