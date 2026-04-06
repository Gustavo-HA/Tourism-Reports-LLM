#!/usr/bin/env python
"""Test script for the Opportunity Workflow. Outputs a Markdown report."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import mlflow

load_dotenv()

sys.path.append(".")

from voz_turista.application.workflow import OpportunitySession  # noqa: E402
from voz_turista.config import settings  # noqa: E402
from voz_turista.infrastructure.llm_providers.litellm_provider import LiteLLMProvider  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

mlflow.set_experiment("Tourism Report Generation - Testing")
mlflow.langchain.autolog()

def format_report_md(report: dict, pueblo_magico: str) -> str:
    """Format the generated report as Markdown."""
    lines = []
    lines.append(f"# Briefing de Competitividad Estratégica: {pueblo_magico}")
    lines.append(f"\n*Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # Executive summary
    lines.append("## Resumen Ejecutivo\n")
    lines.append(report.get("executive_summary", "No disponible"))

    # Scorecard
    scorecard = report.get("scorecard", {})
    if scorecard:
        lines.append("\n## Scorecard de Eficiencia Turística\n")
        lines.append("| Pilar | Calificación | Justificación |")
        lines.append("|-------|:------------:|---------------|")
        for pilar in ["infraestructura", "servicios", "atractivos"]:
            pilar_data = scorecard.get(pilar, {})
            if isinstance(pilar_data, dict):
                score = pilar_data.get("score", "N/A")
                justification = pilar_data.get("justification", "-")
                lines.append(f"| {pilar.capitalize()} | {score}/10 | {justification} |")

    # Gap diagnosis
    gaps = report.get("gap_diagnosis", [])
    if gaps:
        lines.append("\n## Diagnóstico de Brechas\n")
        for gap in gaps:
            lines.append(f"- {gap}")

    # Roadmap
    roadmap = report.get("roadmap", {})
    if roadmap:
        lines.append("\n## Hoja de Ruta\n")
        pub = roadmap.get("inversion_publica") or []
        if pub:
            lines.append("### Inversión Pública\n")
            for i, action in enumerate(pub, 1):
                lines.append(f"{i}. {action}")
        priv = roadmap.get("capacitacion_privada") or []
        if priv:
            lines.append("\n### Capacitación Privada\n")
            for i, action in enumerate(priv, 1):
                lines.append(f"{i}. {action}")

    # Cross-cutting opportunities
    cross = report.get("cross_cutting_opportunities", [])
    if cross:
        lines.append("\n## Oportunidades Transversales\n")
        for opp in cross:
            lines.append(f"- {opp}")

    # Per business type
    lines.append("\n---\n")
    lines.append("## Detalle por Tipo de Negocio\n")

    for btype, breport in report.get("by_business_type", {}).items():
        total = breport.get("total_reviews_analyzed", 0)
        lines.append(f"### {btype} ({total} reseñas analizadas)\n")
        lines.append(f"{breport.get('summary', 'N/A')}\n")

        strengths = breport.get("strengths", [])
        if strengths:
            lines.append("**Fortalezas:**\n")
            for s in strengths:
                lines.append(f"- {s}")

        bgaps = breport.get("gap_diagnosis", [])
        if bgaps:
            lines.append("\n**Brechas:**\n")
            for g in bgaps:
                lines.append(f"- {g}")

        opps = breport.get("opportunity_areas", [])
        if opps:
            lines.append("\n**Hallazgos:**\n")
            lines.append("| Urgencia | Atribución | Dimensión | Insight | Sugerencia |")
            lines.append("|----------|------------|-----------|---------|------------|")
            for opp in opps:
                lines.append(
                    f"| {opp.get('urgencia', '-')} "
                    f"| {opp.get('atribucion', '-')} "
                    f"| {opp.get('dimension', '-')} "
                    f"| {opp.get('insight', '-')} "
                    f"| {opp.get('actionable_suggestion', '-')} |"
                )
        lines.append("")

    return "\n".join(lines)


def format_chat_md(queries: list[str], responses: list[str]) -> str:
    """Format chat exchanges as Markdown."""
    lines = []
    lines.append("## Chat Interactivo\n")
    for query, response in zip(queries, responses):
        lines.append(f"**Usuario:** {query}\n")
        lines.append(f"**Asistente:** {response}\n")
        lines.append("---\n")
    return "\n".join(lines)


def main():
    pueblo_magico = sys.argv[1] if len(sys.argv) > 1 else "Isla_Mujeres"

    logger.info("Iniciando workflow para: %s", pueblo_magico)

    with mlflow.start_run():
        mlflow.log_params(
            {
                "pueblo_magico": pueblo_magico,
                "llm_model": settings.LLM_MODEL,
                "llm_temperature": settings.LLM_TEMPERATURE,
                "embedding_model": settings.EMBEDDING_MODEL,
                "vector_db_path": settings.VECTOR_DB_PATH,
                "reranker_model": settings.RERANKER_MODEL or "disabled",
            }
        )

        llm_provider = LiteLLMProvider(
            model_name=settings.LLM_MODEL, temperature=settings.LLM_TEMPERATURE
        )
        session = OpportunitySession(pueblo_magico, llm_provider=llm_provider)

        # Phase 1: Generate Report
        logger.info("Fase 1: Generando reporte...")
        report = session.generate_report()
        report_md = format_report_md(report, pueblo_magico)

        # Phase 2: Chat
        logger.info("Fase 2: Ejecutando consultas de chat...")
        test_queries = [
            "Cuales son las principales quejas sobre hoteles?",
            "Que problemas de servicio tienen los restaurantes?",
            "Dame ejemplos de resenas negativas sobre limpieza",
        ]

        responses = []
        for query in test_queries:
            logger.info("  -> %s...", query[:50])
            responses.append(session.chat(query))

        chat_md = format_chat_md(test_queries, responses)

        # Combine and write output
        full_md = f"{report_md}\n{chat_md}"

        output_dir = Path("reports")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"opportunity_{pueblo_magico}.md"
        output_path.write_text(full_md, encoding="utf-8")

        mlflow.log_artifact(str(output_path))
        logger.info("Reporte guardado en: %s", output_path)


if __name__ == "__main__":
    main()
