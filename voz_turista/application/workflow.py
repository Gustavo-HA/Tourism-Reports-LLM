from typing import List, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from voz_turista.domain.schemas import InsightList, FullReport, AuditResult
from voz_turista.domain.prompts.templates import SYSTEM_PROMPT_EXTRACT, SYSTEM_PROMPT_SYNTHESIZE, SYSTEM_PROMPT_AUDITOR
from voz_turista.infrastructure.database.chroma_client import ChromaClient
from voz_turista.infrastructure.llm_providers.google_provider import LangChainGoogleProvider

# --- State ---
class ReportState(TypedDict):
    town: str
    reviews_hotel: List[str]
    reviews_restaurant: List[str]
    reviews_attraction: List[str]
    insights_hotel: List[dict]
    insights_restaurant: List[dict]
    insights_attraction: List[dict]
    final_report: dict
    audit_result: dict

# --- Nodes ---

def retrieve_data(state: ReportState):
    """Retrieves reviews for each category from ChromaDB."""
    town = state["town"]
    # Initialize ChromaClient (Assuming shared instance or creating new one here for simplicity)
    # TODO: In production, inject this dependency.
    chroma = ChromaClient(
        persist_directory="data/chromadb/restmex_sss_cs200_ov50", # Adjust path as needed
        collection_name="restmex_sss_cs200_ov50",
        embedding_model="hiiamsid/sentence_similarity_spanish_es",
        device_preference="cpu" # Use CPU to be safe/compatible
    )
    
    # Helper to query
    def get_reviews(category_filter):
        results = chroma.query_reviews(
            town=town,
            limit=20, # Initial limit
            text_query="Problemas, quejas, sugerencias y experiencias negativas o positivas relevantes.", # Broad query for insights
            filters=category_filter
        )
        return [r["text"] for r in results]

    return {
        "reviews_hotel": get_reviews({"type": "Hotel"}),
        "reviews_restaurant": get_reviews({"type": "Restaurant"}),
        "reviews_attraction": get_reviews({"type": "Attractive"}) 
    }

def analyze_category(state: ReportState, category: str, output_key: str):
    """Generic node to analyze a specific category."""
    town = state["town"]
    reviews = state.get(f"reviews_{category}", [])
    
    if not reviews:
        return {output_key: []}

    reviews_text = "\n\n".join(reviews)
    
    llm = LangChainGoogleProvider()
    prompt = SYSTEM_PROMPT_EXTRACT.format(pueblo_magico=town, reviews=reviews_text)
    
    try:
        result: InsightList = llm.generate_structured(
            messages=[HumanMessage(content=prompt)],
            schema=InsightList
        )
        return {output_key: [i.model_dump() for i in result.insights]}
    except Exception as e:
        print(f"Error analyzing {category}: {e}")
        return {output_key: []}

def analyze_hotels(state: ReportState):
    return analyze_category(state, "hotel", "insights_hotel")

def analyze_restaurants(state: ReportState):
    return analyze_category(state, "restaurant", "insights_restaurant")

def analyze_attractions(state: ReportState):
    return analyze_category(state, "attraction", "insights_attraction")

def synthesize_report(state: ReportState):
    """Aggregates insights and generates the briefing."""
    town = state["town"]
    all_insights = (
        state.get("insights_hotel", []) + 
        state.get("insights_restaurant", []) + 
        state.get("insights_attraction", [])
    )
    
    insights_text = str(all_insights) # Dump as string representation
    
    llm = LangChainGoogleProvider()
    prompt = SYSTEM_PROMPT_SYNTHESIZE.format(pueblo_magico=town, insights=insights_text)
    
    try:
        result: FullReport = llm.generate_structured(
            messages=[HumanMessage(content=prompt)],
            schema=FullReport
        )
        return {"final_report": result.model_dump()}
    except Exception as e:
        print(f"Error synthesizing report: {e}")
        return {"final_report": {}}

def audit_report(state: ReportState):
    """Audits the generated report against original reviews."""
    town = state["town"]
    report = state.get("final_report", {})
    
    # Collecting evidence (sample from each)
    evidence = (
        state.get("reviews_hotel", [])[:5] + 
        state.get("reviews_restaurant", [])[:5] + 
        state.get("reviews_attraction", [])[:5]
    )
    evidence_text = "\n\n".join(evidence)
    
    llm = LangChainGoogleProvider()
    prompt = SYSTEM_PROMPT_AUDITOR.format(
        pueblo_magico=town, 
        report=str(report), 
        evidence=evidence_text
    )
    
    try:
        result: AuditResult = llm.generate_structured(
            messages=[HumanMessage(content=prompt)],
            schema=AuditResult
        )
        return {"audit_result": result.model_dump()}
    except Exception as e:
        print(f"Error auditing report: {e}")
        return {"audit_result": {"status": "ERROR"}}

# --- Graph Builder ---

def build_workflow():
    workflow = StateGraph(ReportState)
    
    workflow.add_node("retrieve_data", retrieve_data)
    workflow.add_node("analyze_hotels", analyze_hotels)
    workflow.add_node("analyze_restaurants", analyze_restaurants)
    workflow.add_node("analyze_attractions", analyze_attractions)
    workflow.add_node("synthesize", synthesize_report)
    workflow.add_node("audit", audit_report)
    
    workflow.set_entry_point("retrieve_data")
    
    # Parallel analysis
    workflow.add_edge("retrieve_data", "analyze_hotels")
    workflow.add_edge("retrieve_data", "analyze_restaurants")
    workflow.add_edge("retrieve_data", "analyze_attractions")
    
    # Converge to synthesize
    workflow.add_edge("analyze_hotels", "synthesize")
    workflow.add_edge("analyze_restaurants", "synthesize")
    workflow.add_edge("analyze_attractions", "synthesize")
    
    workflow.add_edge("synthesize", "audit")
    workflow.add_edge("audit", END)
    
    return workflow.compile()
