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

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
