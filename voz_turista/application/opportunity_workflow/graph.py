"""Graph definitions for the Opportunity Workflow."""

from langgraph.graph import END, START, StateGraph

from voz_turista.application.opportunity_workflow.nodes import (
    audit_report_node,
    consolidate_report_node,
    execute_query_node,
    extract_opportunities_node,
    generate_response_node,
    parse_user_query_node,
    prepare_analysis_tasks_node,
    retrieve_reviews_by_type_node,
    route_after_audit,
    synthesize_reports_node,
)
from voz_turista.application.opportunity_workflow.state import (
    ChatState,
    ReportGenerationState,
)


def build_report_workflow() -> StateGraph:
    """
    Construye el grafo para generacion de reportes de oportunidades.

    Flujo:
    START -> retrieve_reviews_by_type -> [parallel extract_opportunities]
          -> synthesize_reports -> consolidate_report -> audit_report
          -> (APROBADO) END | (RECHAZADO) consolidate_report
    """
    workflow = StateGraph(ReportGenerationState)

    # Add nodes
    workflow.add_node("retrieve_reviews_by_type", retrieve_reviews_by_type_node)
    workflow.add_node("extract_opportunities_node", extract_opportunities_node)
    workflow.add_node("synthesize_reports", synthesize_reports_node)
    workflow.add_node("consolidate_report", consolidate_report_node)
    workflow.add_node("audit_report", audit_report_node)

    # Define flow
    workflow.add_edge(START, "retrieve_reviews_by_type")

    # Map phase: parallel processing via Send()
    workflow.add_conditional_edges(
        "retrieve_reviews_by_type",
        prepare_analysis_tasks_node,
        ["extract_opportunities_node"],
    )

    # Reduce phase
    workflow.add_edge("extract_opportunities_node", "synthesize_reports")
    workflow.add_edge("synthesize_reports", "consolidate_report")
    workflow.add_edge("consolidate_report", "audit_report")

    # Self-correction loop
    workflow.add_conditional_edges(
        "audit_report",
        route_after_audit,
        {"end": END, "consolidate_report": "consolidate_report"},
    )

    return workflow.compile()


def build_chat_workflow() -> StateGraph:
    """
    Construye el grafo para el modo de chat interactivo.

    Flujo:
    START -> parse_user_query -> execute_query -> generate_response -> END
    """
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("parse_user_query", parse_user_query_node)
    workflow.add_node("execute_query", execute_query_node)
    workflow.add_node("generate_response", generate_response_node)

    # Define flow
    workflow.add_edge(START, "parse_user_query")
    workflow.add_edge("parse_user_query", "execute_query")
    workflow.add_edge("execute_query", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()
