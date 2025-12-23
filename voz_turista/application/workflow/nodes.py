from typing import Dict, List, Any
from langchain_core.messages import SystemMessage, HumanMessage
from voz_turista.application.workflow.state import ProjectState, ReviewChunkState
from voz_turista.config import Config

# --- Mock Services (Reemplazar con implementaciones reales en Infrastructure) ---
def fetch_reviews(pueblo: str) -> List[str]:
    # Simulación de DB
    return [f"Review simulada {i} para {pueblo}" for i in range(150)]

def llm_analyze_chunk(reviews: List[str]) -> List[Dict[str, Any]]:
    return [{"insight": "Buena comida", "source_ids": [1, 2]}, {"insight": "Tráfico", "source_ids": [3]}]

def llm_synthesize(insights: List[Dict], pueblo: str) -> Dict[str, Any]:
    return {
        "scorecard": {"calidad": 4.5, "precio": 3.0},
        "lo_bueno": ["Gastronomía", "Paisajes"],
        "areas_oportunidad": ["Estacionamiento"],
        "consideraciones": ["Llevar efectivo"]
    }

def llm_generate_suggestions(report: Dict) -> List[str]:
    return ["¿Cómo es la seguridad de noche?", "¿Qué opciones veganas hay?", "¿Mejor época para ir?"]

def llm_rag_answer(query: str, context: List[str]) -> Dict[str, Any]:
    return {"pregunta": query, "respuesta": "Respuesta basada en RAG...", "fuentes": [10, 12]}

# --- Nodos del Grafo ---

def router_node(state: ProjectState):
    """
    Analiza el estado para decidir el siguiente paso.
    Si no hay reporte base o cambió el pueblo -> Map-Reduce.
    Si hay query y reporte -> Deep Dive.
    """
    print(f"--- Router: Analizando solicitud para {state.get('pueblo_magico')} ---")
    
    # Lógica simple: Si no hay reporte, generarlo.
    if not state.get("reporte_base"):
        # Cargar reviews aquí o en un nodo de carga
        reviews = fetch_reviews(state["pueblo_magico"])
        return {"next_step": "map_reduce", "reviews": reviews}
    
    if state.get("user_query"):
        return {"next_step": "deep_dive"}
        
    return {"next_step": "end"}

# --- Nodos Map-Reduce ---

def prepare_chunks_node(state: ProjectState):
    print("--- Preparando Chunks ---")
    reviews = state["reviews"]
    batch_size = Config.CHUNK_SIZE
    chunks = [reviews[i:i + batch_size] for i in range(0, len(reviews), batch_size)]
    return {"review_chunks": chunks}

def extract_insights_node(state: ReviewChunkState):
    # Fase Map
    # print(f"--- Extrayendo Insights Chunk {state['chunk_id']} ---")
    insights = llm_analyze_chunk(state["reviews"])
    return {"extracted_insights": insights}

def synthesize_report_node(state: ProjectState):
    print("--- Sintetizando Reporte (Reduce) ---")
    insights = state["extracted_insights"]
    pueblo = state["pueblo_magico"]
    
    report = llm_synthesize(insights, pueblo)
    
    # Consolidar evidencia (mock)
    evidencia = {str(i): f"Texto review {i}" for i in range(10)} 
    
    return {
        "reporte_base": report,
        "evidencia_recuperada": evidencia
    }

def generate_suggestions_node(state: ProjectState):
    print("--- Generando Sugerencias ---")
    report = state["reporte_base"]
    suggestions = llm_generate_suggestions(report)
    
    # Añadir sugerencias como mensaje del sistema
    msg = SystemMessage(content=f"Sugerencias: {', '.join(suggestions)}")
    
    return {"messages": [msg]}

# --- Nodos Deep Dive ---

def deep_dive_node(state: ProjectState):
    print(f"--- Deep Dive: {state['user_query']} ---")
    # Simulación RAG
    query = state["user_query"]
    # Retrieve context (mock)
    context = ["Contexto relevante 1", "Contexto relevante 2"]
    
    answer = llm_rag_answer(query, context)
    
    return {
        "secciones_adicionales": [answer],
        "messages": [HumanMessage(content=query), SystemMessage(content=answer["respuesta"])]
    }
