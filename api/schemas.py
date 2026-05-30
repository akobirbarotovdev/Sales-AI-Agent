from pydantic import BaseModel
from typing import Optional, List


class RunPipelineRequest(BaseModel):
    query: str
    industry: Optional[str] = None
    city: Optional[str] = None


class UpdateLeadRequest(BaseModel):
    email_edited: Optional[str] = None
    email_edited_subject: Optional[str] = None
    checked: Optional[int] = None
    status: Optional[str] = None


class SendEmailsRequest(BaseModel):
    lead_ids: List[int]


class LeadFilters(BaseModel):
    pipeline_id: Optional[int] = None
    status: Optional[str] = None
    min_score: int = 0
    max_score: int = 100
    industry: Optional[str] = None
    source: Optional[str] = None
    validation_status: Optional[str] = None
    search: Optional[str] = None
    limit: int = 100
    offset: int = 0
