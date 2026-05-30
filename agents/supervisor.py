import json
from agents.base import BaseAgent
from config import settings


SUPERVISOR_SYSTEM = """You are the Supervisor Agent of a multi-agent sales lead pipeline.
Your job is to analyze the current pipeline state and decide which agent should run next.

Phases flow: lead_generation → research → qualification → validation → email_draft → complete

Rules:
- lead_generation: Only run once, at the start
- research: Run after lead_gen, once per batch
- qualification: Run after research, score each lead
- validation: Run after qualification (only for 75+ score leads)
- email_draft: Run after validation (only for validated leads)

Respond with JSON:
{
  "decision": "continue" | "complete" | "error",
  "next_agent": "lead_generation" | "research" | "qualification" | "validation" | "email_draft" | "none",
  "reason": "brief explanation",
  "skip_leads": []
}
"""

PHASE_ORDER = ["lead_generation", "research", "qualification", "validation", "email_draft"]


class SupervisorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="supervisor",
            model=settings.sonnet_model,
            timeout=settings.sonnet_timeout,
        )

    def delegate(self, pipeline_state: dict) -> dict:
        done_map = {
            "lead_generation": pipeline_state.get("lead_gen_done", False),
            "research": pipeline_state.get("research_done", False),
            "qualification": pipeline_state.get("qualification_done", False),
            "validation": pipeline_state.get("validation_done", False),
            "email_draft": pipeline_state.get("email_draft_done", False),
        }
        errors = pipeline_state.get("errors", [])

        if errors and len(errors) > 10:
            return {"decision": "error", "next_agent": "none", "reason": "Too many errors", "skip_leads": []}

        for phase in PHASE_ORDER:
            if not done_map.get(phase):
                return {"decision": "continue", "next_agent": phase, "reason": f"Next phase: {phase}", "skip_leads": []}

        return {"decision": "complete", "next_agent": "none", "reason": "All phases done", "skip_leads": []}
