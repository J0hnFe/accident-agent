"""LangfuseTracer sin red: el SDK real exporta a memoria (InMemorySpanExporter de OpenTelemetry)."""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from accident_agent.core.memory import InMemoryConversationMemory
from accident_agent.core.orchestrator import Orchestrator
from accident_agent.core.registry import ToolRegistry
from accident_agent.observability.langfuse_tracer import LangfuseTracer
from accident_agent.tools.accident_search import SearchAccidentsTool
from tests.fakes import FakeAccidentRepository, FakeLLMProvider, ListLogger, answer, call

TRACE_ID = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def exported() -> Iterator[tuple[LangfuseTracer, InMemorySpanExporter]]:
    exporter = InMemorySpanExporter()
    # El SDK reutiliza un cliente por clave publica: una clave por prueba aisla los exportadores.
    test_key = uuid.uuid4().hex
    client = Langfuse(
        public_key=f"pk-lf-{test_key}",
        secret_key=f"sk-lf-{test_key}",
        base_url="http://127.0.0.1:1",
        span_exporter=exporter,
        flush_at=1,
    )
    yield LangfuseTracer(public_key="", secret_key="", base_url="", client=client), exporter
    client.shutdown()


def _spans(exporter: InMemorySpanExporter) -> dict[str, Any]:
    return {span.name: span for span in exporter.get_finished_spans()}


def test_trace_structure_ids_and_session(
    exported: tuple[LangfuseTracer, InMemorySpanExporter],
) -> None:
    tracer, exporter = exported
    trace = tracer.start_trace(trace_id=TRACE_ID, session_id="s1", input="hola")
    with trace.generation([{"role": "user"}]) as generation:
        generation.update(model="m", output="x", usage={"prompt_tokens": 3})
    with trace.span("search_accidents", {"province": "Guayas"}) as span:
        span.update(output={"total_found": 5})
    trace.end(output="respuesta", metadata={"stop_reason": "final_answer"})
    tracer.flush()
    spans = _spans(exporter)
    assert set(spans) == {"request", "llm", "search_accidents"}
    for span in spans.values():
        assert format(span.context.trace_id, "032x") == TRACE_ID
        assert span.attributes["session.id"] == "s1"
    assert spans["llm"].attributes["langfuse.observation.type"] == "generation"
    assert spans["search_accidents"].attributes["langfuse.observation.type"] == "tool"


def test_data_is_redacted_before_sending(
    exported: tuple[LangfuseTracer, InMemorySpanExporter],
) -> None:
    tracer, exporter = exported
    trace = tracer.start_trace(trace_id=TRACE_ID, session_id="s1", input="mi cedula 1712345678")
    with trace.span("echo", {"text": "placa PBX-1234"}) as span:
        span.update(output="clave sk-or-v1-abcdef0123")
    trace.end(output="ok", metadata={})
    tracer.flush()
    spans = exporter.get_finished_spans()
    text = " ".join(str(v) for s in spans for v in (s.attributes or {}).values())
    for secret in ("1712345678", "PBX-1234", "sk-or-v1-abcdef0123"):
        assert secret not in text
    assert "[CEDULA]" in text


def test_orchestrator_request_produces_one_trace(
    exported: tuple[LangfuseTracer, InMemorySpanExporter],
) -> None:
    tracer, exporter = exported
    registry = ToolRegistry()
    registry.register(SearchAccidentsTool(FakeAccidentRepository()))
    orchestrator = Orchestrator(
        llm=FakeLLMProvider([call(("search_accidents", {"province": "Guayas"})), answer("5")]),
        registry=registry,
        memory=InMemoryConversationMemory(),
        logger=ListLogger(),
        tracer=tracer,
    )
    response = orchestrator.handle("s1", "Guayas")
    tracer.flush()
    spans = exporter.get_finished_spans()
    assert sorted(s.name for s in spans) == ["llm", "llm", "request", "search_accidents"]
    assert {format(s.context.trace_id, "032x") for s in spans} == {response.trace_id}


def test_generation_measures_the_llm_call(
    exported: tuple[LangfuseTracer, InMemorySpanExporter],
) -> None:
    import time

    tracer, exporter = exported
    trace = tracer.start_trace(trace_id=TRACE_ID, session_id="s1", input="hola")
    with trace.generation([]) as generation:
        time.sleep(0.05)
        generation.update(model="m", output="x", usage={})
    trace.end(output="ok", metadata={})
    tracer.flush()
    span = _spans(exporter)["llm"]
    assert span.end_time is not None
    assert span.start_time is not None
    assert (span.end_time - span.start_time) / 1e9 >= 0.05
