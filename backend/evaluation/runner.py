import json
from pathlib import Path
from time import perf_counter

from app.agents.research_agent import ResearchAgent
from app.agents.verification_agent import VerificationAgent
from evaluation.metrics import calculate_metrics
from evaluation.models import (
    BenchmarkCase,
    Evidence,
    EvaluationResult,
    RelationshipEvidence,
    RetrievalResult,
)
from evaluation.variants import (
    VariantAdapter,
    create_adapter,
)


class EvaluationRunner:
    def __init__(
        self,
        retrieval_only: bool = False,
    ):
        self.retrieval_only = retrieval_only
        self.adapters: dict[str, VariantAdapter] = {}
        self._research_agent = None
        self._verification_agent = None

    def close(self) -> None:
        for adapter in self.adapters.values():
            adapter.close()

    def _adapter(self, variant: str) -> VariantAdapter:
        if variant not in self.adapters:
            self.adapters[variant] = create_adapter(variant)
        return self.adapters[variant]

    def _agents(self):
        if self._research_agent is None:
            self._research_agent = ResearchAgent()
            self._verification_agent = VerificationAgent()
        return self._research_agent, self._verification_agent

    def run_case(
        self,
        case: BenchmarkCase,
        variant: str,
    ) -> EvaluationResult:
        total_started = perf_counter()
        retrieval = self._adapter(variant).retrieve(
            question=case.question,
            document_ids=case.document_ids,
        )

        answer = None
        verified = None
        verification_reason = None
        unsupported_claims: list[str] = []
        used_labels: list[str] = []

        if not self.retrieval_only:
            research, verification = self._agents()
            draft = research.research(
                question=case.question,
                research_context=retrieval.context,
                retrieval_route=variant,
            )
            decision = verification.verify(
                question=case.question,
                draft_answer=draft.answer,
                research_context=retrieval.context,
            )
            answer = decision.final_answer
            verified = decision.passed
            verification_reason = decision.reason
            unsupported_claims = decision.unsupported_claims
            used_labels = draft.used_evidence_labels

        metrics = calculate_metrics(
            case=case,
            retrieval=retrieval,
            answer=answer,
            verified=verified,
            unsupported_claims=unsupported_claims,
        )
        return EvaluationResult(
            case_id=case.id,
            category=case.category,
            variant=variant,
            question=case.question,
            document_ids=case.document_ids,
            answer=answer,
            verified=verified,
            verification_reason=verification_reason,
            unsupported_claims=unsupported_claims,
            retry_count=0,
            used_evidence_labels=used_labels,
            retrieval=retrieval,
            metrics=metrics,
            total_latency_seconds=perf_counter() - total_started,
        )


def load_existing_results(
    path: str | Path,
) -> list[EvaluationResult]:
    result_path = Path(path)
    if not result_path.exists():
        return []
    payload = json.loads(
        result_path.read_text(encoding="utf-8")
    )
    results = []
    for item in payload.get("results", []):
        retrieval_data = item["retrieval"]
        retrieval = RetrievalResult(
            **{
                **retrieval_data,
                "evidence": [
                    Evidence(**value)
                    for value in retrieval_data["evidence"]
                ],
                "relationships": [
                    RelationshipEvidence(**value)
                    for value in retrieval_data["relationships"]
                ],
            }
        )
        results.append(
            EvaluationResult(
                **{
                    **item,
                    "retrieval": retrieval,
                }
            )
        )
    return results
