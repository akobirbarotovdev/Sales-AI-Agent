from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LeadData(BaseModel):
    company_name: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    position: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    location: Optional[str] = None
    source: str = "manual"


class ResearchData(BaseModel):
    full_name: Optional[str] = None
    position: Optional[str] = None
    work_email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_activity: Optional[str] = None
    recent_news: Optional[str] = None
    pain_point: Optional[str] = None
    competitor_info: Optional[str] = None


class ScoreBreakdown(BaseModel):
    industry_relevance: dict = {}
    company_size: dict = {}
    decision_maker_access: dict = {}
    engagement_potential: dict = {}
    contact_quality: dict = {}
    market_fit: dict = {}
    urgency: dict = {}


class EmailDraft(BaseModel):
    subject: str
    body: str


class PipelineResponse(BaseModel):
    pipeline_id: int
    status: str
    message: str


class LeadResponse(BaseModel):
    id: int
    company_name: str
    email: Optional[str]
    contact_person: Optional[str]
    position: Optional[str]
    industry: Optional[str]
    score: int
    status: str
    validation_status: Optional[str]
    email_draft: Optional[str]
    email_subject: Optional[str]
    email_edited: Optional[str]
    checked: int
    source: Optional[str]
    website: Optional[str]
    created_at: str
