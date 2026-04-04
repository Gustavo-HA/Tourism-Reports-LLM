"""Node functions for the Opportunity Workflow."""

import logging
from typing import Any, Dict, List, Literal

from langchain_core.messages import HumanMessage
from langgraph.types import Send

from voz_turista.application.workflow.prompts import (
    PROMPT_AUDIT_REPORT,
    PROMPT_CHAT_RESPONSE,
    PROMPT_CONSOLIDATE_REPORT,
    PROMPT_EXTRACT_OPPORTUNITIES,
    PROMPT_PARSE_QUERY,
    PROMPT_SYNTHESIZE_OPPORTUNITIES,
)
from voz_turista.application.workflow.state import (
    BusinessTypeChunkState,
    ChatState,
    ReportGenerationState,
)
from voz_turista.config import settings
from voz_turista.domain.schemas import (
    AuditResult,
    BusinessTypeSynthesis,
    ConsolidatedReport,
    ExtractedOpportunityInsightList,
    ParsedQuery,
    Review,
)
from voz_turista.infrastructure.database.chroma_client import ChromaClient
from voz_turista.infrastructure.llm_providers.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)

# Service initialization
llm_provider = LiteLLMProvider(
    model_name=settings.LLM_MODEL, temperature=settings.LLM_TEMPERATURE
)

BUSINESS_TYPES = ["Hotel", "Restaurant", "Attractive"]

BUSINESS_TYPE_QUERIES: Dict[str, List[str]] = {
    "Hotel": [
        "problemas con la experiencia de hospedaje habitación limpieza comodidad",
        "problemas con recepción servicio atención check-in personal",
        "problemas con las amenidades instalaciones alberca desayuno precio",
    ],
    "Restaurant": [
        "problemas con comida sabor calidad platillo frescura",
        "problemas con servicio mesero tiempo espera atención",
        "problemas con ambiente precio menú variedad opciones",
    ],
    "Attractive": [
        "problemas con experiencia visita recorrido actividad entretenimiento",
        "problemas con paisaje vista lugar belleza natural",
        "problemas con acceso infraestructura señalización guía seguridad",
    ],
}

REVIEWS_PER_QUERY = 5


def _get_chroma_client() -> ChromaClient:
    """Get ChromaDB client instance."""
    return ChromaClient(
        persist_directory=settings.VECTOR_DB_PATH,
        collection_name="restmex_sss_cs200_ov50",
        embedding_model=settings.EMBEDDING_MODEL,
    )


# ============== Report Generation Nodes ==============


def retrieve_reviews_by_type_node(state: ReportGenerationState) -> Dict[str, Any]:
    """Recupera reseñas de ChromaDB para cada tipo de negocio usando múltiples queries."""
    logger.info("Recuperando reseñas para %s", state["pueblo_magico"])

    chroma_client = _get_chroma_client()
    reviews_by_type: Dict[str, List[Review]] = {}

    for business_type in BUSINESS_TYPES:
        queries = BUSINESS_TYPE_QUERIES.get(business_type, [])
        seen_ids: set = set()
        type_reviews: List[Review] = []

        for query in queries:
            logger.info("  Consultando %s: '%s...'", business_type, query[:40])
            raw_reviews = chroma_client.query_reviews(
                town=state["pueblo_magico"],
                limit=REVIEWS_PER_QUERY,
                filters={"type": business_type},
                text_query=query,
            )
            for r in raw_reviews:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    type_reviews.append(
                        Review(
                            id=r["id"],
                            text=r["text"],
                            metadata=r["metadata"],
                            distance=r["distance"],
                        )
                    )

        reviews_by_type[business_type] = type_reviews
        logger.info("  -> %d reseñas únicas encontradas para %s", len(type_reviews), business_type)

    return {"reviews_by_type": reviews_by_type, "iteration_count": 0}


def prepare_analysis_tasks_node(state: ReportGenerationState) -> List[Send]:
    """Distribuye el trabajo para procesamiento paralelo por tipo y chunks."""
    logger.info("Preparando tareas de analisis")

    tasks = []
    chunk_size = 15

    for business_type, reviews in state["reviews_by_type"].items():
        if not reviews:
            continue

        # Split reviews into chunks
        chunks = [
            reviews[i : i + chunk_size] for i in range(0, len(reviews), chunk_size)
        ]

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

    logger.info("  -> %d tareas creadas", len(tasks))
    return tasks


def extract_opportunities_node(state: BusinessTypeChunkState) -> Dict[str, Any]:
    """MAP: Extrae insights de oportunidad de un chunk de reseñas."""
    logger.info("Extrayendo oportunidades: %s chunk %s", state["business_type"], state["chunk_id"])

    # Handle both Review objects and dicts (for compatibility)
    reviews_text = "\n".join(
        [
            f"ID: {r.id if hasattr(r, 'id') else r['id']} | "
            f"Calificacion: {(r.metadata if hasattr(r, 'metadata') else r['metadata']).get('polarity', 'N/A')} | "
            f"Año : {(r.metadata if hasattr(r, 'metadata') else r['metadata']).get('year', 'N/A')} | "
            f"Texto: {r.text if hasattr(r, 'text') else r['text']}"
            for r in state["reviews"]
        ]
    )

    prompt = PROMPT_EXTRACT_OPPORTUNITIES.format(
        business_type=state["business_type"],
        pueblo_magico=state["pueblo_magico"],
        reviews=reviews_text,
    )

    try:
        response: ExtractedOpportunityInsightList = llm_provider.generate_structured(
            messages=[HumanMessage(content=prompt)],
            schema=ExtractedOpportunityInsightList,
        )
        # Add business_type to each insight and convert to dict for state accumulation
        insights = []
        for insight in response.insights:
            insight_dict = insight.model_dump()
            insight_dict["business_type"] = state["business_type"]
            insights.append(insight_dict)
        return {"insights": insights}
    except Exception:
        logger.exception("Error en %s chunk %s", state["business_type"], state["chunk_id"])
        return {"insights": []}


def synthesize_reports_node(state: ReportGenerationState) -> Dict[str, Any]:
    """REDUCE: Sintetiza insights en reportes por tipo de negocio."""
    logger.info("Sintetizando reportes por tipo de negocio")

    business_reports: Dict[str, Any] = {}

    for business_type in BUSINESS_TYPES:
        # Filter insights for this business type
        type_insights = [
            i for i in state["insights"] if i.get("business_type") == business_type
        ]

        # Get reviews count (handle both Review objects and dicts)
        reviews_list = state["reviews_by_type"].get(business_type, [])
        total_reviews = len(reviews_list)

        if not type_insights:
            business_reports[business_type] = {
                "business_type": business_type,
                "total_reviews_analyzed": total_reviews,
                "opportunity_areas": [],
                "strengths": [],
                "summary": "No se encontraron suficientes reseñas para analizar.",
            }
            continue

        insights_text = "\n".join(
            [
                f"- [{i['urgencia']}] {i['insight']} (Atribución: {i['atribucion']}, Dimensión: {i['dimension']}) -> Sugerencia: {i['actionable_suggestion']}"
                for i in type_insights
            ]
        )

        prompt = PROMPT_SYNTHESIZE_OPPORTUNITIES.format(
            business_type=business_type,
            pueblo_magico=state["pueblo_magico"],
            insights=insights_text,
            total_reviews=total_reviews,
        )

        try:
            response: BusinessTypeSynthesis = llm_provider.generate_structured(
                messages=[HumanMessage(content=prompt)], schema=BusinessTypeSynthesis
            )
            business_reports[business_type] = {
                "business_type": business_type,
                "total_reviews_analyzed": total_reviews,
                "opportunity_areas": type_insights,
                "strengths": response.strengths,
                "gap_diagnosis": response.gap_diagnosis,
                "summary": response.summary,
            }
        except Exception as e:
            logger.exception("Error sintetizando %s", business_type)
            business_reports[business_type] = {
                "business_type": business_type,
                "total_reviews_analyzed": total_reviews,
                "opportunity_areas": type_insights,
                "strengths": [],
                "gap_diagnosis": [],
                "summary": f"Error al generar resumen: {e}",
            }

    return {"business_reports": business_reports}


def consolidate_report_node(state: ReportGenerationState) -> Dict[str, Any]:
    """Genera el reporte consolidado final."""
    logger.info("Consolidando reporte final")

    reports_text = ""
    for btype, report in state["business_reports"].items():
        reports_text += f"\n## {btype}\n"
        reports_text += f"Reseñas analizadas: {report['total_reviews_analyzed']}\n"
        reports_text += f"Resumen: {report['summary']}\n"
        reports_text += f"Fortalezas: {', '.join(report['strengths'])}\n"
        reports_text += f"Brechas: {'; '.join(report.get('gap_diagnosis', []))}\n"
        reports_text += f"Hallazgos ({len(report['opportunity_areas'])}):\n"
        for opp in report["opportunity_areas"][:5]:  # Top 5
            reports_text += f"  - [{opp['urgencia']}] ({opp['atribucion']}/{opp['dimension']}) {opp['insight']}\n"

    prompt = PROMPT_CONSOLIDATE_REPORT.format(
        pueblo_magico=state["pueblo_magico"],
        business_reports=reports_text,
    )

    try:
        response: ConsolidatedReport = llm_provider.generate_structured(
            messages=[HumanMessage(content=prompt)], schema=ConsolidatedReport
        )
        # Convert to dict and add business reports context
        consolidated = response.model_dump()
        consolidated["by_business_type"] = state["business_reports"]
        consolidated["pueblo_magico"] = state["pueblo_magico"]
        return {"consolidated_report": consolidated}
    except Exception as e:
        logger.exception("Error consolidando reporte")
        return {
            "consolidated_report": {
                "executive_summary": f"Error al generar reporte: {e}",
                "scorecard": {},
                "gap_diagnosis": [],
                "roadmap": {"inversion_publica": [], "capacitacion_privada": []},
                "cross_cutting_opportunities": [],
                "by_business_type": state["business_reports"],
                "pueblo_magico": state["pueblo_magico"],
            }
        }


def audit_report_node(state: ReportGenerationState) -> Dict[str, Any]:
    """Audita el reporte contra la evidencia."""
    logger.info("Auditando reporte")

    report_str = str(state["consolidated_report"])

    # Collect sample evidence from all business types (handle both Review objects and dicts)
    evidence_reviews = []
    for reviews in state["reviews_by_type"].values():
        evidence_reviews.extend(reviews)

    evidence_text = "\n".join(
        [
            f"- {r.text if hasattr(r, 'text') else r['text']}"
            for r in evidence_reviews
        ]
    )

    prompt = PROMPT_AUDIT_REPORT.format(
        pueblo_magico=state["pueblo_magico"],
        report=report_str,
        evidence=evidence_text,
    )

    try:
        response: AuditResult = llm_provider.generate_structured(
            messages=[HumanMessage(content=prompt)], schema=AuditResult
        )
        return {
            "audit_result": response.model_dump(),
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    except Exception as e:
        logger.exception("Error en auditoría")
        return {
            "audit_result": {"status": "APROBADO", "corrections": [], "error": str(e)},
            "iteration_count": state.get("iteration_count", 0) + 1,
        }


def route_after_audit(
    state: ReportGenerationState,
) -> Literal["end", "consolidate_report"]:
    """Decide si terminar o regenerar el reporte."""
    audit = state.get("audit_result", {})
    iteration = state.get("iteration_count", 0)

    if audit.get("status") == "APROBADO" or iteration >= 3:
        logger.info("Reporte %s", "aprobado" if audit.get("status") == "APROBADO" else "max iteraciones")
        return "end"
    else:
        logger.info("Reporte rechazado, iteracion %d/3", iteration)
        return "consolidate_report"


# ============== Chat Nodes ==============


def parse_user_query_node(state: ChatState) -> Dict[str, Any]:
    """Parsea la consulta del usuario a filtros de ChromaDB."""
    logger.info("Parseando consulta: %s...", state["user_message"][:50])

    prompt = PROMPT_PARSE_QUERY.format(
        pueblo_magico=state["pueblo_magico"],
        user_query=state["user_message"],
    )

    try:
        response: ParsedQuery = llm_provider.generate_structured(
            messages=[HumanMessage(content=prompt)], schema=ParsedQuery
        )
        return {
            "text_query": response.text_query or state["user_message"],
            "parsed_filters": response.filters.model_dump(exclude_none=True),
        }
    except Exception:
        logger.exception("Error parseando consulta")
        return {
            "text_query": state["user_message"],
            "parsed_filters": {},
        }


def execute_query_node(state: ChatState) -> Dict[str, Any]:
    """Ejecuta la consulta contra ChromaDB."""
    logger.info("Ejecutando consulta: %s...", state.get("text_query", "")[:50])

    chroma_client = _get_chroma_client()

    try:
        raw_reviews = chroma_client.query_reviews(
            town=state["pueblo_magico"],
            limit=20,
            filters=state.get("parsed_filters") or None,
            text_query=state.get("text_query", state["user_message"]),
        )
        # Convert to Review Pydantic models
        reviews = [
            Review(
                id=r["id"],
                text=r["text"],
                metadata=r["metadata"],
                distance=r["distance"],
            )
            for r in raw_reviews
        ]
        return {"query_results": reviews}
    except Exception:
        logger.exception("Error ejecutando consulta")
        return {"query_results": []}


def generate_response_node(state: ChatState) -> Dict[str, Any]:
    """Genera la respuesta del chat."""
    logger.info("Generando respuesta")

    # Format report summary (handle both dict and Pydantic model)
    report = state.get("consolidated_report", {})
    if hasattr(report, "model_dump"):
        report = report.model_dump()

    scorecard = report.get("scorecard", {})
    scorecard_text = ", ".join(
        f"{p}: {scorecard.get(p, {}).get('score', 'N/A')}/10"
        for p in ["infraestructura", "servicios", "atractivos"]
        if isinstance(scorecard.get(p), dict)
    )
    roadmap = report.get("roadmap", {})
    report_summary = f"""
Pueblo Mágico: {report.get("pueblo_magico", state["pueblo_magico"])}
Resumen Ejecutivo: {report.get("executive_summary", "No disponible")}
Scorecard: {scorecard_text or "No disponible"}
Brechas: {"; ".join(report.get("gap_diagnosis", [])[:3])}
Inversión Pública: {"; ".join((roadmap.get("inversion_publica") or [])[:3])}
Capacitación Privada: {"; ".join((roadmap.get("capacitacion_privada") or [])[:3])}
Oportunidades Transversales: {", ".join(report.get("cross_cutting_opportunities", [])[:3])}
"""

    # Format query results (handle both Review objects and dicts)
    results = state.get("query_results", [])
    if results:
        results_text = "\n".join(
            [
                f"- [{(r.metadata if hasattr(r, 'metadata') else r['metadata']).get('type', 'N/A')}] "
                f"(Cal: {(r.metadata if hasattr(r, 'metadata') else r['metadata']).get('polarity', 'N/A')}) "
                f"{(r.text if hasattr(r, 'text') else r['text'])[:200]}..."
                for r in results[:10]
            ]
        )
    else:
        results_text = "No se encontraron reseñas que coincidan con la consulta."

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
        logger.exception("Error generando respuesta")
        return {"response": f"Lo siento, ocurrió un error al procesar tu consulta: {e}"}
