from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_rag"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/agentic_rag"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Anthropic (LLM calls — or any Anthropic-compatible provider)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str | None = None  # e.g. "https://openrouter.ai/api/v1"
    ANTHROPIC_ROUTER_MODEL: str = "claude-haiku-4-5-20251001"
    ANTHROPIC_ANSWERER_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_CHECKER_MODEL: str = "claude-haiku-4-5-20251001"

    # Embeddings (OpenAI-compatible: OpenAI, OpenRouter, Azure, Ollama, etc.)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str | None = None  # e.g. "https://openrouter.ai/api/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Cohere (reranking — or any Cohere-compatible provider)
    COHERE_API_KEY: str = ""
    COHERE_BASE_URL: str | None = None
    COHERE_RERANK_MODEL: str = "rerank-v3.5"

    # LlamaParse (document parsing)
    LLAMA_CLOUD_API_KEY: str = ""
    LLAMA_CLOUD_BASE_URL: str | None = None

    # Tokenizer
    TIKTOKEN_ENCODING: str = "cl100k_base"

    # Phoenix tracing
    PHOENIX_COLLECTOR_ENDPOINT: str = "http://localhost:4317"
    PHOENIX_ENABLED: bool = True

    # Ragas evaluation
    RAGAS_ENABLED: bool = True
    RAGAS_FAITHFULNESS_BYPASS_THRESHOLD: float = 0.9
    RAGAS_LLM_MODEL: str = "gpt-4o-mini"


settings = Settings()
