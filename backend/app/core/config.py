from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GenAI Chatbot API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    allowed_origins: str = "http://localhost:5173"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768
    max_context_chunks: int = 4

    vector_backend: str = "local"
    vector_index_path: str = "data/vector_index.json"
    postgres_dsn: str = ""
    pgvector_table: str = "knowledge_chunks"

    source_urls: str = "https://handbook.gitlab.com,https://about.gitlab.com/direction/"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def source_url_list(self) -> list[str]:
        return [url.strip() for url in self.source_urls.split(",") if url.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
