from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors
from pydantic import BaseModel, ValidationError

from app.agents.query_decomposition import ConditionalDecompositionRetriever, QueryDecomposer
from app.agents.research_agent import ResearchAgent
from app.agents.verification_agent import VerificationAgent
from app.core.config import settings
from app.core.provider_resilience import call_with_provider_resilience
from app.graph.extractor import GraphExtractor
from app.graph.ontology import GENERAL_ONTOLOGY
from app.graph.ontology_classifier import OntologyClassifier
from app.models.document import Document, DocumentChunk, FileType
from app.retrieval.embeddings import GeminiEmbeddingService


def server_error(code: int, headers=None):
    response = httpx.Response(code, headers=headers or {})
    return errors.ServerError(code, {"message": "temporary"}, response)


def client_error(code: int):
    return errors.ClientError(code, {"message": "rejected"})


class SequenceModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def _next(self):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def generate_content(self, **kwargs):
        return self._next()

    def embed_content(self, **kwargs):
        return self._next()


def fake_client(*outcomes):
    models = SequenceModels(outcomes)
    return SimpleNamespace(models=models), models


@pytest.fixture
def no_component_sleep(monkeypatch):
    monkeypatch.setattr(settings, "provider_retry_base_delay_seconds", 0.0)
    monkeypatch.setattr(settings, "provider_retry_max_delay_seconds", 0.0)


def run(outcomes):
    calls = 0
    sleeps = []

    def operation():
        nonlocal calls
        outcome = outcomes[calls]
        calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    result = call_with_provider_resilience(
        operation,
        sleep=sleeps.append,
        random_value=lambda: 0.0,
    )
    return result, calls, sleeps


def test_success_on_first_attempt():
    result, calls, _ = run(["ok"])
    assert result == "ok"
    assert calls == 1


@pytest.mark.parametrize("code", [503, 429, 500])
def test_retryable_http_status_then_success(code):
    result, calls, _ = run([server_error(code), "ok"])
    assert result == "ok"
    assert calls == 2


@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError("connect"), httpx.ReadTimeout("read")],
)
def test_transport_failure_then_success(failure):
    result, calls, _ = run([failure, "ok"])
    assert result == "ok"
    assert calls == 2


def test_three_transient_failures_preserve_final_exception():
    failures = [server_error(503), server_error(503), server_error(504)]
    calls = 0

    def operation():
        nonlocal calls
        failure = failures[calls]
        calls += 1
        raise failure

    with pytest.raises(errors.ServerError) as caught:
        call_with_provider_resilience(operation, sleep=lambda value: None)
    assert calls == 3
    assert caught.value is failures[-1]


@pytest.mark.parametrize("code", [400, 401, 403])
def test_non_retryable_http_status_calls_once(code):
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        raise client_error(code)

    with pytest.raises(errors.ClientError):
        call_with_provider_resilience(operation, sleep=lambda value: None)
    assert calls == 1


def test_pydantic_validation_failure_is_not_retried():
    class RequiredValue(BaseModel):
        value: int

    try:
        RequiredValue.model_validate({})
    except ValidationError as failure:
        calls = 0

        def operation():
            nonlocal calls
            calls += 1
            raise failure

        with pytest.raises(ValidationError):
            call_with_provider_resilience(operation)
        assert calls == 1


def test_retry_after_is_honored_and_bounded(monkeypatch):
    monkeypatch.setattr(settings, "provider_retry_max_delay_seconds", 2.0)
    _, _, sleeps = run([server_error(429, {"Retry-After": "20"}), "ok"])
    assert sleeps == [2.0]


def test_jitter_and_backoff_are_bounded(monkeypatch):
    monkeypatch.setattr(settings, "provider_retry_base_delay_seconds", 0.5)
    monkeypatch.setattr(settings, "provider_retry_max_delay_seconds", 2.0)
    sleeps = []
    outcomes = [server_error(503), server_error(503), "ok"]
    calls = 0

    def operation():
        nonlocal calls
        outcome = outcomes[calls]
        calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    call_with_provider_resilience(
        operation,
        sleep=sleeps.append,
        random_value=lambda: 1.0,
    )
    assert sleeps == [1.0, 2.0]


def test_ontology_exhaustion_keeps_deterministic_fallback(monkeypatch, no_component_sleep):
    from app.graph import ontology_classifier as module

    client, models = fake_client(*[server_error(503) for _ in range(3)])
    monkeypatch.setattr(module, "create_gemini_client", lambda timeout: client)
    monkeypatch.setattr(
        OntologyClassifier,
        "_score_profiles",
        classmethod(lambda cls, text: {
            "research": 4.0, "career": 0.0, "policy": 0.0, "contract": 0.0,
        }),
    )
    doc = Document(filename="ambiguous.txt", file_type=FileType.TXT)
    result = OntologyClassifier().classify(doc, "ambiguous technical content")
    assert result.method == "fallback"
    assert models.calls == 3


def test_decomposition_exhaustion_keeps_adaptive_fallback(no_component_sleep):
    client, models = fake_client(*[server_error(503) for _ in range(3)])
    decomposer = QueryDecomposer(client=client)
    adaptive = SimpleNamespace(
        _requires_decomposition=lambda question: True,
        __call__=lambda state: {"research_context": "fallback"},
    )

    class Adaptive:
        def _requires_decomposition(self, question):
            return True

        def __call__(self, state):
            return {"research_context": "fallback"}

    result = ConditionalDecompositionRetriever(Adaptive(), decomposer)({"question": "complex"})
    assert result["decomposition_degraded"] is True
    assert models.calls == 3


@pytest.mark.parametrize("agent_type", [ResearchAgent, VerificationAgent])
def test_fatal_agent_exhaustion_propagates(agent_type, no_component_sleep):
    client, models = fake_client(*[server_error(503) for _ in range(3)])
    agent = agent_type.__new__(agent_type)
    agent.client = client
    agent.model = "model"
    with pytest.raises(errors.ServerError):
        if agent_type is ResearchAgent:
            agent.research("question", "[Evidence 1] facts", "hybrid")
        else:
            agent.verify("question", "answer [Evidence 1]", "[Evidence 1] facts")
    assert models.calls == 3


def test_embedding_transient_failure_then_success(no_component_sleep):
    response = SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2])])
    client, models = fake_client(server_error(503), response)
    service = GeminiEmbeddingService.__new__(GeminiEmbeddingService)
    service.client = client
    service.model = "embedding-model"
    service.dimensions = 2
    assert service.embed_query("question") == [0.1, 0.2]
    assert models.calls == 2


def graph_extractor_with(outcomes):
    client, models = fake_client(*outcomes)
    extractor = GraphExtractor.__new__(GraphExtractor)
    extractor.client = client
    extractor.model = "graph-model"
    extractor.ontology_profile = GENERAL_ONTOLOGY
    return extractor, models


def test_graph_extraction_503_then_success_before_any_write(no_component_sleep):
    response = SimpleNamespace(text='{"chunks":[{"chunk_index":0,"entities":[],"relationships":[]}]}')
    extractor, models = graph_extractor_with([server_error(503), response])
    doc = Document(filename="graph.txt", file_type=FileType.TXT)
    chunk = DocumentChunk(document_id=doc.id, chunk_index=0, text="content")
    result = extractor._extract_batch(doc, [chunk])
    assert len(result.chunks) == 1
    assert models.calls == 2


def test_graph_extraction_400_is_not_retried(no_component_sleep):
    extractor, models = graph_extractor_with([client_error(400)])
    doc = Document(filename="graph.txt", file_type=FileType.TXT)
    chunk = DocumentChunk(document_id=doc.id, chunk_index=0, text="content")
    with pytest.raises(errors.ClientError):
        extractor._extract_batch(doc, [chunk])
    assert models.calls == 1
