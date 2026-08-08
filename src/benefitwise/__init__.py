"""BenefitWise AI application package."""

from benefitwise.embeddings import SentenceTransformerEmbeddings
from benefitwise.employee import EmployeeContext
from benefitwise.employee_repository import (
    EmployeeDatabaseNotInitializedError,
    EmployeeNotFoundError,
    SQLiteEmployeeRepository,
    initialize_employee_database,
)
from benefitwise.policy import PolicyChunk, PolicyEligibility, filter_eligible_policies
from benefitwise.policy_parser import PolicyParseError, load_policy_chunks
from benefitwise.retrieval import PolicyEvidence, PolicyRetriever
from benefitwise.retrieval_tool import build_policy_retrieval_tool

__all__ = [
    "EmployeeContext",
    "EmployeeDatabaseNotInitializedError",
    "EmployeeNotFoundError",
    "PolicyChunk",
    "PolicyEligibility",
    "PolicyEvidence",
    "PolicyParseError",
    "PolicyRetriever",
    "SentenceTransformerEmbeddings",
    "SQLiteEmployeeRepository",
    "build_policy_retrieval_tool",
    "filter_eligible_policies",
    "initialize_employee_database",
    "load_policy_chunks",
]
