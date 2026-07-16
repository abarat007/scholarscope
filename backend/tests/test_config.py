from src.config import Settings


def test_defaults_produce_local_dsn():
    settings = Settings(_env_file=None)
    assert settings.postgres_dsn == (
        "postgresql://scholarscope:scholarscope@localhost:5432/scholarscope"
    )


def test_environment_overrides_are_respected(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret")
    settings = Settings(_env_file=None)
    assert settings.postgres_host == "db.internal"
    assert settings.postgres_dsn == (
        "postgresql://scholarscope:s3cret@db.internal:5432/scholarscope"
    )
