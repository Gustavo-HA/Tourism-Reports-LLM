"""Report export utilities: Markdown formatting and PDF generation."""

import io
from datetime import datetime
from typing import Any, Dict

import markdown as md_lib
import weasyprint


def format_report_md(report: Dict[str, Any], pueblo_magico: str) -> str:
    """Format a consolidated report dict as Markdown."""
    lines = []
    pueblo_display = pueblo_magico.replace("_", " ")
    lines.append(f"# Briefing de Competitividad Estratégica: {pueblo_display}")
    lines.append(f"\n*Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # Executive summary
    lines.append("## Resumen Ejecutivo\n")
    lines.append(report.get("resumen_ejecutivo", "No disponible"))

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
                justification = pilar_data.get("justificacion", "-")
                lines.append(f"| {pilar.capitalize()} | {score}/10 | {justification} |")

    # Gap diagnosis (dict with publica/privada lists of GapItem dicts)
    gap_diag = report.get("diagnostico_brechas", {})
    if gap_diag:
        lines.append("\n## Diagnóstico de Brechas\n")
        publica_gaps = gap_diag.get("publica", []) if isinstance(gap_diag, dict) else []
        privada_gaps = gap_diag.get("privada", []) if isinstance(gap_diag, dict) else []
        if publica_gaps:
            lines.append("### Brechas Públicas *(gobierno / infraestructura)*\n")
            for gap in publica_gaps:
                desc = gap.get("descripcion", "") if isinstance(gap, dict) else str(gap)
                suggestion = gap.get("sugerencia", "") if isinstance(gap, dict) else ""
                lines.append(f"- **{desc}** — *{suggestion}*")
        if privada_gaps:
            lines.append("\n### Brechas Privadas *(gestión / sector privado)*\n")
            for gap in privada_gaps:
                desc = gap.get("descripcion", "") if isinstance(gap, dict) else str(gap)
                suggestion = gap.get("sugerencia", "") if isinstance(gap, dict) else ""
                lines.append(f"- **{desc}** — *{suggestion}*")

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
    cross = report.get("oportunidades_transversales", [])
    if cross:
        lines.append("\n## Oportunidades Transversales\n")
        for opp in cross:
            lines.append(f"- {opp}")

    # Per business type
    by_type = report.get("by_business_type", {})
    if by_type:
        lines.append("\n---\n")
        lines.append("## Detalle por Tipo de Negocio\n")
        for btype, breport in by_type.items():
            if hasattr(breport, "model_dump"):
                breport = breport.model_dump()
            total = breport.get("total_resenas_analizadas", 0)
            lines.append(f"### {btype} ({total} reseñas analizadas)\n")
            lines.append(f"{breport.get('resumen', 'N/A')}\n")
            strengths = breport.get("fortalezas", [])
            if strengths:
                lines.append("**Fortalezas:**\n")
                for s in strengths:
                    lines.append(f"- {s}")
            bgaps = breport.get("diagnostico_brechas", [])
            if bgaps:
                lines.append("\n**Brechas:**\n")
                for g in bgaps:
                    lines.append(f"- {g}")
            opps = breport.get("areas_oportunidad", [])
            if opps:
                lines.append("\n**Hallazgos:**\n")
                lines.append(
                    "| Urgencia | Atribución | Dimensión | Insight | Sugerencia |"
                )
                lines.append(
                    "|----------|------------|-----------|---------|------------|"
                )
                for opp in opps:
                    if hasattr(opp, "model_dump"):
                        opp = opp.model_dump()
                    lines.append(
                        f"| {opp.get('urgencia', '-')} "
                        f"| {opp.get('atribucion', '-')} "
                        f"| {opp.get('dimension', '-')} "
                        f"| {opp.get('insight', '-')} "
                        f"| {opp.get('sugerencia_accionable', '-')} |"
                    )
            lines.append("")

    return "\n".join(lines)


_PDF_CSS = """
@page {
    margin: 2cm 2.5cm;
    @bottom-right {
        content: counter(page);
        font-size: 9pt;
        color: #7f8c8d;
    }
}
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    color: #2c3e50;
    line-height: 1.5;
}
h1 {
    color: #1a5276;
    font-size: 18pt;
    border-bottom: 2px solid #1a5276;
    padding-bottom: 6px;
    margin-top: 0;
}
h2 {
    color: #2874a6;
    font-size: 14pt;
    border-bottom: 1px solid #aed6f1;
    padding-bottom: 4px;
    margin-top: 24px;
}
h3 {
    color: #2e86c1;
    font-size: 12pt;
    margin-top: 16px;
}
p {
    margin: 6px 0;
}
em {
    color: #7f8c8d;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 10pt;
}
th {
    background-color: #2874a6;
    color: white;
    padding: 8px 10px;
    text-align: left;
}
td {
    border: 1px solid #bdc3c7;
    padding: 7px 10px;
}
tr:nth-child(even) td {
    background-color: #f2f3f4;
}
ul, ol {
    margin: 6px 0;
    padding-left: 22px;
}
li {
    margin: 3px 0;
}
hr {
    border: none;
    border-top: 1px solid #bdc3c7;
    margin: 20px 0;
}
"""


def report_to_pdf(report: Dict[str, Any], pueblo_magico: str) -> bytes:
    """Convert a consolidated report dict to PDF bytes."""
    md_content = format_report_md(report, pueblo_magico)
    html_body = md_lib.markdown(
        md_content,
        extensions=["tables", "fenced_code"],
    )
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>{_PDF_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""
    buf = io.BytesIO()
    weasyprint.HTML(string=full_html).write_pdf(buf)
    return buf.getvalue()
