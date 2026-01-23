import operator
from typing import Annotated, List, Optional, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage


class Review(TypedDict):
    """Representa una reseña individual recuperada de ChromaDB."""

    id: str
    text: str
    metadata: Dict[str, Any]


class Insight(TypedDict):
    """Representa un hallazgo extraído de un lote de reseñas."""

    idx_review: List[str]  # IDs de referencia
    insight: str  # Hallazgo conciso
    atribucion: str  # 'Pública' | 'Privada'
    dimension: str  # 'Recurso Natural' | 'Servicio de Soporte' | 'Gestión de Destino'
    urgencia: str  # 'Alta' | 'Media' | 'Baja'


class ProjectState(TypedDict):
    """
    Estado principal del grafo que gestiona el flujo de la aplicación.
    """

    # --- Entradas del Usuario ---
    pueblo_magico: str
    user_query: Optional[str]  # Pregunta actual del usuario (si aplica)

    # --- Datos del Proceso ---
    reviews: List[Review]  # Reseñas recuperadas para el análisis
    insights: Annotated[
        List[Insight], operator.add
    ]  # Lista acumulativa de insights extraídos (Map phase)

    # --- Estado del Producto (Persistente) ---
    reporte_base: Optional[
        Dict[str, Any]
    ]  # El "Briefing de Competitividad Estratégica" (Reduce phase)
    auditoria: Optional[Dict[str, Any]]  # Resultado del nodo Auditor (Self-Correction)

    # --- Control de Flujo ---
    iteration_count: int  # Para evitar ciclos infinitos en self-correction

    # --- Chat History (Opcional para interacción futura) ---
    messages: Annotated[List[BaseMessage], operator.add]


class ReviewChunkState(TypedDict):
    """
    Estado para el procesamiento de un chunk individual de reviews (Fase Map).
    """

    chunk_id: int
    reviews: List[Review]
