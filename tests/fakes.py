"""Deterministic test doubles for external or model-backed components."""

from __future__ import annotations

from collections.abc import Sequence
import re

import numpy as np
from langchain_core.messages import AIMessage
from numpy.typing import NDArray


class KeywordEmbeddings:
    """Small semantic test double with explicit synonym groups."""

    _CONCEPTS = (
        ("outpatient", "clinic", "doctor visit", "ผู้ป่วยนอก", "คลินิก"),
        ("inpatient", "hospital admission", "hospitalized", "ผู้ป่วยใน"),
        ("room", "food", "hospital room", "ค่าห้อง", "ค่าอาหาร"),
        ("claim procedure", "receipt", "documents", "ใบเสร็จ", "เอกสาร"),
        ("covered", "coverage", "eligible expense", "รายการค่ารักษา"),
        ("day case", "same day", "ไม่พักค้างคืน"),
        ("social security", "primary rights", "ประกันสังคม", "สิทธิหลัก"),
        ("accident", "อุบัติเหตุ"),
        ("allowance", "limit", "วงเงิน", "ไม่เกิน"),
        ("dental", "dentist", "teeth"),
        ("annual leave", "vacation", "days off"),
        ("international", "overseas"),
        ("travel", "flight", "trip"),
        ("medical", "health", "ค่ารักษาพยาบาล", "รักษาพยาบาล"),
        ("parking", "car park"),
    )

    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> NDArray[np.float32]:
        text_list = list(texts)
        self.batches.append(text_list)
        vectors = [self._embed_one(text) for text in text_list]
        return np.asarray(vectors, dtype=np.float32)

    def _embed_one(self, text: str) -> list[float]:
        normalized_text = text.lower()
        return [
            1.0 if any(term in normalized_text for term in terms) else 0.0
            for terms in self._CONCEPTS
        ]


class FakeToolCallingModel:
    """Chat-model double that records binding and emits one retrieval call."""

    def __init__(
        self,
        search_query: str = "outpatient medical expenses",
        *,
        tool_calls: list[dict[str, object]] | None = None,
    ) -> None:
        self.search_query = search_query
        self.configured_tool_calls = tool_calls
        self.bound_tools = []
        self.tool_choice = None
        self.invocations = []

    def bind_tools(self, tools, *, tool_choice=None):
        self.bound_tools = list(tools)
        self.tool_choice = tool_choice
        return self

    def invoke(self, messages):
        self.invocations.append(messages)
        calls = self.configured_tool_calls
        if calls is None:
            calls = [
                {
                    "name": "retrieve_benefit_policies",
                    "args": {"query": self.search_query, "top_k": 10},
                    "id": "fake-tool-call",
                    "type": "tool_call",
                }
            ]
        return AIMessage(content="", tool_calls=calls)


class FakeReportModel:
    """Tool-free report-model double with a fixed response."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.invocations = []

    def invoke(self, messages):
        self.invocations.append(messages)
        return AIMessage(content=self.response)


class EvidenceEchoReportModel:
    """Build a grounded test answer from the evidence included in the prompt."""

    def __init__(self) -> None:
        self.invocations = []

    def invoke(self, messages):
        self.invocations.append(messages)
        request = messages[-1].content
        policy_id = re.search(r"Policy ID: ([A-Z0-9-]+)", request).group(1)
        amount = re.search(r"THB [\d,]+", request).group(0)
        return AIMessage(
            content=f"The applicable outpatient limit is {amount} [{policy_id}]."
        )
