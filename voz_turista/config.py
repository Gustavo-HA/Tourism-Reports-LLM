from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )

    LLM_MODEL: str
    LLM_TEMPERATURE: float = 0.0

    EMBEDDING_MODEL: str

    VECTOR_DB_PATH: str
    VECTOR_DB_COLLECTION: str

    RERANKER_MODEL: str | None = None


settings = Settings()
