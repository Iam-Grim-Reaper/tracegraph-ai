import re
from time import perf_counter

from google.genai import types
from pydantic import BaseModel, Field, model_validator

from app.agents.adaptive_retrieval import AdaptiveEvidenceRetriever
from app.agents.state import TraceGraphState
from app.core.config import settings
from app.core.provider_resilience import call_with_provider_resilience, create_gemini_client


class SubQuestion(BaseModel):
    id: str
    question: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)


class DecompositionPlan(BaseModel):
    subquestions: list[SubQuestion] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def validate_dependencies(self):
        seen = set()
        for item in self.subquestions:
            if item.id in seen or any(value not in seen for value in item.depends_on):
                raise ValueError("Sub-question dependencies must be unique and ordered")
            seen.add(item.id)
        return self


class QueryDecomposer:
    def __init__(self, client=None):
        if client is None and not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        self.client = client or create_gemini_client(
            settings.provider_default_timeout_seconds
        )

    def decompose(self, question: str) -> DecompositionPlan:
        prompt = f"""
Break this operationally complex retrieval question into two or at most three focused questions.

ORIGINAL QUESTION
{question}

Rules:
- Preserve the original intent.
- Use dependencies when a later question needs an entity found by an earlier question.
- Refer to that unknown value as the identified entity; do not invent its name.
- IDs must be q1, q2, then optionally q3.
- Dependencies may reference only earlier IDs.
- Return only the structured result. Do not provide reasoning or answers.
""".strip()
        response = call_with_provider_resilience(lambda: self.client.models.generate_content(
            model=settings.decomposition_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DecompositionPlan,
                temperature=0.0,
            ),
        ))
        if not response.text:
            raise RuntimeError("Decomposer returned an empty response")
        plan = DecompositionPlan.model_validate_json(response.text)
        return DecompositionPlan(
            subquestions=plan.subquestions[: settings.decomposition_max_subquestions]
        )


class ConditionalDecompositionRetriever:
    def __init__(self, adaptive=None, decomposer=None):
        self.adaptive = adaptive or AdaptiveEvidenceRetriever()
        self.decomposer = decomposer or QueryDecomposer()

    def __call__(self, state: TraceGraphState) -> dict:
        question = state.get("rewritten_question") or state.get("question", "")
        should_decompose = (
            state.get("retry_count", 0) == 0
            and self.adaptive._requires_decomposition(question)
        )
        if not should_decompose:
            result = self.adaptive(state)
            result.update({
                "decomposition_used": False,
                "decomposition_degraded": False,
                "decomposition_call_count": 0,
                "decomposition_latency_ms": None,
                "subquestion_count": 0,
                "subquestions": [],
            })
            return result

        started = perf_counter()
        try:
            plan = self.decomposer.decompose(question)
        except Exception:
            result = self.adaptive(state)
            result.update({
                "decomposition_used": False,
                "decomposition_degraded": True,
                "decomposition_call_count": 1,
                "decomposition_latency_ms": (perf_counter() - started) * 1000,
                "subquestion_count": 0,
                "subquestions": [],
            })
            return result

        decomposition_latency = (perf_counter() - started) * 1000
        results = {}
        metadata = []
        contexts = []
        seen_evidence = set()
        chunk_ids = []
        graph_count = 0
        embedding_calls = 0
        qdrant_calls = 0
        neo4j_calls = 0
        crossencoder_calls = 0
        evidence_items = []

        for item in plan.subquestions:
            grounded = []
            for dependency in item.depends_on:
                grounded.extend(results.get(dependency, {}).get("grounded_entities", []))
            grounded = list(dict.fromkeys(grounded))
            if item.depends_on and not grounded:
                metadata.append({"id": item.id, "question": item.question, "route": None, "evidence_count": 0, "depends_on": item.depends_on})
                continue

            retrieval_question = item.question
            if grounded:
                retrieval_question += " Grounded entity: " + ", ".join(grounded[:2]) + "."
            sub_state = {
                "question": retrieval_question,
                "document_ids": state.get("document_ids"),
                "retry_count": state.get("retry_count", 0),
                "provenance_expand": bool(item.depends_on or any(q.depends_on for q in plan.subquestions)),
            }
            try:
                result = self.adaptive(sub_state)
            except Exception:
                metadata.append({"id": item.id, "question": item.question, "route": None, "evidence_count": 0, "depends_on": item.depends_on})
                continue
            results[item.id] = result
            embedding_calls += result.get("query_embedding_call_count", 0)
            qdrant_calls += result.get("qdrant_call_count", 0)
            neo4j_calls += result.get("neo4j_call_count", 0)
            crossencoder_calls += result.get("crossencoder_call_count", 0)
            graph_count += result.get("graph_fact_count", 0)
            for chunk_id in result.get("retrieved_chunk_ids", []):
                if chunk_id not in chunk_ids:
                    chunk_ids.append(chunk_id)
            evidence_count = len(result.get("retrieved_chunk_ids", []))
            metadata.append({"id": item.id, "question": item.question, "route": result.get("retrieval_route"), "evidence_count": evidence_count, "depends_on": item.depends_on})
            for evidence in result.get("evidence_items", []):
                original_label = str(evidence.get("label", ""))
                public_label = re.sub(
                    r"^(Graph )?Evidence (\d+)$",
                    rf"\1Evidence {item.id}-\2",
                    original_label,
                )
                evidence_items.append({
                    **evidence,
                    "label": public_label,
                    "subquestion_id": item.id,
                    "subquestion": item.question,
                })
            for block in re.split(r"\n\n(?=\[(?:Graph )?Evidence \d+\])", result.get("research_context", "")):
                identity = re.search(r"Chunk(?: ID)?: ([^\n]+)", block)
                key = identity.group(1) if identity else block
                if key in seen_evidence or block.startswith("No document-scoped"):
                    continue
                seen_evidence.add(key)
                labeled = re.sub(r"\[(Graph )?Evidence (\d+)\]", rf"[\1Evidence {item.id}-\2]", block)
                contexts.append(f"Sub-question {item.id}: {item.question}\n{labeled}")

        return {
            "retrieval_route": "fused",
            "initial_route": "fused",
            "final_route": "fused",
            "routing_strategy": "adaptive_evidence",
            "routing_reason": "Evidence was gathered for dependent parts of the question.",
            "research_context": "\n\n".join(contexts) or "No document-scoped retrieval evidence found.",
            "retrieved_chunk_ids": chunk_ids,
            "graph_fact_count": graph_count,
            "requires_decomposition": True,
            "decomposition_used": True,
            "decomposition_degraded": len(results) < len(plan.subquestions),
            "decomposition_call_count": 1,
            "decomposition_latency_ms": decomposition_latency,
            "subquestion_count": len(plan.subquestions),
            "subquestions": metadata,
            "query_embedding_call_count": embedding_calls,
            "degraded": False,
            "qdrant_call_count": qdrant_calls,
            "neo4j_call_count": neo4j_calls,
            "crossencoder_call_count": crossencoder_calls,
            "evidence_items": evidence_items,
        }
