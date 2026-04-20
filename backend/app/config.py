from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- API keys ---
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    BRAVE_API_KEY: Optional[str] = None
    E2B_API_KEY: Optional[str] = None

    # --- Langfuse ---
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: Optional[str] = None

    # --- Ollama ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_KEEP_ALIVE: str = "-1"

    # --- VRAM / routing policy ---
    LOCALVRAM_MAX_GB: int = 8
    FORCE_API_FOR_HEAVY: bool = False

    # --- Per-task model assignments (consumed by router.py in Phase 2) ---
    MODEL_PLANNER: Optional[str] = None
    MODEL_SYNTH: Optional[str] = None
    MODEL_CRITIC_INNER: Optional[str] = None
    MODEL_CRITIC_FINAL: Optional[str] = None
    MODEL_PREF_EXTRACT: Optional[str] = None
    MODEL_ENTAILMENT: Optional[str] = None
    MODEL_EVAL_JUDGE: Optional[str] = None

    # --- Embeddings ---
    EMBEDDINGS_PROVIDER: str = "sentence-transformers"
    EMBEDDINGS_MODEL: str = "BAAI/bge-small-en-v1.5"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./data/aethermind.db"

    # --- Chroma ---
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
