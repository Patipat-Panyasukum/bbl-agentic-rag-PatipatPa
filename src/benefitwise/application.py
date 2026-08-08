"""Composition root for the runnable BenefitWise LangGraph application."""

from __future__ import annotations

from benefitwise.config import AppSettings, build_chat_model, build_embedding_provider
from benefitwise.employee_repository import (
    SQLiteEmployeeRepository,
    initialize_employee_database,
)
from benefitwise.graph import build_benefit_graph
from benefitwise.policy_parser import load_policy_chunks
from benefitwise.retrieval import PolicyRetriever


def create_default_graph(settings: AppSettings | None = None):
    """Construct the production graph from local data and environment settings."""

    runtime_settings = settings or AppSettings.from_env()
    initialize_employee_database(runtime_settings.database_path)
    employee_repository = SQLiteEmployeeRepository(runtime_settings.database_path)
    retriever = PolicyRetriever(
        load_policy_chunks(
            runtime_settings.knowledge_base_path,
            runtime_settings.policy_metadata_path,
        ),
        build_embedding_provider(runtime_settings),
        min_similarity=runtime_settings.min_similarity,
    )
    model = build_chat_model(runtime_settings)
    return build_benefit_graph(
        employee_repository,
        retriever,
        model,
        model,
        top_k=runtime_settings.top_k,
    )
