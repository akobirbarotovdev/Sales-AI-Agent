from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import io
from datetime import datetime

from api.schemas import RunPipelineRequest, UpdateLeadRequest, SendEmailsRequest, LeadFilters
from database import (
    get_dashboard_stats,
    get_leads,
    get_lead_by_id,
    update_lead,
    get_distinct_industries,
    get_distinct_sources,
    get_pipeline_stats,
    count_leads,
    create_pipeline,
    update_pipeline,
    init_db,
)
from pipeline.graph import SalesGraph
from excel_export import export_leads_to_excel
from email_sender import send_email
from product_config import get_product_info

router = APIRouter()
pipeline_runner = SalesGraph()

# Keep strong references to running pipeline tasks so the event loop doesn't
# garbage-collect them mid-run.
_running_tasks: set = set()


async def _run_pipeline_bg(query: str, pipeline_id: int):
    try:
        await pipeline_runner.run(query, pipeline_id=pipeline_id)
    except Exception as e:
        update_pipeline(pipeline_id, status="error", error=str(e))


@router.get("/api/product-info")
async def product_info():
    return get_product_info()


@router.get("/api/init")
async def initialize():
    init_db()
    return {"status": "ok"}


@router.post("/api/pipeline/run")
async def run_pipeline(req: RunPipelineRequest):
    try:
        # Create the row up front so we can return its id immediately, then run
        # the (multi-minute) pipeline in the background. The dashboard polls
        # /api/pipeline/latest for completion.
        pipeline_id = create_pipeline(req.query)
        task = asyncio.create_task(_run_pipeline_bg(req.query, pipeline_id))
        _running_tasks.add(task)
        task.add_done_callback(_running_tasks.discard)
        return {"pipeline_id": pipeline_id, "status": "running", "message": "Pipeline started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: int):
    stats = get_pipeline_stats(pipeline_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return stats


@router.get("/api/pipeline/latest")
async def get_latest_pipeline():
    stats = get_pipeline_stats()
    return stats


@router.get("/api/leads")
async def list_leads(
    pipeline_id: int = None,
    status: str = None,
    min_score: int = 0,
    max_score: int = 100,
    industry: str = None,
    source: str = None,
    validation_status: str = None,
    search: str = None,
    limit: int = 100,
    offset: int = 0,
):
    leads = get_leads(
        pipeline_id=pipeline_id,
        status=status,
        min_score=min_score,
        max_score=max_score,
        industry=industry,
        source=source,
        validation_status=validation_status,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = count_leads()
    return {"leads": leads, "total": total, "limit": limit, "offset": offset}


@router.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int):
    lead = get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/api/leads/{lead_id}")
async def update_lead_endpoint(lead_id: int, req: UpdateLeadRequest):
    lead = get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    updates = req.model_dump(exclude_unset=True)
    if updates:
        update_lead(lead_id, **updates)
    return get_lead_by_id(lead_id)


@router.post("/api/leads/batch-check")
async def batch_check_leads(data: dict):
    lead_ids = data.get("lead_ids", [])
    checked = data.get("checked", 1)
    for lid in lead_ids:
        update_lead(lid, checked=checked)
    return {"status": "ok", "updated": len(lead_ids)}


@router.get("/api/stats")
async def dashboard_stats():
    return get_dashboard_stats()


@router.get("/api/filters/industries")
async def industries():
    return {"industries": get_distinct_industries()}


@router.get("/api/filters/sources")
async def sources():
    return {"sources": get_distinct_sources()}


@router.post("/api/send")
async def send_emails(req: SendEmailsRequest):
    sent = []
    errors = []
    for lead_id in req.lead_ids:
        lead = get_lead_by_id(lead_id)
        if not lead:
            errors.append({"lead_id": lead_id, "error": "Not found"})
            continue
        email_body = lead.get("email_edited") or lead.get("email_draft")
        email_subject = lead.get("email_edited_subject") or lead.get("email_subject", "Taklif")
        recipient_email = lead.get("email", "")
        if not email_body:
            errors.append({"lead_id": lead_id, "error": "No email draft"})
            continue
        if not recipient_email:
            errors.append({"lead_id": lead_id, "error": "No recipient email"})
            continue

        smtp_sent = send_email(recipient_email, email_subject, email_body)
        if smtp_sent:
            update_lead(lead_id, status="sent", sent_at=datetime.utcnow().isoformat(), send_error=None)
            sent.append(lead_id)
        else:
            # Do NOT mark as sent when SMTP fails — that hides bounces and makes
            # the dashboard lie about what actually went out.
            update_lead(lead_id, send_error="SMTP failed or not configured")
            errors.append({"lead_id": lead_id, "error": "SMTP failed or not configured"})

    return {"sent": sent, "errors": errors, "total_sent": len(sent), "total_errors": len(errors)}


@router.get("/api/export/excel")
async def export_excel(
    pipeline_id: int = None,
    status: str = None,
    min_score: int = 0,
    max_score: int = 100,
):
    leads = get_leads(
        pipeline_id=pipeline_id,
        status=status,
        min_score=min_score,
        max_score=max_score,
        limit=5000,
    )
    output = io.BytesIO()
    export_leads_to_excel(leads, output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=leads_export.xlsx"},
    )
