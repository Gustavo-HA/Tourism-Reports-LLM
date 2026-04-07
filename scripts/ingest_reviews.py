#!/usr/bin/env python
"""Pipeline to ingest Pueblo Mágico reviews into ChromaDB.

Usage examples:
    # Ingest a specific parquet file
    python scripts/ingest_reviews.py --parquet data/PueblosMagicos/interim/isla_mujeres.parquet

    # Ingest by pueblo name (filters main_dataset.parquet)
    python scripts/ingest_reviews.py --pueblo Isla_Mujeres

    # Ingest the full dataset
    python scripts/ingest_reviews.py --all

    # Override chunk and batch settings
    python scripts/ingest_reviews.py --pueblo Isla_Mujeres --chunk-size 300 --chunk-overlap 75 --batch-size 500
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.append(".")

from voz_turista.config import settings  # noqa: E402
from voz_turista.infrastructure.database.chroma_client import ChromaClient  # noqa: E402
from voz_turista.infrastructure.database.utils import read_restmex_dataframe  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

INTERIM_DIR = Path("data/PueblosMagicos/interim")
MAIN_DATASET = INTERIM_DIR / "main_dataset.parquet"


def build_client(device: str, upsert: bool) -> ChromaClient:
    return ChromaClient(
        persist_directory=settings.VECTOR_DB_PATH,
        collection_name=settings.VECTOR_DB_COLLECTION,
        embedding_model=settings.EMBEDDING_MODEL,
        device_preference=device,
        use_upsert=upsert,
    )


def ingest_file(parquet_path: Path, client: ChromaClient, chunk_size: int, chunk_overlap: int, batch_size: int) -> None:
    if not parquet_path.exists():
        logger.error("Archivo no encontrado: %s", parquet_path)
        sys.exit(1)

    logger.info("Ingesting: %s", parquet_path)
    client.ingest_restmex(
        parquet_path=str(parquet_path),
        batch_size=batch_size,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    logger.info("Completado: %s", parquet_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingesta reseñas de Pueblos Mágicos en ChromaDB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--parquet",
        metavar="PATH",
        help="Ruta directa al archivo Parquet a ingestar.",
    )
    source.add_argument(
        "--pueblo",
        metavar="NOMBRE",
        help=f"Nombre del Pueblo Mágico (e.g. Isla_Mujeres). Filtra por pueblo en {MAIN_DATASET}.",
    )
    source.add_argument(
        "--all",
        action="store_true",
        dest="all_data",
        help=f"Ingestar el dataset completo ({MAIN_DATASET}).",
    )

    parser.add_argument("--chunk-size", type=int, default=200, metavar="N", help="Tamaño del chunk (default: 200).")
    parser.add_argument("--chunk-overlap", type=int, default=50, metavar="N", help="Solapamiento entre chunks (default: 50).")
    parser.add_argument("--batch-size", type=int, default=1000, metavar="N", help="Tamaño del lote para ChromaDB (default: 1000).")
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Dispositivo para el modelo de embeddings (default: cuda, cae a cpu si no disponible).",
    )
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Usar upsert en lugar de add (actualiza documentos existentes).",
    )

    args = parser.parse_args()

    logger.info("Vector DB: %s / colección: %s", settings.VECTOR_DB_PATH, settings.VECTOR_DB_COLLECTION)
    logger.info("Embedding model: %s", settings.EMBEDDING_MODEL)
    logger.info("chunk_size=%d, chunk_overlap=%d, batch_size=%d", args.chunk_size, args.chunk_overlap, args.batch_size)

    client = build_client(device=args.device, upsert=args.upsert)

    if args.parquet:
        ingest_file(Path(args.parquet), client, args.chunk_size, args.chunk_overlap, args.batch_size)

    elif args.pueblo:
        if not MAIN_DATASET.exists():
            logger.error("Dataset principal no encontrado: %s", MAIN_DATASET)
            sys.exit(1)
        df = read_restmex_dataframe(str(MAIN_DATASET))
        filtered = df[df["Pueblo"] == args.pueblo]
        if filtered.empty:
            logger.error("No se encontraron reseñas para '%s' en %s", args.pueblo, MAIN_DATASET)
            sys.exit(1)
        logger.info("%d reseñas encontradas para '%s'", len(filtered), args.pueblo)
        client.ingest_dataframe(filtered, batch_size=args.batch_size, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)

    else:  # --all
        ingest_file(MAIN_DATASET, client, args.chunk_size, args.chunk_overlap, args.batch_size)


if __name__ == "__main__":
    main()
