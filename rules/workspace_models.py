"""Incomplete domain research proposals, never executable canonical Rules."""

from datetime import date
from typing import Literal

from pydantic import Field

from contracts.models import Contract
from rules.discovery_models import ProposedRelation


class ObligationProposal(Contract):
    topic_id: str = Field(max_length=50)
    actor: Literal["operator", "authority", "tenant", "unknown"]
    article: str = Field(min_length=1, max_length=250)
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=6000)
    title: str = Field(min_length=1, max_length=500)
    concept: str = Field(min_length=1, max_length=300)
    requirement: str = Field(min_length=1, max_length=2000)
    applicability: str = Field(min_length=1, max_length=2000)
    missing_facts: tuple[str, ...] = Field(max_length=12)
    evidence_needed: tuple[str, ...] = Field(max_length=12)
    valid_from: date | None
    valid_to: date | None
    date_quote: str | None = Field(max_length=1500)
    date_page: int | None = Field(ge=1)
    exceptions: tuple[str, ...] = Field(max_length=12)
    related_documents: tuple[str, ...] = Field(max_length=12)


class HousingExtraction(Contract):
    document_number: str = Field(max_length=150)
    proposals: tuple[ObligationProposal, ...] = Field(max_length=12)
    relations: tuple[ProposedRelation, ...] = Field(max_length=16)
