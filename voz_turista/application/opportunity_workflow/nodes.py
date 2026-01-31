"""Node functions for the Opportunity Workflow."""

from typing import Any, Dict, List, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.types import Send

from voz_turista.application.opportunity_workflow.prompts import (
    PROMPT_AUDIT_REPORT,
    PROMPT_CHAT_RESPONSE,
    PROMPT_CONSOLIDATE_REPORT,
    PROMPT_EXTRACT_OPPORTUNITIES,
    PROMPT_PARSE_QUERY,
    PROMPT_SYNTHESIZE_OPPORTUNITIES,
)
from voz_turista.application.opportunity_workflow.state import (
    BusinessTypeChunkState,
    ChatState,
    ReportGenerationState,
)
from voz_turista.config import settings
from voz_turista.infrastructure.database.chroma_client import ChromaClient
from voz_turista.infrastructure.llm_providers.google_provider import (
    LangChainGoogleProvider,
)

# Service initialization
llm_provider = LangChainGoogleProvider(model_name=settings.LLM_ORCHESTRATOR)

BUSINESS_TYPES = ["Hotel", "Restaurant", "Attractive"]


def _get_chroma_client() -> ChromaClient:
    """Get ChromaDB client instance."""
    return ChromaClient(
        persist_directory="data/chromadb/restmex_sss_cs200_ov50",
        collection_name="restmex_sss_cs200_ov50",
        embedding_model=settings.EMBEDDING_MODEL,
    )


# ============== Report Generation Nodes ==============


def retrieve_reviews_by_type_node(state: ReportGenerationState) -> Dict[str, Any]:
    """Recupera resenas de ChromaDB para cada tipo de negocio."""
    print(f"--- Recuperando resenas para {state['pueblo_magico']} ---")

    chroma_client = _get_chroma_client()
    reviews_by_type: Dict[str, List] = {}

    for business_type in BUSINESS_TYPES:
        print(f"  Consultando {business_type}s...")
        reviews = chroma_client.query_reviews(
            town=state["pueblo_magico"],
            limit=50,
            filters={"type": business_type},
            text_query="experiencia servicio calidad opinion",
        )
        reviews_by_type[business_type] = reviews
        print(f"  -> {len(reviews)} resenas encontradas para {business_type}")

    return {"reviews_by_type": reviews_by_type, "iteration_count": 0}


def prepare_analysis_tasks_node(state: ReportGenerationState) -> List[Send]:
    """Distribuye el trabajo para procesamiento paralelo por tipo y chunks."""
    print("--- Preparando tareas de analisis ---")

    tasks = []
    chunk_size = 15

    for business_type, reviews in state["reviews_by_type"].items():
        if not reviews:
            continue

        # Split reviews into chunks
        chunks = [reviews[i : i + chunk_size] for i in range(0, len(reviews), chunk_size)]

        for i, chunk in enumerate(chunks):
            tasks.append(
                Send(
                    "extract_opportunities_node",
                    {
                        "business_type": business_type,
                        "chunk_id": i,
                        "reviews": chunk,
                        "pueblo_magico": state["pueblo_magico"],
                    },
                )
            )

    print(f"  -> {len(tasks)} tareas creadas")
    return tasks


def extract_opportunities_node(state: BusinessTypeChunkState) -> Dict[str, Any]:
    """MAP: Extrae insights de oportunidad de un chunk de resenas."""
    print(f"--- Extrayendo oportunidades: {state['business_type']} chunk {state['chunk_id']} ---")

    reviews_text = "\n".join(
        [f"ID: {r['id']} | Calificacion: {r['metadata'].get('polarity', 'N/A')} | Texto: {r['text']}" for r in state["reviews"]]
    )

    prompt = PROMPT_EXTRACT_OPPORTUNITIES.format(
        business_type=state["business_type"],
        pueblo_magico=state["pueblo_magico"],
        reviews=reviews_text,
    )

    schema = {
        "title": "OpportunityInsights",
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "idx_review": {"type": "array", "items": {"type": "string"}},
                        "insight": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": ["Infraestructura", "Servicio", "Experiencia", "Precio", "Ubicacion", "Limpieza"],
                        },
                        "priority": {"type": "string", "enum": ["Alta", "Media", "Baja"]},
                        "actionable_suggestion": {"type": "string"},
                    },
                    "required": ["idx_review", "insight", "category", "priority", "actionable_suggestion"],
                },
            }
        },
        "required": ["insights"],
    }

    try:
        response = llm_provider.generate_structured(messages=[HumanMessage(content=prompt)], schema=schema)
        # Add business_type to each insight
        insights = []
        for insight in response.get("insights", []):
            insight["business_type"] = state["business_type"]
            insights.append(insight)
        return {"insights": insights}
    except Exception as e:
        print(f"Error en {state['business_type']} chunk {state['chunk_id']}: {e}")
        return {"insights": []}


def synthesize_reports_node(state: ReportGenerationState) -> Dict[str, Any]:
    """REDUCE: Sintetiza insights en reportes por tipo de negocio."""
    print("--- Sintetizando reportes por tipo de negocio ---")

    business_reports: Dict[str, Any] = {}

    for business_type in BUSINESS_TYPES:
        # Filter insights for this business type
        type_insights = [i for i in state["insights"] if i.get("business_type") == business_type]

        if not type_insights:
            business_reports[business_type] = {
                "business_type": business_type,
                "total_reviews_analyzed": len(state["reviews_by_type"].get(business_type, [])),
                "opportunity_areas": [],
                "strengths": [],
                "summary": "No se encontraron suficientes resenas para analizar.",
            }
            continue

        insights_text = "\n".join(
            [f"- [{i['priority']}] {i['insight']} (Categoria: {i['category']}) -> Sugerencia: {i['actionable_suggestion']}" for i in type_insights]
        )

        prompt = PROMPT_SYNTHESIZE_OPPORTUNITIES.format(
            business_type=business_type,
            pueblo_magico=state["pueblo_magico"],
            insights=insights_text,
            total_reviews=len(state["reviews_by_type"].get(business_type, [])),
        )

        schema = {
            "title": "BusinessTypeReport",
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "strengths"],
        }

        try:
            response = llm_provider.generate_structured(messages=[HumanMessage(content=prompt)], schema=schema)
            business_reports[business_type] = {
                "business_type": business_type,
                "total_reviews_analyzed": len(state["reviews_by_type"].get(business_type, [])),
                "opportunity_areas": type_insights,
                "strengths": response.get("strengths", []),
                "summary": response.get("summary", ""),
            }
        except Exception as e:
            print(f"Error sintetizando {business_type}: {e}")
            business_reports[business_type] = {
                "business_type": business_type,
                "total_reviews_analyzed": len(state["reviews_by_type"].get(business_type, [])),
                "opportunity_areas": type_insights,
                "strengths": [],
                "summary": f"Error al generar resumen: {e}",
            }

    return {"business_reports": business_reports}


def consolidate_report_node(state: ReportGenerationState) -> Dict[str, Any]:
    """Genera el reporte consolidado final."""
    print("--- Consolidando reporte final ---")

    # Format business reports for the prompt
    reports_text = ""
    for btype, report in state["business_reports"].items():
        reports_text += f"\n## {btype}\n"
        reports_text += f"Resenas analizadas: {report['total_reviews_analyzed']}\n"
        reports_text += f"Resumen: {report['summary']}\n"
        reports_text += f"Fortalezas: {', '.join(report['strengths'])}\n"
        reports_text += f"Oportunidades ({len(report['opportunity_areas'])}):\n"
        for opp in report["opportunity_areas"][:5]:  # Top 5
            reports_text += f"  - [{opp['priority']}] {opp['insight']}\n"

    prompt = PROMPT_CONSOLIDATE_REPORT.format(
        pueblo_magico=state["pueblo_magico"],
        business_reports=reports_text,
    )

    schema = {
        "title": "ConsolidatedReport",
        "type": "object",
        "properties": {
            "executive_summary": {"type": "string"},
            "cross_cutting_opportunities": {"type": "array", "items": {"type": "string"}},
            "priority_matrix": {
                "type": "object",
                "properties": {
                    "high_urgency_high_impact": {"type": "array", "items": {"type": "string"}},
                    "high_urgency_low_impact": {"type": "array", "items": {"type": "string"}},
                    "low_urgency_high_impact": {"type": "array", "items": {"type": "string"}},
                    "low_urgency_low_impact": {"type": "array", "items": {"type": "string"}},
                },
            },
            "recommended_actions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        },
        "required": ["executive_summary", "cross_cutting_opportunities", "recommended_actions"],
    }

    try:
        response = llm_provider.generate_structured(messages=[HumanMessage(content=prompt)], schema=schema)
        # Add business reports to consolidated report
        response["by_business_type"] = state["business_reports"]
        response["pueblo_magico"] = state["pueblo_magico"]
        return {"consolidated_report": response}
    except Exception as e:
        print(f"Error consolidando reporte: {e}")
        return {
            "consolidated_report": {
                "executive_summary": f"Error al generar reporte: {e}",
                "by_business_type": state["business_reports"],
                "pueblo_magico": state["pueblo_magico"],
            }
        }


def audit_report_node(state: ReportGenerationState) -> Dict[str, Any]:
    """Audita el reporte contra la evidencia."""
    print("--- Auditando reporte ---")

    report_str = str(state["consolidated_report"])

    # Collect sample evidence from all business types
    evidence_reviews = []
    for reviews in state["reviews_by_type"].values():
        evidence_reviews.extend(reviews[:5])

    evidence_text = "\n".join([f"- {r['text']}" for r in evidence_reviews[:15]])

    prompt = PROMPT_AUDIT_REPORT.format(
        pueblo_magico=state["pueblo_magico"],
        report=report_str,
        evidence=evidence_text,
    )

    schema = {
        "title": "AuditResult",
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["APROBADO", "RECHAZADO"]},
            "corrections": {"type": "array", "items": {"type": "string"}},
            "confidence_score": {"type": "number"},
        },
        "required": ["status"],
    }

    try:
        response = llm_provider.generate_structured(messages=[HumanMessage(content=prompt)], schema=schema)
        return {
            "audit_result": response,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    except Exception as e:
        print(f"Error en auditoria: {e}")
        return {
            "audit_result": {"status": "APROBADO", "corrections": [], "error": str(e)},
            "iteration_count": state.get("iteration_count", 0) + 1,
        }


def route_after_audit(state: ReportGenerationState) -> Literal["end", "consolidate_report"]:
    """Decide si terminar o regenerar el reporte."""
    audit = state.get("audit_result", {})
    iteration = state.get("iteration_count", 0)

    if audit.get("status") == "APROBADO" or iteration >= 3:
        print(f"--- Reporte {'aprobado' if audit.get('status') == 'APROBADO' else 'max iteraciones'} ---")
        return "end"
    else:
        print(f"--- Reporte rechazado, iteracion {iteration}/3 ---")
        return "consolidate_report"


# ============== Chat Nodes ==============


def parse_user_query_node(state: ChatState) -> Dict[str, Any]:
    """Parsea la consulta del usuario a filtros de ChromaDB."""
    print(f"--- Parseando consulta: {state['user_message'][:50]}... ---")

    prompt = PROMPT_PARSE_QUERY.format(
        pueblo_magico=state["pueblo_magico"],
        user_query=state["user_message"],
    )

    schema = {
        "title": "ParsedQuery",
        "type": "object",
        "properties": {
            "text_query": {"type": "string"},
            "filters": {"type": "object"},
            "requires_report_context": {"type": "boolean"},
        },
        "required": ["text_query", "filters", "requires_report_context"],
    }

    try:
        response = llm_provider.generate_structured(messages=[HumanMessage(content=prompt)], schema=schema)
        return {
            "text_query": response.get("text_query", state["user_message"]),
            "parsed_filters": response.get("filters", {}),
        }
    except Exception as e:
        print(f"Error parseando consulta: {e}")
        return {
            "text_query": state["user_message"],
            "parsed_filters": {},
        }


def execute_query_node(state: ChatState) -> Dict[str, Any]:
    """Ejecuta la consulta contra ChromaDB."""
    print(f"--- Ejecutando consulta: {state.get('text_query', '')[:50]}... ---")

    chroma_client = _get_chroma_client()

    try:
        reviews = chroma_client.query_reviews(
            town=state["pueblo_magico"],
            limit=20,
            filters=state.get("parsed_filters") or None,
            text_query=state.get("text_query", state["user_message"]),
        )
        return {"query_results": reviews}
    except Exception as e:
        print(f"Error ejecutando consulta: {e}")
        return {"query_results": []}


def generate_response_node(state: ChatState) -> Dict[str, Any]:
    """Genera la respuesta del chat."""
    print("--- Generando respuesta ---")

    # Format report summary
    report = state.get("consolidated_report", {})
    report_summary = f"""
Pueblo Magico: {report.get('pueblo_magico', state['pueblo_magico'])}
Resumen Ejecutivo: {report.get('executive_summary', 'No disponible')}
Oportunidades Transversales: {', '.join(report.get('cross_cutting_opportunities', [])[:3])}
"""

    # Format query results
    results = state.get("query_results", [])
    if results:
        results_text = "\n".join(
            [f"- [{r['metadata'].get('type', 'N/A')}] (Cal: {r['metadata'].get('polarity', 'N/A')}) {r['text'][:200]}..." for r in results[:10]]
        )
    else:
        results_text = "No se encontraron resenas que coincidan con la consulta."

    # Format chat history
    messages = state.get("messages", [])
    history_text = ""
    for msg in messages[-6:]:  # Last 3 exchanges
        role = "Usuario" if isinstance(msg, HumanMessage) else "Asistente"
        history_text += f"{role}: {msg.content[:200]}...\n"

    prompt = PROMPT_CHAT_RESPONSE.format(
        pueblo_magico=state["pueblo_magico"],
        report_summary=report_summary,
        num_results=len(results),
        query_results=results_text,
        chat_history=history_text or "Sin historial previo.",
        user_query=state["user_message"],
    )

    try:
        response = llm_provider.generate(messages=[HumanMessage(content=prompt)])
        return {"response": response}
    except Exception as e:
        print(f"Error generando respuesta: {e}")
        return {"response": f"Lo siento, ocurrio un error al procesar tu consulta: {e}"}
