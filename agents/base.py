import time
import random
import json
from anthropic import Anthropic
from config import settings


SIMULATION_RESPONSES = {
    "supervisor": json.dumps({
        "decision": "continue",
        "next_agent": "auto",
        "reason": "simulation mode",
        "skip_leads": [],
    }),
    "lead_generation": json.dumps([
        {"company_name": "UzInfoCom", "industry": "IT", "location": "Toshkent", "source": "simulation"},
        {"company_name": "DigitalSoft", "industry": "IT", "location": "Toshkent", "source": "simulation"},
        {"company_name": "WebPark", "industry": "IT", "location": "Toshkent", "source": "simulation"},
        {"company_name": "ProSystem", "industry": "IT", "location": "Samarqand", "source": "simulation"},
        {"company_name": "DataStream", "industry": "Telekom", "location": "Toshkent", "source": "simulation"},
        {"company_name": "SmartBiz", "industry": "Konsalting", "location": "Toshkent", "source": "simulation"},
    ]),
    "research": json.dumps({
        "full_name": "Alisher Karimov",
        "position": "CEO",
        "work_email": "a.karimov@company.uz",
        "linkedin_url": "https://linkedin.com/in/alisher-karimov",
        "company_activity": "IT xizmatlar va dasturiy ta'minot",
        "recent_news": "Kompaniya 2025 yilda 40% o'sishga erishdi",
        "pain_point": "Raqamli marketing va mijozlar jalb qilishda qiyinchilik",
        "competitor_info": "Mahalliy IT kompaniyalari bilan raqobat",
    }),
    "qualification": json.dumps({
        "total_score": 82,
        "score_breakdown": {
            "industry_relevance": {"score": 18, "weight": 20, "explanation": "Yuqori darajada mos"},
            "company_size": {"score": 12, "weight": 15, "explanation": "O'rta kattalikdagi kompaniya"},
            "decision_maker_access": {"score": 17, "weight": 20, "explanation": "CEO bilan to'g'ridan-to'g'ri aloqa"},
            "engagement_potential": {"score": 12, "weight": 15, "explanation": "Faoliyati davomida hamkorlikka ochiq"},
            "contact_quality": {"score": 10, "weight": 15, "explanation": "Email mavjud"},
            "market_fit": {"score": 8, "weight": 10, "explanation": "Mahsulotga mos keladi"},
            "urgency": {"score": 5, "weight": 5, "explanation": "Tezda murojaat qilish kerak"},
        },
        "recommendation": "high_priority",
    }),
    "validator": json.dumps({
        "validated": True,
        "validation_status": "passed",
        "email_valid": True,
        "phone_valid": True,
        "website_working": True,
        "is_personal_email": True,
        "is_duplicate": False,
        "issues": [],
        "score_penalty": 0,
    }),
    "email_draft": json.dumps({
        "subject": "Hamkorlik taklifi: [Company] uchun yechim",
        "body": "Salom [Ism],\n\n[Company] faoliyati haqida bilaman...\n\nBizning yechimimiz sizga mos keladi deb o'ylayman.\n\n15 daqiqalik qo'ng'iroqqa tayyormisiz?",
    }),
}


class BaseAgent:
    def __init__(self, name: str, model: str, timeout: int = 60):
        self.name = name
        self.model = model
        self.timeout = timeout
        self.simulation = settings.simulation_mode
        if not self.simulation:
            self.client = Anthropic(
                api_key=settings.anthropic_api_key,
                max_retries=settings.max_retries,
            )

    def _call_llm(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        if self.simulation:
            sim_data = SIMULATION_RESPONSES.get(self.name, "{}")
            time.sleep(random.uniform(0.3, 0.8))
            return sim_data

        last_error = None
        for attempt in range(settings.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    timeout=self.timeout,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except Exception as e:
                last_error = e
                if "429" in str(e):
                    wait = (2 ** attempt) * 5 + random.uniform(0, 5)
                    time.sleep(wait)
                elif attempt < settings.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise last_error
        raise last_error or Exception("LLM call failed")
