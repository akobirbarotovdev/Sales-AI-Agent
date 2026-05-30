import asyncio
import json
import time
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from pipeline.state import PipelineState
from agents.supervisor import SupervisorAgent
from agents.lead_generation import LeadGenerationAgent
from agents.research import ResearchAgent
from agents.qualification import QualificationAgent
from agents.validator import ValidatorAgent
from agents.email_draft import EmailDraftAgent
from database import create_pipeline, update_pipeline, insert_lead, update_lead
from utils.helpers import now_iso


class SalesGraph:
    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.lead_gen = LeadGenerationAgent()
        self.research = ResearchAgent()
        self.qualification = QualificationAgent()
        self.validator = ValidatorAgent()
        self.email_draft = EmailDraftAgent()
        self.graph = None
        self._build_graph()

    def _build_graph(self):
        builder = StateGraph(PipelineState)

        builder.add_node("supervisor", self._supervisor_node)
        builder.add_node("lead_generation", self._lead_gen_node)
        builder.add_node("research", self._research_node)
        builder.add_node("qualification", self._qualification_node)
        builder.add_node("validation", self._validation_node)
        builder.add_node("email_draft", self._email_draft_node)
        builder.add_node("finish", self._finish_node)

        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges(
            "supervisor",
            self._router,
            {
                "lead_generation": "lead_generation",
                "research": "research",
                "qualification": "qualification",
                "validation": "validation",
                "email_draft": "email_draft",
                "complete": "finish",
                "error": "finish",
            },
        )
        builder.add_edge("lead_generation", "supervisor")
        builder.add_edge("research", "supervisor")
        builder.add_edge("qualification", "supervisor")
        builder.add_edge("validation", "supervisor")
        builder.add_edge("email_draft", "supervisor")
        builder.add_edge("finish", END)

        memory = MemorySaver()
        self.graph = builder.compile(checkpointer=memory)

    def _router(self, state: PipelineState) -> Literal["lead_generation", "research", "qualification", "validation", "email_draft", "complete", "error"]:
        decision = self.supervisor.delegate(state)
        next_agent = decision.get("next_agent", "complete")

        if decision.get("decision") == "complete" or next_agent == "none":
            return "complete"
        if decision.get("decision") == "error":
            return "error"

        if next_agent == "lead_generation" and not state.get("lead_gen_done"):
            return "lead_generation"
        if next_agent == "research" and not state.get("research_done"):
            return "research"
        if next_agent == "qualification" and not state.get("qualification_done"):
            return "qualification"
        if next_agent == "validation" and not state.get("validation_done"):
            return "validation"
        if next_agent == "email_draft" and not state.get("email_draft_done"):
            return "email_draft"

        return "complete"

    async def _supervisor_node(self, state: PipelineState) -> dict:
        return {"messages": [AIMessage(content=f"Supervisor routing from phase: {state.get('phase', 'start')}")]}

    async def _lead_gen_node(self, state: PipelineState) -> dict:
        try:
            leads = await self.lead_gen.run(state["query"])
            lead_ids = []
            for lead in leads:
                lid = insert_lead(state["pipeline_id"], {
                    "pipeline_id": state["pipeline_id"],
                    "company_name": lead.get("company_name", ""),
                    "website": lead.get("website", ""),
                    "phone": lead.get("phone", ""),
                    "email": lead.get("email", ""),
                    "industry": lead.get("industry", ""),
                    "location": lead.get("location", ""),
                    "source": lead.get("source", "scraped"),
                    "source_primary": lead.get("source", "scraped"),
                    "status": "pending",
                })
                lead_ids.append(lid)
            update_pipeline(state["pipeline_id"], total_leads=len(leads))
            return {"leads": leads, "lead_ids": lead_ids, "lead_gen_done": True, "phase": "lead_generation",
                    "messages": [AIMessage(content=f"Lead gen complete: {len(leads)} leads found")]}
        except Exception as e:
            return {"errors": state.get("errors", []) + [f"lead_gen: {str(e)}"],
                    "lead_gen_done": True,
                    "messages": [AIMessage(content=f"Lead gen error: {str(e)}")]}

    async def _research_node(self, state: PipelineState) -> dict:
        errors = list(state.get("errors", []))
        leads = list(state.get("leads", []))
        lead_ids = state.get("lead_ids", [])
        for i, lead in enumerate(leads):
            try:
                if i < len(lead_ids):
                    lead_id = lead_ids[i]
                    researched = await self.research.run(lead)
                    leads[i] = researched
                    rd = researched.get("research_data", {})
                    update_lead(lead_id,
                        contact_person=rd.get("full_name", ""),
                        position=rd.get("position", ""),
                        email=rd.get("work_email", ""),
                        research_data=json.dumps(rd),
                        status="research_complete",
                    )
            except Exception as e:
                errors.append(f"research[{i}]: {str(e)}")
        return {"leads": leads, "research_done": True, "phase": "research",
                "errors": errors,
                "messages": [AIMessage(content=f"Research complete for {len(leads)} leads")]}

    async def _qualification_node(self, state: PipelineState) -> dict:
        errors = list(state.get("errors", []))
        leads = list(state.get("leads", []))
        lead_ids = state.get("lead_ids", [])
        for i, lead in enumerate(leads):
            try:
                if i < len(lead_ids):
                    lead_id = lead_ids[i]
                    qualified = self.qualification.run(lead)
                    leads[i] = qualified
                    update_lead(lead_id,
                        score=qualified.get("score", 0),
                        score_breakdown=qualified.get("score_breakdown", "{}"),
                        status=qualified.get("status", "approved"),
                    )
            except Exception as e:
                errors.append(f"qualification[{i}]: {str(e)}")
        return {"leads": leads, "qualification_done": True, "phase": "qualification",
                "errors": errors,
                "messages": [AIMessage(content=f"Qualification complete")]}

    async def _validation_node(self, state: PipelineState) -> dict:
        errors = list(state.get("errors", []))
        leads = list(state.get("leads", []))
        lead_ids = state.get("lead_ids", [])
        for i, lead in enumerate(leads):
            try:
                if i < len(lead_ids) and lead.get("status") in ("approved", "validated"):
                    lead_id = lead_ids[i]
                    validated = await self.validator.run(lead)
                    leads[i] = validated
                    update_lead(lead_id,
                        score=validated.get("score", 0),
                        validation_status=validated.get("validation_status", "failed"),
                        validation_details=validated.get("validation_details", "{}"),
                        status=validated.get("status", "validated"),
                    )
            except Exception as e:
                errors.append(f"validation[{i}]: {str(e)}")
        return {"leads": leads, "validation_done": True, "phase": "validation",
                "errors": errors,
                "messages": [AIMessage(content=f"Validation complete")]}

    async def _email_draft_node(self, state: PipelineState) -> dict:
        errors = list(state.get("errors", []))
        leads = list(state.get("leads", []))
        lead_ids = state.get("lead_ids", [])
        for i, lead in enumerate(leads):
            try:
                if i < len(lead_ids) and lead.get("validation_status") == "passed":
                    lead_id = lead_ids[i]
                    drafted = self.email_draft.run(lead)
                    leads[i] = drafted
                    update_lead(lead_id,
                        email_subject=drafted.get("email_subject", ""),
                        email_draft=drafted.get("email_draft", ""),
                        status="email_draft_ready",
                    )
            except Exception as e:
                errors.append(f"email_draft[{i}]: {str(e)}")
        return {"leads": leads, "email_draft_done": True, "phase": "email_draft",
                "errors": errors,
                "messages": [AIMessage(content=f"Email draft complete")]}

    async def _finish_node(self, state: PipelineState) -> dict:
        total = len(state.get("leads", []))
        leads = state.get("leads", [])
        researched = sum(1 for l in leads if l.get("research_data"))
        qualified = sum(1 for l in leads if l.get("score", 0) >= 75)
        validated = sum(1 for l in leads if l.get("validation_status") == "passed")
        has_errors = len(state.get("errors", [])) > 0
        final_status = "error" if has_errors else "finished"
        update_pipeline(
            state["pipeline_id"],
            status=final_status,
            total_leads=total,
            researched=researched,
            qualified=qualified,
            validated=validated,
            finished_at=now_iso(),
        )
        return {"phase": "complete",
                "messages": [AIMessage(content=f"Pipeline finished. Total: {total}, Errors: {len(state.get('errors', []))}")]}

    async def run(self, query: str, pipeline_id: int = None) -> int:
        if pipeline_id is None:
            pipeline_id = create_pipeline(query)
        start_time = time.time()

        initial_state: PipelineState = {
            "pipeline_id": pipeline_id,
            "query": query,
            "phase": "start",
            "leads": [],
            "lead_ids": [],
            "errors": [],
            "lead_gen_done": False,
            "research_done": False,
            "qualification_done": False,
            "validation_done": False,
            "email_draft_done": False,
            "start_time": now_iso(),
            "current_lead_index": 0,
            "messages": [HumanMessage(content=f"Start pipeline: {query}")],
        }

        config = {"configurable": {"thread_id": str(pipeline_id)}}
        try:
            await self.graph.ainvoke(initial_state, config)
        except Exception as e:
            duration = time.time() - start_time
            update_pipeline(pipeline_id, status="error", finished_at=now_iso(), duration_seconds=round(duration, 2), error=str(e))
            return pipeline_id

        duration = time.time() - start_time
        update_pipeline(pipeline_id, duration_seconds=round(duration, 2))
        return pipeline_id
