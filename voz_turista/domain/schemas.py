from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

class Insight(BaseModel):
    """Estructura de un insight individual extraído de reseñas."""
    idx_review: List[str] = Field(description="IDs de referencia de las reseñas que sustentan el hallazgo.")
    insight: str = Field(description="Hallazgo conciso y accionable.")
    atribucion: Literal["Publica", "Privada"] = Field(description="Clasifica si el problema/oportunidad recae en el gobierno (Publica) o en los negocios privados (Privada).")
    dimension: Literal["Recurso Natural", "Servicio de Soporte", "Gestion de Destino"] = Field(description="Dimensión del hallazgo.")
    urgencia: Literal["Alta", "Media", "Baja"] = Field(description="Nivel de urgencia según el impacto en la competitividad turística.")

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
    scorecard: Dict[str, int] = Field(description="Puntajes por pilar (Infraestructura, Servicios, Atractivos).")
    gaps: List[str] = Field(description="Lista de brechas identificadas.")
    roadmap: Dict[str, List[str]] = Field(description="Hoja de ruta con acciones priorizadas (Publica vs Privada).")

class AuditResult(BaseModel):
    """Resultado de la auditoría del reporte."""
    status: Literal["APROBADO", "RECHAZADO"]
    corrections: Optional[List[str]] = Field(default=None, description="Correcciones necesarias si fue rechazado.")
