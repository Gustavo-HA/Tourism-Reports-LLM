from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============== Base Workflow Schemas ==============
# Used by voz_turista/application/workflow.py


class Insight(BaseModel):
    """Estructura de un insight individual extraído de reseñas."""

    idx_review: List[str] = Field(
        description="IDs de referencia de las reseñas que sustentan el hallazgo."
    )
    insight: str = Field(description="Hallazgo conciso y accionable.")
    atribucion: Literal["Publica", "Privada"] = Field(
        description="Clasifica si el problema/oportunidad recae en el gobierno (Publica) o en los negocios privados (Privada)."
    )
    dimension: Literal[
        "Recurso Natural", "Servicio de Soporte", "Gestion de Destino"
    ] = Field(description="Dimensión del hallazgo.")
    urgencia: Literal["Alta", "Media", "Baja"] = Field(
        description="Nivel de urgencia según el impacto en la competitividad turística."
    )


class InsightList(BaseModel):
    """Lista de insights extraídos."""

    insights: List[Insight]


class ReportSection(BaseModel):
    """Sección del reporte para un pilar específico (Scorecard, Gaps, Roadmap)."""

    score: int = Field(description="Calificación del 1 al 10.", ge=1, le=10)
    summary: str = Field(description="Resumen ejecutivo de la sección.")
    actions: List[str] = Field(description="Acciones concretas sugeridas.")


class FullReport(BaseModel):
    """Estructura del reporte sintetizado final."""

    scorecard: Dict[str, int] = Field(
        description="Puntajes por pilar (Infraestructura, Servicios, Atractivos)."
    )
    gaps: List[str] = Field(description="Lista de brechas identificadas.")
    roadmap: Dict[str, List[str]] = Field(
        description="Hoja de ruta con acciones priorizadas (Publica vs Privada)."
    )


class AuditResult(BaseModel):
    """Resultado de la auditoría del reporte."""

    status: Literal["APROBADO", "RECHAZADO"]
    corrections: List[str] = Field(
        default_factory=list, description="Correcciones necesarias si fue rechazado."
    )
    confidence_score: Optional[float] = Field(
        default=None, description="Puntuación de confianza del auditor (0-1)."
    )


# ============== Opportunity Workflow Schemas ==============
# Used by voz_turista/application/opportunity_workflow/


class Review(BaseModel):
    """Representa una reseña individual recuperada de ChromaDB."""

    id: str = Field(description="ID único de la reseña en ChromaDB.")
    text: str = Field(description="Contenido de la reseña.")
    metadata: Dict[str, Any] = Field(
        description="Metadatos de la reseña (town, polarity, type, place, month, year)."
    )
    distance: float = Field(description="Distancia de similitud desde la consulta.")


class ExtractedOpportunityInsight(BaseModel):
    """Insight extraído por el LLM (sin business_type, se añade después)."""

    idx_review: List[str] = Field(
        description="IDs de las reseñas que sustentan este insight."
    )
    insight: str = Field(description="Hallazgo conciso y accionable.")
    atribucion: Literal["Publica", "Privada"] = Field(
        description="Clasifica si el problema/oportunidad recae en el gobierno (Publica) o en los negocios privados (Privada)."
    )
    dimension: Literal[
        "Recurso Natural", "Servicio de Soporte", "Gestion de Destino"
    ] = Field(description="Dimensión del hallazgo.")
    urgencia: Literal["Alta", "Media", "Baja"] = Field(
        description="Nivel de urgencia según el impacto en la competitividad turística."
    )
    actionable_suggestion: str = Field(
        description="Sugerencia accionable para abordar el insight."
    )


class ExtractedOpportunityInsightList(BaseModel):
    """Lista de insights extraídos por el LLM."""

    insights: List[ExtractedOpportunityInsight]


class OpportunityInsight(ExtractedOpportunityInsight):
    """Un insight de oportunidad completo con tipo de negocio."""

    business_type: str = Field(
        description="Tipo de negocio: 'Hotel', 'Restaurant', 'Attractive'."
    )


class OpportunityInsightList(BaseModel):
    """Lista de insights de oportunidad con tipo de negocio."""

    insights: List[OpportunityInsight]


class BusinessTypeReport(BaseModel):
    """Sección del reporte para un tipo de negocio específico."""

    business_type: str = Field(description="Tipo de negocio analizado.")
    total_reviews_analyzed: int = Field(description="Número de reseñas analizadas.")
    opportunity_areas: List[OpportunityInsight] = Field(
        description="Lista de áreas de oportunidad identificadas."
    )
    strengths: List[str] = Field(description="Fortalezas identificadas.")
    summary: str = Field(description="Resumen ejecutivo de la sección.")


class BusinessTypeSynthesis(BaseModel):
    """Resultado de la síntesis para un tipo de negocio (sin opportunity_areas, se añaden después)."""

    summary: str = Field(description="Resumen ejecutivo de la sección.")
    strengths: List[str] = Field(description="Fortalezas identificadas.")
    gap_diagnosis: List[str] = Field(
        description="Brechas identificadas: recursos infrautilizados por fallas públicas o privadas."
    )


class PillarScore(BaseModel):
    """Calificación de un pilar del scorecard."""

    score: int = Field(description="Calificación del 1 al 10.", ge=1, le=10)
    justification: str = Field(
        description="Justificación breve de la calificación basada en evidencia."
    )


class Scorecard(BaseModel):
    """Scorecard de Eficiencia Turística por pilares."""

    infraestructura: PillarScore = Field(
        description="Evaluación de infraestructura (transporte, señalización, accesos, servicios básicos)."
    )
    servicios: PillarScore = Field(
        description="Evaluación de servicios turísticos (hospedaje, restaurantes, guías, atención)."
    )
    atractivos: PillarScore = Field(
        description="Evaluación de atractivos (recursos naturales, culturales, experiencias)."
    )


class RoadmapActions(BaseModel):
    """Acciones de la hoja de ruta separadas por atribución."""

    inversion_publica: List[str] = Field(
        description="Acciones concretas que requieren inversión o gestión pública (3-5 acciones)."
    )
    capacitacion_privada: List[str] = Field(
        description="Acciones concretas para capacitación o mejora del sector privado (3-5 acciones)."
    )


class ConsolidatedReport(BaseModel):
    """Briefing de Competitividad Estratégica para autoridades turísticas."""

    executive_summary: str = Field(
        description="Visión general del destino y principales hallazgos (3-4 oraciones)."
    )
    scorecard: Scorecard = Field(
        description="Scorecard de Eficiencia Turística con calificación 1-10 por pilar."
    )
    gap_diagnosis: List[str] = Field(
        description="Diagnóstico de brechas: recursos infrautilizados por fallas macro (públicas) o micro (privadas)."
    )
    roadmap: RoadmapActions = Field(
        description="Hoja de ruta: priorización de inversión pública vs capacitación privada."
    )
    cross_cutting_opportunities: List[str] = Field(
        description="Patrones transversales que afectan a múltiples tipos de negocio."
    )


class ParsedQuery(BaseModel):
    """Resultado del parseo de una consulta de usuario para el chat."""

    text_query: str = Field(description="Consulta de texto para búsqueda semántica.")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filtros para ChromaDB."
    )
    requires_report_context: bool = Field(
        default=False, description="Si la consulta requiere contexto del reporte."
    )
