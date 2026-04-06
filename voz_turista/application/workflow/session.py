"""Session management for Opportunity Workflow."""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from voz_turista.application.workflow.graph import (
    build_chat_workflow,
    build_report_workflow,
)
from voz_turista.application.workflow.nodes import set_llm_provider
from voz_turista.infrastructure.llm_providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpportunitySession:
    """
    Manages a complete opportunity analysis session.

    Usage:
        from voz_turista.infrastructure.llm_providers.litellm_provider import LiteLLMProvider

        provider = LiteLLMProvider(model_name="gemini/gemini-2.5-flash")
        session = OpportunitySession("Isla_Mujeres", llm_provider=provider)

        # Generate the report
        report = session.generate_report()
        print(report)

        # Interactive chat
        response = session.chat("Muestrame quejas sobre hoteles")
        print(response)

        response = session.chat("Que restaurantes tienen problemas de servicio?")
        print(response)
    """

    def __init__(self, pueblo_magico: str, llm_provider: LLMProvider):
        """
        Initialize the session.

        Args:
            pueblo_magico: Name of the Pueblo Magico to analyze
        """
        set_llm_provider(llm_provider)
        self.pueblo_magico = pueblo_magico
        self.report_app = build_report_workflow()
        self.chat_app = build_chat_workflow()
        self.report: Optional[Dict[str, Any]] = None
        self.messages: List[BaseMessage] = []

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate the opportunity areas report.

        Returns:
            The consolidated report dictionary
        """
        logger.info("Generando reporte de oportunidades para %s", self.pueblo_magico)

        result = self.report_app.invoke({"pueblo_magico": self.pueblo_magico})

        self.report = result.get("consolidated_report", {})
        return self.report

    def chat(self, user_message: str) -> str:
        """
        Send a chat message and get a response.

        Args:
            user_message: The user's query

        Returns:
            The assistant's response
        """
        if self.report is None:
            return "Error: Primero debes generar el reporte con generate_report()"

        result = self.chat_app.invoke(
            {
                "pueblo_magico": self.pueblo_magico,
                "consolidated_report": self.report,
                "user_message": user_message,
                "messages": self.messages,
            }
        )

        response = result.get("response", "No se pudo generar una respuesta.")

        # Update message history
        self.messages.append(HumanMessage(content=user_message))
        self.messages.append(AIMessage(content=response))

        return response

    def get_report_summary(self) -> str:
        """Get a formatted summary of the report."""
        if self.report is None:
            return "No hay reporte generado."

        summary = f"""
{'='*60}
BRIEFING DE COMPETITIVIDAD ESTRATEGICA: {self.report.get('pueblo_magico', self.pueblo_magico)}
{'='*60}

RESUMEN EJECUTIVO:
{self.report.get('executive_summary', 'No disponible')}

SCORECARD DE EFICIENCIA TURISTICA:
"""
        scorecard = self.report.get("scorecard", {})
        for pilar in ["infraestructura", "servicios", "atractivos"]:
            pilar_data = scorecard.get(pilar, {})
            if isinstance(pilar_data, dict):
                score = pilar_data.get("score", "N/A")
                justification = pilar_data.get("justification", "")
                summary += f"  {pilar.upper()}: {score}/10 — {justification}\n"

        summary += "\nDIAGNOSTICO DE BRECHAS:\n"
        for gap in self.report.get("gap_diagnosis", []):
            summary += f"  - {gap}\n"

        summary += "\nHOJA DE RUTA:\n"
        roadmap = self.report.get("roadmap", {})
        summary += "  Inversion Publica:\n"
        for action in (roadmap.get("inversion_publica") or []):
            summary += f"    - {action}\n"
        summary += "  Capacitacion Privada:\n"
        for action in (roadmap.get("capacitacion_privada") or []):
            summary += f"    - {action}\n"

        summary += "\nOPORTUNIDADES TRANSVERSALES:\n"
        for opp in self.report.get("cross_cutting_opportunities", []):
            summary += f"  - {opp}\n"

        summary += f"\n{'='*60}\n"
        summary += "POR TIPO DE NEGOCIO:\n"

        for btype, breport in self.report.get("by_business_type", {}).items():
            summary += f"\n{btype}:\n"
            summary += f"  Resenas analizadas: {breport.get('total_reviews_analyzed', 0)}\n"
            summary += f"  Resumen: {breport.get('summary', 'N/A')[:200]}...\n"
            summary += f"  Hallazgos: {len(breport.get('opportunity_areas', []))}\n"
            summary += f"  Brechas: {len(breport.get('gap_diagnosis', []))}\n"

        return summary

    def clear_chat_history(self) -> None:
        """Clear the chat message history."""
        self.messages = []
        logger.info("Historial de chat limpiado.")
