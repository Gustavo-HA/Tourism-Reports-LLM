from typing import Dict, List, Any, Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Send

from voz_turista.application.workflow.state import ProjectState, ReviewChunkState
from voz_turista.domain.prompts.templates import (
    SYSTEM_PROMPT_EXTRACT,
    SYSTEM_PROMPT_SYNTHESIZE,
    SYSTEM_PROMPT_AUDITOR,
)
from voz_turista.infrastructure.database.chroma_client import ChromaClient
from voz_turista.infrastructure.llm_providers.google_provider import (
    LangChainGoogleProvider,
)
from voz_turista.config import settings

# Inicialización de servicios (Idealmente inyectados)
# Nota: Se asume que las variables de entorno están configuradas

llm_provider = LangChainGoogleProvider(model_name=settings.LLM_ORCHESTRATOR)

chroma_client = ChromaClient(persist_directory=settings.VECTOR_DB_PATH)


def retrieve_reviews_node(state: ProjectState) -> Dict[str, Any]:
    """
    Recupera reseñas de ChromaDB basadas en el Pueblo Mágico seleccionado.
    """
    print(f"--- Recuperando reseñas para {state['pueblo_magico']} ---")
    reviews = chroma_client.query_reviews(
        town=state["pueblo_magico"],
        limit=100,  # Limite configurable, 300k es mucho para una demo, usar paginación en prod
    )
    return {"reviews": reviews}


def prepare_chunks_node(state: ProjectState) -> List[Send]:
    """
    Divide las reseñas en chunks y distribuye el trabajo (Map).
    """
    print("--- Preparando chunks para procesamiento paralelo ---")
    reviews = state["reviews"]
    chunk_size = 20  # Tamaño del lote
    chunks = [reviews[i : i + chunk_size] for i in range(0, len(reviews), chunk_size)]

    # Generar tareas para el nodo de extracción
    tasks = []
    for i, chunk in enumerate(chunks):
        tasks.append(Send("extract_insights_node", {"chunk_id": i, "reviews": chunk}))

    return tasks


def extract_insights_node(state: ReviewChunkState) -> Dict[str, Any]:
    """
    Nodo MAP: Analiza un lote de reseñas y extrae insights.
    """
    print(f"--- Extrayendo insights del chunk {state['chunk_id']} ---")

    # Formatear reseñas para el prompt
    reviews_text = "\n".join(
        [f"ID: {r['id']} | Texto: {r['text']}" for r in state["reviews"]]
    )

    prompt = SYSTEM_PROMPT_EXTRACT.format(
        pueblo_magico="el destino",  # O pasar el nombre si estuviera en el estado del chunk
        reviews=reviews_text,
    )

    # Definir esquema de salida esperado (simplificado para el ejemplo)
    # En producción usar Pydantic models
    schema = {
        "title": "InsightsList",
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "idx_review": {"type": "array", "items": {"type": "string"}},
                        "insight": {"type": "string"},
                        "atribucion": {
                            "type": "string",
                            "enum": ["Pública", "Privada"],
                        },
                        "dimension": {"type": "string"},
                        "urgencia": {"type": "string"},
                    },
                    "required": [
                        "idx_review",
                        "insight",
                        "atribucion",
                        "dimension",
                        "urgencia",
                    ],
                },
            }
        },
    }

    try:
        response = llm_provider.generate_structured(
            messages=[HumanMessage(content=prompt)], schema=schema
        )
        return {"insights": response["insights"]}
    except Exception as e:
        print(f"Error en chunk {state['chunk_id']}: {e}")
        return {"insights": []}


def synthesize_report_node(state: ProjectState) -> Dict[str, Any]:
    """
    Nodo REDUCE: Sintetiza todos los insights en un reporte estratégico.
    """
    print("--- Sintetizando reporte final ---")

    # Consolidar insights (ya están en state['insights'] gracias al reducer operator.add)
    insights_text = "\n".join(
        [
            f"- [{i['urgencia']}] {i['insight']} ({i['atribucion']})"
            for i in state["insights"]
        ]
    )

    prompt = SYSTEM_PROMPT_SYNTHESIZE.format(
        pueblo_magico=state["pueblo_magico"], insights=insights_text
    )

    # Esquema del reporte
    schema = {
        "title": "StrategicBriefing",
        "type": "object",
        "properties": {
            "scorecard": {"type": "object"},
            "diagnostico_brechas": {"type": "array", "items": {"type": "string"}},
            "hoja_ruta": {"type": "object"},
        },
    }

    response = llm_provider.generate_structured(
        messages=[HumanMessage(content=prompt)], schema=schema
    )

    return {"reporte_base": response}


def auditor_node(state: ProjectState) -> Dict[str, Any]:
    """
    Self-Correction Loop: Verifica la fidelidad del reporte contra la evidencia.
    """
    print("--- Auditando reporte ---")

    report_str = str(state["reporte_base"])
    # Tomar una muestra aleatoria o relevante de reseñas como evidencia para el auditor
    # En un sistema real, usaríamos RAG para buscar evidencia que contradiga el reporte
    evidence_sample = "\n".join([r["text"] for r in state["reviews"][:10]])

    prompt = SYSTEM_PROMPT_AUDITOR.format(
        pueblo_magico=state["pueblo_magico"],
        report=report_str,
        evidence=evidence_sample,
    )

    schema = {
        "title": "AuditResult",
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["APROBADO", "RECHAZADO"]},
            "correcciones": {"type": "string"},
        },
    }

    response = llm_provider.generate_structured(
        messages=[HumanMessage(content=prompt)], schema=schema
    )

    return {
        "auditoria": response,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def route_after_audit(state: ProjectState) -> Literal["end", "synthesize_report"]:
    """
    Decide si terminar o corregir el reporte.
    """
    if state["auditoria"]["status"] == "APROBADO" or state["iteration_count"] > 3:
        print("--- Auditoría aprobada o límite de iteraciones alcanzado ---")
        return "end"
    else:
        print("--- Auditoría rechazada, regenerando reporte ---")
        # Aquí podríamos inyectar las correcciones en el contexto para la próxima síntesis
        return "synthesize_report"
