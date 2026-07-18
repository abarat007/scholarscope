from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "scholarscope"
    postgres_password: str = "scholarscope"
    postgres_db: str = "scholarscope"

    opensearch_url: str = "http://localhost:9200"
    redis_url: str = "redis://localhost:6379/0"
    airflow_url: str = "http://localhost:8080"

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5"
    # Frontend dev servers; override via CORS_ORIGINS='["https://…"]' in prod.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ]
    # Sonnet 5 introductory pricing ($/MTok) through 2026-08-31; override via env after.
    llm_input_cost_per_mtok: float = 2.0
    llm_output_cost_per_mtok: float = 10.0

    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dims: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_async_dsn(self) -> str:
        return self.postgres_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
