from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GenAI Chatbot API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    allowed_origins: str = "http://localhost:5173"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    users_path: str = "data/users.json"
    chat_db_path: str = "data/chats.db"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    router_model: str = "gemini-2.0-flash"
    critic_model: str = "gemini-2.0-flash"
    embedding_dimensions: int = 3072
    max_context_chunks: int = 4
    max_regeneration_attempts: int = 1
    ood_similarity_threshold: float = 0.12

    vector_backend: str = "local"
    vector_index_path: str = "data/vector_index.json"
    postgres_dsn: str = ""
    pgvector_table: str = "knowledge_chunks"
    graph_path: str = "data/knowledge_graph.json"
    hybrid_vector_weight: float = 0.6
    hybrid_graph_weight: float = 0.4
    telemetry_path: str = "data/telemetry.log"

    source_urls: str = "https://handbook.gitlab.com,https://about.gitlab.com/direction/"
    crawl_depth: int = 1
    max_child_links_per_page: int = 12
    max_expanded_pages_per_seed: int = 25

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
