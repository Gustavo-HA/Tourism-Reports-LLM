from langgraph.graph import StateGraph, END, START
from voz_turista.application.workflow.state import ProjectState
from voz_turista.application.workflow.nodes import (
    router_node,
    prepare_chunks_node,
    extract_insights_node,
    synthesize_report_node,
    generate_suggestions_node,
    deep_dive_node
)
from voz_turista.application.workflow.edges import route_request, map_reviews

# Definición del Grafo
workflow = StateGraph(ProjectState)

# 1. Añadir Nodos
workflow.add_node("router", router_node)
workflow.add_node("prepare_chunks", prepare_chunks_node)
workflow.add_node("extract_insights", extract_insights_node)
workflow.add_node("synthesize_report", synthesize_report_node)
workflow.add_node("generate_suggestions", generate_suggestions_node)
workflow.add_node("deep_dive_node", deep_dive_node)

# 2. Definir Flujo
workflow.add_edge(START, "router")

# Router decide: Map-Reduce (Nuevo) o Deep Dive (Pregunta)
workflow.add_conditional_edges(
    "router",
    route_request,
    {
        "prepare_chunks": "prepare_chunks",
        "deep_dive_node": "deep_dive_node",
        "__end__": END
    }
)

# Rama Map-Reduce
workflow.add_conditional_edges("prepare_chunks", map_reviews, ["extract_insights"])
workflow.add_edge("extract_insights", "synthesize_report")
workflow.add_edge("synthesize_report", "generate_suggestions")
workflow.add_edge("generate_suggestions", END)

# Rama Deep Dive
workflow.add_edge("deep_dive_node", END)

# Compilar
app = workflow.compile()
