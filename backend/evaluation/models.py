from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BenchmarkCase:
    id: str
    category: str
    question: str
    document_ids: list[str]
    expected_answer: str
    expected_entities: list[str] = field(default_factory=list)
    expected_relationships: list[dict[str, str]] = field(default_factory=list)
    forbidden_relationships: list[dict[str, str]] = field(default_factory=list)
    expected_chunk_ids: list[str] = field(default_factory=list)
    answer_must_contain: list[str] = field(default_factory=list)
    requires_graph: bool = False
    multi_hop: bool = False
    negative: bool = False


@dataclass
class Evidence:
    label: str
    kind: str
    document_id: str | None = None
    chunk_id: str | None = None
    text: str = ""


@dataclass
class RelationshipEvidence:
    source: str
    relationship: str
    target: str
    document_id: str | None = None
    chunk_id: str | None = None


@dataclass
class RetrievalResult:
    variant: str
    context: str
    evidence: list[Evidence]
    chunk_ids: list[str]
    entities: list[str]
    relationships: list[RelationshipEvidence]
    retrieval_latency_seconds: float
    limits: dict[str, int]
    stage_latency_seconds: dict[str, float] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    case_id: str
    category: str
    variant: str
    question: str
    document_ids: list[str]
    answer: str | None
    verified: bool | None
    verification_reason: str | None
    unsupported_claims: list[str]
    retry_count: int
    used_evidence_labels: list[str]
    retrieval: RetrievalResult
    metrics: dict[str, Any]
    total_latency_seconds: float
    token_usage_available: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
