"""
Retrieve a complete review from ChromaDB by source_id or chunk_id.

Usage:
    python scripts/get_review_by_id.py <source_id_or_chunk_id>

If a chunk ID is given (e.g. "abc123_2"), the script strips the chunk suffix
and retrieves all chunks for that source review.
"""

import argparse
import os
import sys
import textwrap

from dotenv import load_dotenv

load_dotenv()

VECTOR_DB_PATH = os.environ["VECTOR_DB_PATH"]
VECTOR_DB_COLLECTION = os.environ["VECTOR_DB_COLLECTION"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]


def get_review(source_id: str) -> None:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_collection(
        name=VECTOR_DB_COLLECTION,
        embedding_function=SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL,
            device="cpu",
        ),
    )

    results = collection.get(
        where={"source_id": source_id},
        include=["documents", "metadatas"],
    )

    if not results["ids"]:
        print(f"No chunks found for source_id: {source_id}")
        sys.exit(1)

    # Sort chunks by chunk_index to reconstruct original text order
    chunks = sorted(
        zip(results["ids"], results["documents"], results["metadatas"]),
        key=lambda x: x[2].get("chunk_index", 0),
    )

    metadata = chunks[0][2]
    n = len(chunks)

    width = 62
    sep = "=" * width
    thin = "-" * width

    print(sep)
    print(f"  REVIEW  —  {source_id}")
    print(sep)
    print(f"  Lugar      : {metadata.get('place', '—').replace('_', ' ')}")
    print(f"  Pueblo     : {metadata.get('town', '—').replace('_', ' ')}")
    print(f"  Tipo       : {metadata.get('type', '—')}")
    print(f"  Calificación: {metadata.get('polarity', '—')}/5")
    print(f"  Fecha      : {metadata.get('month'):02d}/{metadata.get('year')}")
    print(f"  Chunks     : {n}")
    print(sep)

    for chunk_id, doc, _ in chunks:
        idx = chunk_id.rsplit("_", 1)[-1]
        print(f"\n  [chunk {idx}]")
        print(thin)
        for line in textwrap.wrap(doc.strip(), width=width - 2):
            print(f"  {line}")

    print(f"\n{sep}")


def main():
    parser = argparse.ArgumentParser(description="Retrieve a full review from ChromaDB by ID.")
    parser.add_argument("id", help="source_id or chunk_id (e.g. 'abc123' or 'abc123_2')")
    args = parser.parse_args()

    raw_id = args.id
    # Strip chunk suffix if a full chunk id was provided
    parts = raw_id.rsplit("_", 1)
    if len(parts) == 2 and parts[1].isdigit():
        source_id = parts[0]
    else:
        source_id = raw_id

    get_review(source_id)


if __name__ == "__main__":
    main()
