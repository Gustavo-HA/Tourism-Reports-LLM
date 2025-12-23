from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")
    
    GEMINI_API_KEY: str
    LLM: str = "gemini-2.5-pro"
    
    VECTOR_DB_PATH: str = "data/vectordb"
