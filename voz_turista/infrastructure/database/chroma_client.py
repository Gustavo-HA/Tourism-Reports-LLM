import logging
import uuid
from typing import Any, Dict, List

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .utils import read_restmex_dataframe

logger = logging.getLogger(__name__)


class ChromaClient:
    def __init__(
        self,
        persist_directory: str,
        collection_name: str,
        embedding_model: str,
        device_preference: str = "cuda",
        use_upsert: bool = False,
        reranker_model: str | None = None,
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

        # Lazy-loaded cross-encoder reranker
        self._reranker = None
        self._reranker_model = reranker_model

    @property
    def reranker(self):
        """Lazily load the CrossEncoder reranker on first use."""
        if self._reranker is None and self._reranker_model is not None:
            from sentence_transformers import CrossEncoder

            logger.info("Cargando reranker: %s", self._reranker_model)
            self._reranker = CrossEncoder(
                self._reranker_model, device=self.embedding_device
            )
        return self._reranker

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        batch_size: int = 1000,
    ) -> None:
        """
        Agrega o actualiza documentos en la colección de forma genérica y por lotes.
        """
        total_records = len(documents)
        total_lotes = (total_records + batch_size - 1) // batch_size
        logger.info(f"Ingestando {total_records} documentos en {total_lotes} lotes...")

        add_fn = (
            self.collection.upsert
            if self.use_upsert and hasattr(self.collection, "upsert")
            else self.collection.add
        )

        for i in range(0, total_records, batch_size):
            end_idx = min(i + batch_size, total_records)

            batch_docs = documents[i:end_idx]
            batch_metas = metadatas[i:end_idx]
            batch_ids = ids[i:end_idx]

            try:
                add_fn(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                )
                logger.info(f"Lote procesado: {i // batch_size + 1} / {total_lotes}")
            except Exception as e:
                logger.error(f"Error en el lote {i}: {e}")

        logger.info("Operación completada.")

    def ingest_dataframe(
        self,
        df,
        batch_size: int = 1000,
        chunk_size: int = 200,
        chunk_overlap: int = 50,
    ) -> None:
        """
        Ingesta un DataFrame de reseñas RESTMEX a ChromaDB con soporte para chunking.
        """
        import pandas as pd

        logger.info(f"Procesando {len(df)} registros originales...")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        all_documents = []
        all_metadatas = []
        all_ids = []

        for row in df.itertuples(index=False):
            original_text = row.text
            if not isinstance(original_text, str) or not original_text.strip():
                continue

            chunks = text_splitter.split_text(original_text)
            composite_key = (
                f"{row.Pueblo}-{row.Lugar}-{row.FechaEstadia}-{original_text}"
            )
            base_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, composite_key))

            for i, chunk in enumerate(chunks):
                chunk_id = f"{base_id}_{i}"
                metadata = {
                    "town": row.Pueblo,
                    "polarity": row.Calificacion,
                    "type": row.Tipo,
                    "place": row.Lugar,
                    "month": row.FechaEstadia.month,
                    "year": row.FechaEstadia.year,
                    "source_id": base_id,
                    "chunk_index": i,
                }

                all_documents.append(chunk)
                all_metadatas.append(metadata)
                all_ids.append(chunk_id)

        self.add_documents(
            documents=all_documents,
            metadatas=all_metadatas,
            ids=all_ids,
            batch_size=batch_size,
        )

    def ingest_restmex(
        self,
        parquet_path: str,
        batch_size: int = 1000,
        chunk_size: int = 200,
        chunk_overlap: int = 50,
    ) -> None:
        """
        Ingesta datos desde un archivo Parquet a ChromaDB con soporte para chunking.
        """
        df = read_restmex_dataframe(parquet_path)
        self.ingest_dataframe(
            df,
            batch_size=batch_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def query_reviews(
        self,
        town: str,
        limit: int = 100,
        filters: Dict[str, Any] = None,
        text_query: str = "",
        rerank: bool = True,
        overfetch_factor: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Recupera reseñas filtradas por pueblo y otros criterios.
        Opcionalmente aplica reranking con un cross-encoder.

        Args:
            town (str): Nombre del Pueblo Mágico.
            limit (int): Número máximo de reseñas a retornar.
            filters (Dict): Filtros adicionales (ej. {'type': 'Restaurant'}).
            text_query (str): Texto de consulta para búsqueda semántica.
            rerank (bool): Si True y hay un reranker configurado, aplica reranking.
            overfetch_factor (int): Factor de sobre-recuperación para el reranker.

        Returns:
            List[Dict]: Lista de reseñas con sus metadatos.
        """
        if not text_query:
            raise ValueError(
                "Se requiere un texto de consulta no vacío para realizar la búsqueda."
            )

        if filters:
            conditions = [{"town": town}]
            for key, value in filters.items():
                if isinstance(value, list):
                    # Para cuando abarcamos varios valores de un metadato.
                    conditions.append({key: {"$in": value}})
                else:
                    conditions.append({key: value})
            where_clause = {"$and": conditions}
        else:
            where_clause = {"town": town}

        # Over-fetch if reranking is enabled
        use_reranker = rerank and self.reranker is not None
        fetch_limit = limit * overfetch_factor if use_reranker else limit

        results = self.collection.query(
            query_texts=[text_query],
            n_results=fetch_limit,
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

        # Stage 2: Rerank with cross-encoder
        if use_reranker and len(reviews) > 0:
            logger.info("Reranking %d candidatos -> top %d", len(reviews), limit)
            pairs = [(text_query, r["text"]) for r in reviews]
            scores = self.reranker.predict(pairs)
            for review, score in zip(reviews, scores):
                review["rerank_score"] = float(score)
            reviews.sort(key=lambda r: r["rerank_score"], reverse=True)
            reviews = reviews[:limit]

        return reviews


if __name__ == "__main__":
    # Ejemplo de ingesta (nueva versión limpia)
    # client = ChromaClient(
    #     persist_directory="data/chromadb/restmex_sss_cs200_ov50",
    #     collection_name="restmex_sss_cs200_ov50",
    #     embedding_model="hiiamsid/sentence_similarity_spanish_es",
    #     device_preference="cuda",
    #     use_upsert=True,
    # )
    # client.ingest_restmex(
    #     parquet_path="data/PueblosMagicos/interim/isla_mujeres.parquet",
    #     batch_size=1000,
    #     chunk_size=200,
    #     chunk_overlap=50,
    # )

    # Ejemplo de consulta
    # client = ChromaClient(
    #     persist_directory="data/chromadb/restmex_sss_cs200_ov50",
    #     collection_name="restmex_sss_cs200_ov50",
    #     embedding_model="hiiamsid/sentence_similarity_spanish_es",
    # )
    # filters = {"type": "Restaurant"}
    # reviews = client.query_reviews(
    #     town="Isla_Mujeres",
    #     limit=5,
    #     text_query="Comentarios sobre el tiempo de espera entre tiempos, la disponibilidad de mesas y la rapidez del servicio de facturación.",
    #     filters=filters,
    # )
    # for review in reviews:
    #     logger.info(f"ID: {review['id']}\nTexto: {review['text']}\nMetadatos: {review['metadata']}\nDistance: {review.get('distance', 'N/A')}\n---\n")
    pass
