import re
from collections.abc import Iterable

from evaluation.models import (
    BenchmarkCase,
    RetrievalResult,
)


ABSTENTION_TERMS = (
    "insufficient",
    "could not find",
    "cannot determine",
    "does not contain",
    "no evidence",
    "not enough evidence",
)


def normalize(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.casefold(),
    ).strip()


def contains_term(
    text: str,
    term: str,
) -> bool:
    return normalize(term) in normalize(text)


def ranked_chunk_metrics(
    retrieved_ids: list[str],
    expected_ids: list[str],
) -> dict[str, float | bool | None]:
    if not expected_ids:
        return {
            "recall_at_k": None,
            "precision_at_k": None,
            "hit_at_k": None,
            "mrr": None,
        }

    expected = set(expected_ids)
    hits = [
        chunk_id
        for chunk_id in retrieved_ids
        if chunk_id in expected
    ]
    first_rank = next(
        (
            index
            for index, chunk_id
            in enumerate(retrieved_ids, start=1)
            if chunk_id in expected
        ),
        None,
    )

    return {
        "recall_at_k": len(set(hits)) / len(expected),
        "precision_at_k": (
            len(hits) / len(retrieved_ids)
            if retrieved_ids
            else 0.0
        ),
        "hit_at_k": bool(hits),
        "mrr": (
            1.0 / first_rank
            if first_rank
            else 0.0
        ),
    }


def relationship_key(
    relationship: dict[str, str] | object,
) -> tuple[str, str, str]:
    if isinstance(relationship, dict):
        source = relationship["source"]
        relation = relationship["relationship"]
        target = relationship["target"]
    else:
        source = getattr(relationship, "source")
        relation = getattr(relationship, "relationship")
        target = getattr(relationship, "target")
    return (
        normalize(source),
        relation.strip().upper(),
        normalize(target),
    )


def citation_labels(text: str) -> set[str]:
    return set(
        re.findall(
            r"\[(?:Graph )?Evidence \d+\]|\[S\d+\]",
            text,
        )
    )


def calculate_metrics(
    case: BenchmarkCase,
    retrieval: RetrievalResult,
    answer: str | None = None,
    verified: bool | None = None,
    unsupported_claims: Iterable[str] = (),
) -> dict[str, object]:
    metrics: dict[str, object] = {}
    metrics.update(
        ranked_chunk_metrics(
            retrieval.chunk_ids,
            case.expected_chunk_ids,
        )
    )

    expected_entities = {
        normalize(item)
        for item in case.expected_entities
    }
    retrieved_entities = {
        normalize(item)
        for item in retrieval.entities
    }
    metrics["expected_entity_hit_rate"] = (
        len(expected_entities & retrieved_entities)
        / len(expected_entities)
        if expected_entities
        else None
    )

    expected_relationships = {
        relationship_key(item)
        for item in case.expected_relationships
    }
    retrieved_relationships = {
        relationship_key(item)
        for item in retrieval.relationships
    }
    matched_relationships = (
        expected_relationships
        & retrieved_relationships
    )
    metrics["expected_relationship_hit_rate"] = (
        len(matched_relationships)
        / len(expected_relationships)
        if expected_relationships
        else None
    )
    metrics["expected_relationship_retrieved"] = (
        expected_relationships
        <= retrieved_relationships
        if expected_relationships
        else None
    )
    metrics["graph_fact_precision"] = (
        len(matched_relationships)
        / len(retrieved_relationships)
        if expected_relationships
        and retrieved_relationships
        else None
    )

    forbidden = {
        relationship_key(item)
        for item in case.forbidden_relationships
    }
    forbidden_hits = forbidden & retrieved_relationships
    metrics["forbidden_relationship_count"] = len(
        forbidden_hits
    )

    allowed_documents = set(case.document_ids)
    evidence_documents = {
        item.document_id
        for item in retrieval.evidence
        if item.document_id
    }
    metrics["out_of_scope_evidence_count"] = len(
        evidence_documents - allowed_documents
    )
    metrics["document_scope_leakage_count"] = sum(
        1
        for item in retrieval.evidence
        if item.document_id
        and item.document_id not in allowed_documents
    )
    metrics["retrieved_chunk_count"] = len(
        retrieval.chunk_ids
    )
    metrics["graph_fact_count"] = len(
        retrieval.relationships
    )

    if answer is None:
        metrics.update(
            {
                "answer_correctness": None,
                "faithfulness": None,
                "citation_correctness": None,
                "citation_coverage": None,
                "unsupported_claim_count": None,
                "unsupported_claim_rate": None,
                "abstention_correctness": None,
                "multi_hop_answer_success": None,
            }
        )
        return metrics

    expected_terms = (
        case.answer_must_contain
        or case.expected_entities
    )
    abstained = any(
        term in answer.casefold()
        for term in ABSTENTION_TERMS
    )
    if case.negative:
        answer_correct = abstained
    else:
        answer_correct = all(
            contains_term(answer, term)
            for term in expected_terms
        )

    cited = citation_labels(answer)
    available = {
        f"[{item.label}]"
        for item in retrieval.evidence
    }
    valid_citations = cited & available
    citation_correctness = (
        len(valid_citations) / len(cited)
        if cited
        else (1.0 if case.negative and abstained else 0.0)
    )
    citation_coverage = (
        1.0
        if case.negative and abstained
        else float(bool(cited) and answer_correct)
    )
    unsupported_count = len(list(unsupported_claims))

    metrics.update(
        {
            "answer_correctness": answer_correct,
            "faithfulness": bool(verified)
            and citation_correctness == 1.0
            and not forbidden_hits,
            "citation_correctness": citation_correctness,
            "citation_coverage": citation_coverage,
            "unsupported_claim_count": unsupported_count,
            "unsupported_claim_rate": (
                0.0 if unsupported_count == 0 else 1.0
            ),
            "abstention_correctness": (
                abstained if case.negative else None
            ),
            "multi_hop_answer_success": (
                answer_correct
                if case.multi_hop
                else None
            ),
        }
    )
    return metrics
