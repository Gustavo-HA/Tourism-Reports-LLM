import uuid
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from .utils import normalize_town_name, prepare_restmex_dataframe


class ChromaClient:
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedding_model: str,
        device_preference: str = "cuda",
        use_upsert: bool = False,
    ):
        """Inicializa el cliente de ChromaDB."""
        self.collection_name = collection_name
        self.use_upsert = use_upsert

        device = device_preference
        try:
            import torch

            if device_preference == "cuda" and not torch.cuda.is_available():
                device = "cpu"
        except Exception:
            device = "cpu" if device_preference == "cuda" else device_preference

        self.embedding_device = device

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=SentenceTransformerEmbeddingFunction(
                model_name=embedding_model,
                device=device,
            ),
            configuration={
                "hnsw": {
                    "space": "cosine",
                    "ef_search": 200,
                    "ef_construction": 200,
                }
            },
        )

    def ingest_restmex_csv(
        self,
        csv_path: str,
        batch_size: int = 500,
        output_clean_csv: str | None = None,
    ) -> None:
        """Ingesta datos desde un archivo CSV a ChromaDB con limpieza y desduplicación."""
        df_clean = prepare_restmex_dataframe(csv_path)

        if output_clean_csv:
            Path(output_clean_csv).parent.mkdir(parents=True, exist_ok=True)
            df_clean.to_csv(output_clean_csv, index=False)
            print(f"CSV limpio escrito en: {output_clean_csv}")

        total_records = len(df_clean)
        print(f"Procesando {total_records} reseñas válidas...")

        texts = df_clean["text"].astype(str).tolist()
        towns = df_clean["TownNormalized"].astype(str).tolist()
        towns_raw = df_clean["Town"].astype(str).tolist()
        polarities = df_clean["Polarity"].astype(float).tolist()
        types = df_clean["Type"].astype(str).tolist()
        regions = df_clean["Region"].astype(str).tolist()

        ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc)) for doc in texts]

        total_lotes = (total_records + batch_size - 1) // batch_size

        add_fn = (
            self.collection.upsert
            if self.use_upsert and hasattr(self.collection, "upsert")
            else self.collection.add
        )

        for i in range(0, total_records, batch_size):
            end_idx = min(i + batch_size, total_records)

            batch_documents = texts[i:end_idx]
            batch_ids = ids[i:end_idx]

            batch_metadatas = [
                {
                    "town": towns[k],
                    "town_raw": towns_raw[k],
                    "polarity": polarities[k],
                    "type": types[k],
                    "region": regions[k],
                }
                for k in range(i, end_idx)
            ]

            try:
                add_fn(
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    ids=batch_ids,
                )
                print(f"Lote procesado: {i // batch_size + 1} / {total_lotes}")
            except Exception as e:
                print(f"Error en el lote {i}: {e}")

        print("Ingesta completada exitosamente.")

    def query_reviews(
        self,
        town: str,
        limit: int = 100,
        filters: Dict[str, Any] = None,
        text_query: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Recupera reseñas filtradas por pueblo y otros criterios.

        Args:
            town (str): Nombre del Pueblo Mágico.
            limit (int): Número máximo de reseñas a recuperar.
            filters (Dict): Filtros adicionales (ej. {'type': 'Restaurant'}).

        Returns:
            List[Dict]: Lista de reseñas con sus metadatos.
        """
        if not text_query:
            raise ValueError(
                "Se requiere un texto de consulta no vacío para realizar la búsqueda."
            )

        town_norm = normalize_town_name(town)

        if filters:
            conditions = [{"town": town_norm}]
            for key, value in filters.items():
                conditions.append({key: value})
            where_clause = {"$and": conditions}
        else:
            where_clause = {"town": town_norm}

        results = self.collection.query(
            query_texts=[text_query],
            n_results=limit,
            where=where_clause,
        )

        reviews = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                reviews.append(
                    {
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                    }
                )

        return reviews


if __name__ == "__main__":
    # Ejemplo de ingesta (nueva versión limpia)
    client = ChromaClient(
        persist_directory="data/chromadb/restmex_reduced_v2",
        collection_name="restmex_reduced_collection_v2",
        embedding_model="hiiamsid/sentence_similarity_spanish_es",
        device_preference="cuda",
        use_upsert=True,
    )
    client.ingest_restmex_csv(
        csv_path="data/restmex/restmex-corpus-reduced.csv",
        batch_size=500,
        output_clean_csv="data/restmex/restmex-corpus-reduced-v2.csv",
    )

    # Ejemplo de consulta
    # client = ChromaClient(
    #     persist_directory="data/chromadb/restmex_reduced_v2",
    #     collection_name="restmex_reduced_collection_v2",
    #     embedding_model="hiiamsid/sentence_similarity_spanish_es",
    # )
    # filters = {"type": "Restaurant"}
    # reviews = client.query_reviews(
    #     town="Isla Mujeres",
    #     limit=5,
    #     text_query="Comentarios sobre el tiempo de espera entre tiempos, la disponibilidad de mesas y la rapidez del servicio de facturación.",
    #     filters=filters,
    # )
    # for review in reviews:
    #     print(f"ID: {review['id']}\nTexto: {review['text']}\nMetadatos: {review['metadata']}\nDistance: {review.get('score', 'N/A')}\n---\n")
    pass
