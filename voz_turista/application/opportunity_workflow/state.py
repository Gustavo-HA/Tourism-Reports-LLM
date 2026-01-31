"""State definitions for the Opportunity Workflow."""

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import BaseMessage


class Review(TypedDict):
    """Representa una resena individual recuperada de ChromaDB."""

    id: str
    text: str
    metadata: Dict[str, Any]
    distance: float


class OpportunityInsight(TypedDict):
    """Un insight de oportunidad para un tipo de negocio especifico."""

    business_type: str  # 'Hotel', 'Restaurant', 'Attractive'
    idx_review: List[str]
    insight: str
    category: str  # 'Infraestructura', 'Servicio', 'Experiencia', 'Precio', 'Ubicacion', 'Limpieza'
    priority: str  # 'Alta', 'Media', 'Baja'
    actionable_suggestion: str


class BusinessTypeReport(TypedDict):
    """Seccion del reporte para un tipo de negocio especifico."""

    business_type: str
    total_reviews_analyzed: int
    opportunity_areas: List[OpportunityInsight]
    strengths: List[str]
    summary: str


# ============== Report Generation State ==============


class ReportGenerationState(TypedDict):
    """Estado principal para la generacion del reporte."""

    # Entrada del usuario
    pueblo_magico: str

    # Datos del proceso
    reviews_by_type: Dict[str, List[Review]]  # {'Hotel': [...], 'Restaurant': [...], 'Attractive': [...]}
    insights: Annotated[List[OpportunityInsight], operator.add]  # Acumulativo via Map

    # Reportes por tipo de negocio
    business_reports: Dict[str, BusinessTypeReport]

    # Reporte consolidado final
    consolidated_report: Optional[Dict[str, Any]]

    # Auditoria
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
    consolidated_report: Dict[str, Any]

    # Consulta actual
    user_message: str
    messages: List[BaseMessage]  # Historial de chat

    # Resultados de la consulta
    parsed_filters: Optional[Dict[str, Any]]
    text_query: Optional[str]
    query_results: Optional[List[Review]]

    # Respuesta generada
    response: Optional[str]
