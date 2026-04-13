from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Review(BaseModel):
    """Representa una reseña individual recuperada de ChromaDB."""

    id: str = Field(description="ID único de la reseña en ChromaDB.")
    texto: str = Field(description="Contenido de la reseña.")
    metadata: Dict[str, Any] = Field(
        description="Metadatos de la reseña (town, polarity, type, place, month, year)."
    )
    distancia: float = Field(description="Distancia de similitud desde la consulta.")


class AuditResult(BaseModel):
    """Resultado de la auditoría del reporte."""

    status: Literal["APROBADO", "RECHAZADO"]
    correcciones: List[str] = Field(
        default_factory=list, description="Correcciones necesarias si fue rechazado."
    )
    score_confianza: Optional[float] = Field(
        default=None, description="Puntuación de confianza del auditor (0-1)."
    )


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
    sugerencia_accionable: str = Field(
        description="Sugerencia accionable para abordar el insight."
    )


class ExtractedOpportunityInsightList(BaseModel):
    """Lista de insights extraídos por el LLM."""

    insights: List[ExtractedOpportunityInsight]


class OpportunityInsight(ExtractedOpportunityInsight):
    """Un insight de oportunidad completo con tipo de negocio."""

    tipo_negocio: str = Field(
        description="Tipo de negocio: 'Hotel', 'Restaurant', 'Attractive'."
    )


class OpportunityInsightList(BaseModel):
    """Lista de insights de oportunidad con tipo de negocio."""

    insights: List[OpportunityInsight]


class BusinessTypeReport(BaseModel):
    """Sección del reporte para un tipo de negocio específico."""

    tipo_negocio: str = Field(description="Tipo de negocio analizado.")
    total_resenas_analizadas: int = Field(description="Número de reseñas analizadas.")
    areas_oportunidad: List[OpportunityInsight] = Field(
        description="Lista de áreas de oportunidad identificadas."
    )
    fortalezas: List[str] = Field(description="Fortalezas identificadas.")
    resumen: str = Field(description="Resumen ejecutivo de la sección.")


class BusinessTypeSynthesis(BaseModel):
    """Resultado de la síntesis para un tipo de negocio (sin opportunity_areas, se añaden después)."""

    resumen: str = Field(description="Resumen ejecutivo de la sección.")
    fortalezas: List[str] = Field(description="Fortalezas identificadas.")
    diagnostico_brechas: List[str] = Field(
        description="Brechas identificadas: recursos infrautilizados por fallas públicas o privadas."
    )


class PillarScore(BaseModel):
    """Calificación de un pilar del scorecard."""

    score: int = Field(description="Calificación del 1 al 10.", ge=1, le=10)
    justificacion: str = Field(
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


class GapItem(BaseModel):
    """Una brecha individual identificada en el diagnóstico."""

    descripcion: str = Field(description="Descripción de la brecha.")
    evidencia: str = Field(description="Evidencia de las reseñas que la sustenta.")
    sugerencia: str = Field(description="Acción concreta para abordar la brecha.")


class GapDiagnosis(BaseModel):
    """Diagnóstico de brechas separado por atribución pública y privada."""

    publica: List[GapItem] = Field(
        description="Brechas atribuibles al gobierno (infraestructura, regulación, servicios públicos)."
    )
    privada: List[GapItem] = Field(
        description="Brechas atribuibles al sector privado (gestión, calidad de servicio, capacitación)."
    )


class ConsolidatedReport(BaseModel):
    """Briefing de Competitividad Estratégica para autoridades turísticas."""

    resumen_ejecutivo: str = Field(
        description="Visión general del destino y principales hallazgos (3-4 oraciones)."
    )
    scorecard: Scorecard = Field(
        description="Scorecard de Eficiencia Turística con calificación 1-10 por pilar."
    )
    diagnostico_brechas: GapDiagnosis = Field(
        description="Diagnóstico de brechas separado por atribución pública y privada."
    )
    roadmap: RoadmapActions = Field(
        description="Hoja de ruta: priorización de inversión pública vs capacitación privada."
    )
    oportunidades_transversales: List[str] = Field(
        description="Patrones transversales que afectan a múltiples tipos de negocio."
    )


class QueryFilters(BaseModel):
    """Filtros de metadata para consultas a ChromaDB."""

    tipo: Optional[str] = Field(
        default=None, description="Tipo de negocio: Hotel, Restaurant o Attractive."
    )
    polaridad: Optional[str] = Field(
        default=None, description="Polaridad de la reseña: positive o negative."
    )
    lugar: Optional[str] = Field(
        default=None, description="Nombre del lugar específico."
    )


class ParsedQuery(BaseModel):
    """Resultado del parseo de una consulta de usuario para el chat."""

    texto_consulta: str = Field(
        description="Consulta de texto para búsqueda semántica."
    )
    filtros: QueryFilters = Field(
        default_factory=QueryFilters, description="Filtros para ChromaDB."
    )
    requiere_contexto: bool = Field(
        default=False, description="Si la consulta requiere contexto del reporte."
    )
