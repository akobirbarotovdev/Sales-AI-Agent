from typing import TypedDict, Optional, List, Any, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages


class PipelineState(TypedDict):
    pipeline_id: int
    query: str
    phase: str
    leads: List[dict]
    lead_ids: List[int]
    errors: List[str]
    lead_gen_done: bool
    research_done: bool
    qualification_done: bool
    validation_done: bool
    email_draft_done: bool
    start_time: Optional[str]
    current_lead_index: int
    messages: Annotated[list, add_messages]
