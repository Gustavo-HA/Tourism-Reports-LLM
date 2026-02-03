"""State definitions for the Opportunity Workflow."""

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage

from voz_turista.domain.schemas import (
    BusinessTypeReport,
    ConsolidatedReport,
    OpportunityInsight,
    Review,
)


# ============== Report Generation State ==============


class ReportGenerationState(TypedDict):
    """Estado principal para la generación del reporte."""

    # Entrada del usuario
    pueblo_magico: str

    # Datos del proceso
    reviews_by_type: Dict[
        str, List[Review]
    ]  # {'Hotel': [...], 'Restaurant': [...], 'Attractive': [...]}
    insights: Annotated[List[OpportunityInsight], operator.add]  # Acumulativo via Map

    # Reportes por tipo de negocio
    business_reports: Dict[str, BusinessTypeReport]

    # Reporte consolidado final
    consolidated_report: Optional[ConsolidatedReport]

    # Auditoría
    audit_result: Optional[Dict[str, Any]]
    iteration_count: int


class BusinessTypeChunkState(TypedDict):
    """Estado para procesamiento paralelo de chunks por tipo de negocio."""

    business_type: str
    chunk_id: int
    reviews: List[Review]
    pueblo_magico: str


# ============== Chat State ==============


class ChatState(TypedDict):
    """Estado para el modo de chat interactivo."""

    # Contexto del reporte
    pueblo_magico: str
    consolidated_report: ConsolidatedReport

    # Consulta actual
    user_message: str
    messages: List[BaseMessage]  # Historial de chat

    # Resultados de la consulta
    parsed_filters: Optional[Dict[str, Any]]
    text_query: Optional[str]
    query_results: Optional[List[Review]]

    # Respuesta generada
    response: Optional[str]
