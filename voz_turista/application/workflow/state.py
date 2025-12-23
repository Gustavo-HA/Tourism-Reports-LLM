import operator
from typing import Annotated, List, Optional, TypedDict, Dict, Any, Union
from langchain_core.messages import BaseMessage

class ProjectState(TypedDict):
    """
    Estado principal del grafo que gestiona el flujo de la aplicación.
    """
    # --- Entradas del Usuario ---
    pueblo_magico: str
    user_query: Optional[str] # Pregunta actual del usuario (si aplica)
    
    # --- Estado del Producto (Persistente) ---
    reporte_base: Optional[Dict[str, Any]] # Scorecard, Pros, Contras
    secciones_adicionales: Annotated[List[Dict[str, Any]], operator.add] # Historial de Deep Dives
    evidencia_recuperada: Dict[str, List[str]] # Mapeo ID -> Texto de evidencia
    
    # --- Control de Flujo ---
    next_step: str # 'map_reduce', 'deep_dive', 'end'
    
    # --- Estado Interno Map-Reduce ---
    reviews: List[str] # Lista completa de reviews (cargada de DB)
    review_chunks: List[List[str]] # Chunks para procesamiento paralelo
    extracted_insights: Annotated[List[Dict[str, Any]], operator.add] # Resultados del Map
    
    # --- Chat History ---
    messages: Annotated[List[BaseMessage], operator.add]

class ReviewChunkState(TypedDict):
    """
    Estado para el procesamiento de un chunk individual de reviews (Fase Map).
    """
    chunk_id: int
    reviews: List[str]
