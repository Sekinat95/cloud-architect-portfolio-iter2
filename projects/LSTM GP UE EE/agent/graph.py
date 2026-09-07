# graph.py
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langgraph.types import RetryPolicy

from tools import get_logs
from llm_diagnose import llm_diagnose


class AgentState(TypedDict):
    run_id: str
    job_id: Optional[str]
    logs: Optional[list]
    diagnosis: Optional[str]
    recommendation: Optional[str]
    confidence: Optional[str]
    next_action: Optional[str]
    iteration: int


def reasoning_node(state: AgentState) -> AgentState:
    if state["logs"] is None:
        state["next_action"] = "call_logs"
    else:
        result = llm_diagnose(state["logs"])
        state["diagnosis"] = result["root_cause"]
        state["recommendation"] = result["recommendation"]
        state["confidence"] = result["confidence"]
        state["next_action"] = "done"
    state["iteration"] += 1
    return state


def tool_node(state: AgentState) -> AgentState:
    if state["next_action"] == "call_logs":
        state["logs"] = get_logs(state["run_id"], job_id=state.get("job_id"))
    return state


graph = StateGraph(AgentState)
graph.add_node("reason", reasoning_node, retry_policy=RetryPolicy(max_attempts=1))
graph.add_node("tool", tool_node)
graph.set_entry_point("reason")
graph.add_conditional_edges("reason", lambda s: "tool" if s["next_action"] != "done" else END)
graph.add_edge("tool", "reason")
app = graph.compile()