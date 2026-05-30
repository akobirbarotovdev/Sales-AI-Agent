import json
from agents.base import BaseAgent
from config import settings
from utils.helpers import extract_json


QUALIFICATION_SYSTEM = """You are a Qualification Agent. You evaluate leads using a 7-question scoring system (100 points total).

For each question, provide a score (0-100 for each sub-score), weight, and explanation.

SCORING CRITERIA:
1. Industry Relevance (20 points): How relevant is this company's industry to our product/service?
2. Company Size (15 points): Is the company big enough to need our solution but small enough to reach decision-makers?
3. Decision-Maker Access (20 points): Do we have the right contact person?
4. Engagement Potential (15 points): Is this company likely to engage with outbound sales?
5. Contact Quality (15 points): Quality of available contact information
6. Market Fit (10 points): How well does our solution fit their needs?
7. Urgency (5 points): Is there a timely reason to contact them now?

Total = sum of all scores (max 100).

Output JSON:
{
  "total_score": <0-100>,
  "score_breakdown": {
    "industry_relevance": {"score": 0, "weight": 20, "explanation": ""},
    "company_size": {"score": 0, "weight": 15, "explanation": ""},
    "decision_maker_access": {"score": 0, "weight": 20, "explanation": ""},
    "engagement_potential": {"score": 0, "weight": 15, "explanation": ""},
    "contact_quality": {"score": 0, "weight": 15, "explanation": ""},
    "market_fit": {"score": 0, "weight": 10, "explanation": ""},
    "urgency": {"score": 0, "weight": 5, "explanation": ""}
  },
  "recommendation": "high_priority" | "medium_priority" | "low_priority"
}
"""


class QualificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="qualification",
            model=settings.sonnet_model,
            timeout=settings.sonnet_timeout,
        )

    def run(self, lead: dict) -> dict:
        company = lead.get("company_name", "")
        industry = lead.get("industry", "")
        research = lead.get("research_data", {})
        contact_person = research.get("full_name", lead.get("contact_person", ""))
        email = research.get("work_email", lead.get("email", ""))

        prompt = f"""Evaluate this lead using the 7-question scoring system:

Company: {company}
Industry: {industry}
Contact Person: {contact_person or 'Unknown'}
Email: {email or 'Unknown'}
Location: {lead.get('location', 'Unknown')}
Source: {lead.get('source', 'Unknown')}

Research Data:
- Activity: {research.get('company_activity', 'N/A')}
- Pain Point: {research.get('pain_point', 'N/A')}
- News: {research.get('recent_news', 'N/A')}
- Competitors: {research.get('competitor_info', 'N/A')}

Score each criterion and provide detailed explanation.
Total score must be between 0-100."""

        result = self._call_llm(QUALIFICATION_SYSTEM, prompt, max_tokens=1000)
        parsed = extract_json(result)
        if not isinstance(parsed, dict):
            parsed = {"total_score": 50, "score_breakdown": {}, "recommendation": "medium_priority"}

        total = parsed.get("total_score", 0)
        if total >= 75:
            status = "approved"
        elif total >= 50:
            status = "zaxira"
        else:
            status = "rejected"

        return {
            **lead,
            "score": total,
            "score_breakdown": json.dumps(parsed.get("score_breakdown", {})),
            "status": status,
        }
