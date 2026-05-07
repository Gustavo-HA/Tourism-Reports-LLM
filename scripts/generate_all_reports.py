#!/usr/bin/env python
"""Bulk-generate consolidated reports for every Pueblo Mágico, persisting JSON+PDF.

Usage:
    python scripts/generate_all_reports.py            # all uncached pueblos
    python scripts/generate_all_reports.py --force    # regenerate everything
    python scripts/generate_all_reports.py --only Isla_Mujeres Bacalar
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.append(".")

from app.report_cache import has_cache, save_report_cache  # noqa: E402
from voz_turista.application.workflow import OpportunitySession  # noqa: E402
from voz_turista.config import settings  # noqa: E402
from voz_turista.domain.prompts.templates import SYSTEM_PROMPT_SPANISH  # noqa: E402
from voz_turista.infrastructure.llm_providers.litellm_provider import (  # noqa: E402
    LiteLLMProvider,
)

PUEBLOS_CSV = Path("data/PueblosMagicos/interim/unique_pueblos.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_pueblos() -> list[str]:
    with open(PUEBLOS_CSV, encoding="utf-8") as f:
        return [
            row["Pueblo"].strip() for row in csv.DictReader(f) if row["Pueblo"].strip()
        ]


def generate_one(pueblo: str, provider: LiteLLMProvider) -> None:
    session = OpportunitySession(pueblo, llm_provider=provider)
    report = session.generate_report()
    save_report_cache(pueblo, report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if cached.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Subset of pueblos to process (canonical underscored form).",
    )
    args = parser.parse_args()

    pueblos = args.only or load_pueblos()
    provider = LiteLLMProvider(
        model_name=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        system_prompt=SYSTEM_PROMPT_SPANISH,
    )

    ok, skipped = 0, 0
    failed: list[tuple[str, str]] = []
    for i, pueblo in enumerate(pueblos, 1):
        if not args.force and has_cache(pueblo):
            logger.info("[%d/%d] %s — cache hit, omitido.", i, len(pueblos), pueblo)
            skipped += 1
            continue
        logger.info("[%d/%d] %s — generando...", i, len(pueblos), pueblo)
        t0 = time.perf_counter()
        try:
            generate_one(pueblo, provider)
            logger.info("    OK en %.1fs", time.perf_counter() - t0)
            ok += 1
        except Exception as e:
            logger.exception("    FALLO: %s", e)
            failed.append((pueblo, str(e)))

    logger.info("Resumen: ok=%d, omitidos=%d, fallos=%d", ok, skipped, len(failed))
    for name, err in failed:
        logger.info("  - %s: %s", name, err)


if __name__ == "__main__":
    main()
