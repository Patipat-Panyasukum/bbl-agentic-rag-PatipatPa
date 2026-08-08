"""Environment-backed configuration for the BenefitWise agent workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from benefitwise.embeddings import DEFAULT_EMBEDDING_MODEL, OpenAIEmbeddingProvider
from benefitwise.employee_repository import DEFAULT_DATABASE_PATH
from benefitwise.policy_parser import (
    DEFAULT_KNOWLEDGE_BASE_PATH,
    DEFAULT_POLICY_METADATA_PATH,
)
from benefitwise.retrieval import DEFAULT_MIN_SIMILARITY
from benefitwise.vector_store import DEFAULT_CHROMA_PATH

# Both agents have narrow, validated responsibilities, so the efficient Luna
# tier is the cost-conscious default. Reviewers can still override it via env.
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Runtime settings with assignment-friendly local defaults."""

    database_path: Path = DEFAULT_DATABASE_PATH
    knowledge_base_path: Path = DEFAULT_KNOWLEDGE_BASE_PATH
    policy_metadata_path: Path = DEFAULT_POLICY_METADATA_PATH
    chroma_path: Path = DEFAULT_CHROMA_PATH
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    min_similarity: float = DEFAULT_MIN_SIMILARITY
    top_k: int = 3
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_base_url: str | None = None
    use_responses_api: bool = True
    reasoning_effort: str = "low"
    verbosity: str = "low"

    def __post_init__(self) -> None:
        if not 1 <= self.top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        if not -1.0 <= self.min_similarity <= 1.0:
            raise ValueError("min_similarity must be between -1.0 and 1.0")
        if not self.openai_model.strip():
            raise ValueError("openai_model must not be blank")
        if not self.embedding_model.strip():
            raise ValueError("embedding_model must not be blank")

    @classmethod
    def from_env(cls) -> AppSettings:
        """Load `.env` without copying API secrets into the settings object."""

        load_dotenv()
        return cls(
            database_path=Path(os.getenv("EMPLOYEE_DATABASE_PATH", DEFAULT_DATABASE_PATH)),
            knowledge_base_path=Path(
                os.getenv("KNOWLEDGE_BASE_PATH", DEFAULT_KNOWLEDGE_BASE_PATH)
            ),
            policy_metadata_path=Path(
                os.getenv("POLICY_METADATA_PATH", DEFAULT_POLICY_METADATA_PATH)
            ),
            chroma_path=Path(os.getenv("CHROMA_PATH", DEFAULT_CHROMA_PATH)),
            embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            min_similarity=float(
                os.getenv("RETRIEVAL_MIN_SIMILARITY", str(DEFAULT_MIN_SIMILARITY))
            ),
            top_k=int(os.getenv("RETRIEVAL_TOP_K", "3")),
            openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
            use_responses_api=_parse_bool(
                os.getenv("OPENAI_USE_RESPONSES_API", "true"),
                "OPENAI_USE_RESPONSES_API",
            ),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
            verbosity=os.getenv("OPENAI_VERBOSITY", "low"),
        )


def build_chat_model(settings: AppSettings) -> ChatOpenAI:
    """Build the shared chat model; binding tools later returns a separate runnable."""

    return ChatOpenAI(
        model=settings.openai_model,
        base_url=settings.openai_base_url,
        use_responses_api=settings.use_responses_api,
        reasoning_effort=settings.reasoning_effort,
        verbosity=settings.verbosity,
        max_retries=2,
        timeout=60,
    )


def build_embedding_provider(settings: AppSettings) -> OpenAIEmbeddingProvider:
    """Build the OpenAI embedding adapter without retaining the API key."""

    return OpenAIEmbeddingProvider(
        settings.embedding_model,
        base_url=settings.openai_base_url,
    )


def _parse_bool(value: str, field_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{field_name} must be a boolean value")
