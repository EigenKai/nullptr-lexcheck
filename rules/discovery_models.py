"""Internal discovery DTOs; shared legal/record contracts stay canonical."""

from datetime import date
from typing import Literal, Protocol

from pydantic import Field

from contracts.models import ClauseVersion, Contract, Record, Rule

RecordKind = Record.model_fields["kind"].annotation


class Topic(Contract):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,49}$")
    question: str = Field(min_length=1, max_length=500)


class ResearchPlan(Contract):
    topics: tuple[Topic, ...] = Field(min_length=1, max_length=8)


class SourceLink(Contract):
    url: str = Field(max_length=2000)
    topic_ids: tuple[str, ...] = Field(min_length=1, max_length=8)


class SearchResult(Contract):
    sources: tuple[SourceLink, ...] = Field(max_length=8)


class CheckPlan(Contract):
    operation: Literal[
        "required_text", "forbidden_text", "uses_subset", "required_reference", "model_review"
    ]
    argument: str | None = Field(default=None, max_length=1000)
    reference_kind: RecordKind | None = None


class Candidate(Contract):
    obligation_actor: Literal["company", "authority", "unknown"] = "unknown"
    topic_id: str
    article: str = Field(min_length=1, max_length=250)
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=10000)
    valid_from: date | None
    valid_to: date | None
    title: str = Field(min_length=1, max_length=500)
    concept: str = Field(min_length=1, max_length=300)
    check_type: str = Field(max_length=80)
    activities: tuple[Literal["advertising", "ad_registration"], ...] = ("advertising",)
    roles: tuple[Literal["domestic_distributor", "producer", "importer"], ...] = (
        "domestic_distributor",
        "producer",
        "importer",
    )
    plan: CheckPlan
    exceptions: tuple[str, ...] = Field(max_length=12)
    uncertainties: tuple[str, ...] = Field(max_length=12)
    related_documents: tuple[str, ...] = Field(max_length=12)


class ProposedRelation(Contract):
    kind: Literal["AMENDS", "REPLACES", "REPEALS", "SUSPENDS", "DETAILS", "GUIDES", "REFERS_TO"]
    target_document: str = Field(min_length=1, max_length=300)
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=3000)
    effective_on: date | None


class Extraction(Contract):
    candidates: tuple[Candidate, ...] = Field(max_length=16)
    relations: tuple[ProposedRelation, ...] = Field(max_length=24)
    document_number: str = Field(default="", max_length=150)


class GeneratedRule(Contract):
    rule: Rule
    clause: ClauseVersion
    plan: CheckPlan
    topic_id: str
    source_id: str
    page: int
    quote_start: int
    quote_end: int
    concept_id: str
    exceptions: tuple[str, ...]
    uncertainties: tuple[str, ...]
    roles: tuple[str, ...] = ()


class Transport(Protocol):
    def complete(
        self, stage: str, payload: dict, schema: dict, *, timeout_s: float, web_search: bool = False
    ) -> dict: ...
