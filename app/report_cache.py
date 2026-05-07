"""On-disk persistent cache for generated reports (JSON + PDF)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.report_exporter import report_to_pdf

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")


def _paths(pueblo_magico: str) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(exist_ok=True)
    base = REPORTS_DIR / f"briefing_{pueblo_magico}"
    return base.with_suffix(".json"), base.with_suffix(".pdf")


def pdf_path_for(pueblo_magico: str) -> Path:
    _, pdf_path = _paths(pueblo_magico)
    return pdf_path


def load_cached_report(pueblo_magico: str) -> dict[str, Any] | None:
    json_path, _ = _paths(pueblo_magico)
    if not json_path.exists():
        return None
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(
            "Cache JSON corrupto para %s (%s); regenerando.", pueblo_magico, e
        )
        return None


def save_report_cache(pueblo_magico: str, report: dict[str, Any]) -> Path:
    """Persist JSON + PDF for the report. Returns the PDF path."""
    json_path, pdf_path = _paths(pueblo_magico)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pdf_path.write_bytes(report_to_pdf(report, pueblo_magico))
    logger.info("Reporte cacheado: %s", pdf_path)
    return pdf_path


def has_cache(pueblo_magico: str) -> bool:
    json_path, pdf_path = _paths(pueblo_magico)
    return json_path.exists() and pdf_path.exists()
