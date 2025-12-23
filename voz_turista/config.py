from pydantic_settings import BaseSettings, SettingsConfigDict

import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")

    OPENAI_API_KEY: str

    VECTOR_DB_PATH: str = "data/vectordb"
