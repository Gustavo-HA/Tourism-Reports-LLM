import uuid
from typing import Any, Dict, List

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .utils import read_restmex_dataframe


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
        print(f"Ingestando {total_records} documentos en {total_lotes} lotes...")

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
                print(f"Lote procesado: {i // batch_size + 1} / {total_lotes}")
            except Exception as e:
                print(f"Error en el lote {i}: {e}")
        
        print("Operación completada.")

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
        df_restmex = read_restmex_dataframe(parquet_path)
        print(f"Procesando {len(df_restmex)} registros originales...")

        # Configurar splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        all_documents = []
        all_metadatas = []
        all_ids = []

        for row in df_restmex.itertuples(index=False):
            # Access attributes with dot notation instead of brackets
            original_text = row.text 
            if not isinstance(original_text, str) or not original_text.strip():
                continue

            # Generar chunks
            chunks = text_splitter.split_text(original_text)
            
            # ID base del documento original
            composite_key = f"{row.Pueblo}-{row.Lugar}-{row.FechaEstadia}-{original_text}"
            base_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, composite_key))

            for i, chunk in enumerate(chunks):
                chunk_id = f"{base_id}_{i}"
                
                # Metadatos base + info del chunk
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

        # Ingestar usando el método genérico
        self.add_documents(
            documents=all_documents,
            metadatas=all_metadatas,
            ids=all_ids,
            batch_size=batch_size
        )

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
    #     print(f"ID: {review['id']}\nTexto: {review['text']}\nMetadatos: {review['metadata']}\nDistance: {review.get('distance', 'N/A')}\n---\n")
    pass
