from app.core.config import Settings


def test_settings_defaults():
    s = Settings(
        _env_file=None,
        ANTHROPIC_API_KEY="test",
        OPENAI_API_KEY="test",
        COHERE_API_KEY="test",
        LLAMA_CLOUD_API_KEY="test",
    )
    assert s.ALGORITHM == "HS256"
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    assert s.EMBEDDING_MODEL == "text-embedding-3-small"
    assert s.EMBEDDING_DIMENSIONS == 1536
    assert s.COHERE_RERANK_MODEL == "rerank-v3.5"
    assert s.REDIS_URL == "redis://localhost:6379"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "my-secret-key")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "512")
    s = Settings(_env_file=None)
    assert s.SECRET_KEY == "my-secret-key"
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 120
    assert s.EMBEDDING_DIMENSIONS == 512
