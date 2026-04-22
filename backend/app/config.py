from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to the repo layout, not the process cwd. Developers run
# ``uv run`` from ``backend/`` while ``.env`` lives at the monorepo root.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
_ENV_FILES = tuple(
    str(p)
    for p in (_REPO_ROOT / ".env", _BACKEND_ROOT / ".env")
    if p.is_file()
)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES if _ENV_FILES else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    MODEL_SOURCE_SUMMARY: Optional[str] = None
    MODEL_TOOL_FORMAT: Optional[str] = None

    # --- Embeddings ---
    EMBEDDINGS_PROVIDER: str = "sentence-transformers"
    EMBEDDINGS_MODEL: str = "BAAI/bge-small-en-v1.5"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./data/aethermind.db"

    # --- Chroma ---
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIR: str = "data/chroma"
    CHROMA_COLLECTION_PREFERENCES: str = "memory_preferences"
    CHROMA_COLLECTION_REPORTS: str = "memory_reports"
    CHROMA_COLLECTION_SCRATCH: str = "scratch_sources"
    MEMORY_RECALL_TOP_K: int = 5
    DEFAULT_USER_NAME: str = "default"
    CITATION_OVERLAP_THRESHOLD: float = 0.6
    CITATION_ENTAILMENT_MIN_CONFIDENCE: float = 0.6

    # --- Tooling ---
    ENABLE_CODE_EXEC: bool = False
    CODE_EXEC_PROVIDER: str = "stub"

    # --- Agent runtime ---
    AGENT_MAX_REVISIONS: int = 2
    AGENT_CHECKPOINT_PATH: str = "data/agent_checkpoints.db"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a normalized list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
