"""Puerto de trazas (seccion 7.9 del plan, tarea 4.6b).

Una traza por solicitud, un span por herramienta y una generation por llamada al LLM. Por
defecto `NoopTracer`. `SafeTracer` envuelve cualquier implementacion: un fallo del trazador
nunca interrumpe la solicitud, solo deja una advertencia en el log.
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any, Protocol

from accident_agent.observability.events import EventLogger


class Span(Protocol):
    def update(self, *, output: Any = None, error: str | None = None) -> None: ...


class Generation(Protocol):
    def update(
        self,
        *,
        model: str | None = None,
        output: Any = None,
        usage: dict[str, int] | None = None,
        error: str | None = None,
    ) -> None: ...


class Trace(Protocol):
    def span(self, name: str, input: Any) -> AbstractContextManager[Span]: ...

    # Se abre antes de llamar al LLM y se cierra despues: asi la traza mide su latencia real.
    def generation(self, input: Any) -> AbstractContextManager[Generation]: ...

    def end(self, *, output: Any, metadata: dict[str, Any]) -> None: ...


class Tracer(Protocol):
    def start_trace(self, *, trace_id: str, session_id: str, input: Any) -> Trace: ...

    def flush(self) -> None: ...


class _NoopSpan:
    def update(self, **kwargs: Any) -> None:
        return None


class _NoopTrace:
    @contextmanager
    def span(self, name: str, input: Any) -> Iterator[Span]:
        yield _NoopSpan()

    @contextmanager
    def generation(self, input: Any) -> Iterator[Generation]:
        yield _NoopSpan()

    def end(self, *, output: Any, metadata: dict[str, Any]) -> None:
        return None


class NoopTracer:
    def start_trace(self, *, trace_id: str, session_id: str, input: Any) -> Trace:
        return _NoopTrace()

    def flush(self) -> None:
        return None


class _SafeSpan:
    def __init__(self, inner: Any, logger: EventLogger, operation: str) -> None:
        self._inner = inner
        self._logger = logger
        self._operation = operation

    def update(self, **kwargs: Any) -> None:
        try:
            self._inner.update(**kwargs)
        except Exception as exc:
            self._logger.warning(
                "tracer_error", operation=self._operation, error=type(exc).__name__
            )


class _SafeTrace:
    def __init__(self, inner: Trace, logger: EventLogger) -> None:
        self._inner = inner
        self._logger = logger

    @contextmanager
    def _guarded(self, manager_factory: Any, kind: str) -> Iterator[Any]:
        try:
            manager = manager_factory()
            inner = manager.__enter__()
        except Exception as exc:
            self._logger.warning(
                "tracer_error", operation=f"{kind}.start", error=type(exc).__name__
            )
            yield _NoopSpan()
            return
        try:
            yield _SafeSpan(inner, self._logger, f"{kind}.update")
        finally:
            try:
                manager.__exit__(None, None, None)
            except Exception as exc:
                self._logger.warning(
                    "tracer_error", operation=f"{kind}.end", error=type(exc).__name__
                )

    def span(self, name: str, input: Any) -> AbstractContextManager[Span]:
        return self._guarded(lambda: self._inner.span(name, input), "span")

    def generation(self, input: Any) -> AbstractContextManager[Generation]:
        return self._guarded(lambda: self._inner.generation(input), "generation")

    def end(self, *, output: Any, metadata: dict[str, Any]) -> None:
        try:
            self._inner.end(output=output, metadata=metadata)
        except Exception as exc:
            self._logger.warning("tracer_error", operation="trace.end", error=type(exc).__name__)


class SafeTracer:
    def __init__(self, inner: Tracer, logger: EventLogger) -> None:
        self._inner = inner
        self._logger = logger

    def start_trace(self, *, trace_id: str, session_id: str, input: Any) -> Trace:
        try:
            return _SafeTrace(
                self._inner.start_trace(trace_id=trace_id, session_id=session_id, input=input),
                self._logger,
            )
        except Exception as exc:
            self._logger.warning("tracer_error", operation="trace.start", error=type(exc).__name__)
            return _NoopTrace()

    def flush(self) -> None:
        try:
            self._inner.flush()
        except Exception as exc:
            self._logger.warning("tracer_error", operation="flush", error=type(exc).__name__)
