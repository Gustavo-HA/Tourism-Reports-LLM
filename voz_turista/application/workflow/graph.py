from langgraph.graph import StateGraph, END, START
from voz_turista.application.workflow.state import ProjectState
from voz_turista.application.workflow.nodes import (
    retrieve_reviews_node,
    prepare_chunks_node,
    extract_insights_node,
    synthesize_report_node,
    auditor_node,
    route_after_audit,
)

# Definición del Grafo
workflow = StateGraph(ProjectState)

# 1. Añadir Nodos
workflow.add_node("retrieve_reviews", retrieve_reviews_node)
workflow.add_node("extract_insights_node", extract_insights_node)  # Nodo Map
workflow.add_node("synthesize_report", synthesize_report_node)  # Nodo Reduce
workflow.add_node("auditor", auditor_node)  # Nodo Self-Correction

# 2. Definir Flujo
workflow.add_edge(START, "retrieve_reviews")

# Map Phase: De recuperación a preparación de chunks (que dispara extract_insights_node en paralelo)
workflow.add_conditional_edges(
    "retrieve_reviews", prepare_chunks_node, ["extract_insights_node"]
)

# Reduce Phase: De extracción a síntesis
workflow.add_edge("extract_insights_node", "synthesize_report")

# Self-Correction Loop: De síntesis a auditoría
workflow.add_edge("synthesize_report", "auditor")

# Decisión Post-Auditoría: Terminar o corregir
workflow.add_conditional_edges(
    "auditor", route_after_audit, {"end": END, "synthesize_report": "synthesize_report"}
)

# Compilar
app = workflow.compile()
