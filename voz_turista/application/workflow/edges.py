from typing import Literal
from langgraph.types import Send
from voz_turista.application.workflow.state import ProjectState

def route_request(state: ProjectState) -> Literal["prepare_chunks", "deep_dive_node", "__end__"]:
    step = state["next_step"]
    if step == "map_reduce":
        return "prepare_chunks"
    elif step == "deep_dive":
        return "deep_dive_node"
    else:
        return "__end__"

def map_reviews(state: ProjectState):
    return [
        Send("extract_insights", {"chunk_id": i, "reviews": chunk}) 
        for i, chunk in enumerate(state["review_chunks"])
    ]
