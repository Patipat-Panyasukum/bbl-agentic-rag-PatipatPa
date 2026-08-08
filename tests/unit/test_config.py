"""Tests for environment configuration and validation."""

import pytest

from benefitwise.config import DEFAULT_OPENAI_MODEL, AppSettings
from benefitwise.embeddings import DEFAULT_EMBEDDING_MODEL


def test_uses_reviewer_friendly_defaults(monkeypatch) -> None:
    for field_name in (
        "OPENAI_MODEL",
        "OPENAI_BASE_URL",
        "OPENAI_USE_RESPONSES_API",
        "OPENAI_REASONING_EFFORT",
        "OPENAI_VERBOSITY",
        "EMPLOYEE_DATABASE_PATH",
        "KNOWLEDGE_BASE_PATH",
        "POLICY_METADATA_PATH",
        "EMBEDDING_MODEL",
        "RETRIEVAL_MIN_SIMILARITY",
        "RETRIEVAL_TOP_K",
    ):
        monkeypatch.delenv(field_name, raising=False)

    settings = AppSettings.from_env()

    assert DEFAULT_OPENAI_MODEL == "gpt-5.6-luna"
    assert settings.openai_model == DEFAULT_OPENAI_MODEL
    assert settings.embedding_model == DEFAULT_EMBEDDING_MODEL
    assert settings.use_responses_api is True
    assert settings.top_k == 3
    assert settings.min_similarity == 0.26


def test_reads_compatible_endpoint_switches(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "compatible-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_USE_RESPONSES_API", "false")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "2")

    settings = AppSettings.from_env()

    assert settings.openai_model == "compatible-model"
    assert settings.openai_base_url == "https://example.test/v1"
    assert settings.use_responses_api is False
    assert settings.top_k == 2


@pytest.mark.parametrize(
    "settings",
    [
        {"top_k": 0},
        {"top_k": 11},
        {"min_similarity": 1.1},
        {"openai_model": " "},
        {"embedding_model": " "},
    ],
)
def test_rejects_invalid_settings(settings) -> None:
    with pytest.raises(ValueError):
        AppSettings(**settings)


def test_rejects_invalid_boolean_environment_value(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_USE_RESPONSES_API", "sometimes")

    with pytest.raises(ValueError, match="OPENAI_USE_RESPONSES_API"):
        AppSettings.from_env()
