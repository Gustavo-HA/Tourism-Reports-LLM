"""Pequeno script de validacion manual de queries contra Chroma.

Ejemplo:
    python voz_turista/tools/validate_queries.py --limit 5 --top 3
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

# Asegura que el paquete voz_turista sea importable cuando se ejecuta como script
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voz_turista.infrastructure.database.chroma_client import ChromaClient  # noqa: E402


DEFAULT_QUERIES: List[Dict] = [
    {
        "label": "restaurant_servicio_rapidez",
        "town": "Isla Mujeres",
        "filters": {"type": "Restaurant"},
        "text_query": "staff servicio atencion tiempo",
    },
    {
        "label": "restaurant_Malservicio_Pocarapidez",
        "town": "Isla Mujeres",
        "filters": {"type": "Restaurant"},
        "text_query": "quejas sobre staff servicio atencion tiempo",
    },
]


def run_validation(
    client: ChromaClient, queries: List[Dict], limit: int, top: int
) -> None:
    for q in queries:
        print("=" * 80)
        print(f"Query: {q['label']}")
        print(f"Town: {q['town']} | Filters: {q.get('filters', {})} | Limit: {limit}")
        results = client.query_reviews(
            town=q["town"],
            limit=limit,
            filters=q.get("filters"),
            text_query=q["text_query"],
        )
        if not results:
            print("Sin resultados\n")
            continue
        for idx, r in enumerate(results[:top]):
            md = r.get("metadata", {})
            print(
                f"#{idx + 1} distance={r.get('distance'):.4f} town={md.get('town')} type={md.get('type')} polarity={md.get('polarity')}"
            )
            print(r.get("text", "")[:500])
            print("-")
    print("Validacion completada")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida queries sobre la coleccion Chroma."
    )
    parser.add_argument(
        "--persist_directory", default="data/chromadb/restmex_reduced_v2"
    )
    parser.add_argument("--collection_name", default="restmex_reduced_collection_v2")
    parser.add_argument(
        "--embedding_model",
        default="hiiamsid/sentence_similarity_spanish_es",
        help="Nombre del modelo de embeddings usado en la coleccion",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Numero de vecinos a recuperar"
    )
    parser.add_argument(
        "--top", type=int, default=5, help="Numero de resultados a mostrar"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = ChromaClient(
        persist_directory=args.persist_directory,
        collection_name=args.collection_name,
        embedding_model=args.embedding_model,
        device_preference="cuda",
    )
    run_validation(client, DEFAULT_QUERIES, limit=args.limit, top=args.top)


if __name__ == "__main__":
    main()
