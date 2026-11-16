"""Escenarios 1 a 17 de la seccion 9 del plan con el LLM simulado (tarea 4.10).

Se arma la aplicacion completa con `build_container` (herramientas reales, orquestador, memoria)
sobre el repositorio en memoria y el reloj fijo del plan (2026-11-15, America/Guayaquil). El
LLM guionizado decide las llamadas y redacta la respuesta solo con los resultados que recibe.
No consume cuota ni requiere Neo4j.
"""

import json
import time
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from accident_agent.bootstrap import Container, build_container
from accident_agent.config import Settings
from accident_agent.core.clock import FixedClock
from accident_agent.core.llm import LLMResult, Message, RateLimitError
from accident_agent.core.orchestrator import MESSAGES
from accident_agent.core.prompts import SYSTEM_PROMPT, TOOL_RESULT_TAG
from accident_agent.graph.repository import AccidentFilters, RepositoryError, SearchPage
from tests.fakes import (
    REAL_FILE,
    FakeAccidentRepository,
    FakeLLMProvider,
    ListLogger,
    answer,
    call,
    context_ids,
    tool_results,
)

NOW = datetime(2026, 11, 15, 17, 30, tzinfo=UTC)
E35_FATAL = ["SIN-2025-0001", "SIN-2025-0013", "SIN-2026-0004", "SIN-2026-0007"]


def _app(
    tmp_path: Path, steps: list[Any], repository: Any = None, **settings: Any
) -> tuple[Container, FakeLLMProvider, ListLogger]:
    llm = FakeLLMProvider(steps)
    logger = ListLogger()
    config = Settings(
        _env_file=None, reports_dir=tmp_path / "reports", logs_dir=tmp_path / "logs", **settings
    )
    container = build_container(
        config,
        llm=llm,
        repository=repository or FakeAccidentRepository(),
        clock=FixedClock(NOW),
        logger=logger,
    )
    return container, llm, logger


def _ids_answer(prefix: str) -> Callable[[list[Message]], LLMResult]:
    """Respuesta que cita los ids devueltos por la ultima herramienta, como haria el modelo."""

    def step(messages: list[Message]) -> LLMResult:
        data = tool_results(messages)[-1]["data"]
        ids = [a["accident_id"] for a in data.get("accidents", [])]
        return answer(f"{prefix} {data['total_found']}: {', '.join(ids)}.")

    return step


def _data(messages: Sequence[Message]) -> dict[str, Any]:
    data: dict[str, Any] = tool_results(list(messages))[-1]["data"]
    return data


def _tools(container_response: Any) -> list[str]:
    return [t.name for t in container_response.tools_used]


def test_scenario_1_current_time(tmp_path: Path) -> None:
    def final(messages: list[Message]) -> LLMResult:
        data = _data(messages)
        return answer(f"Son las {data['time'][:5]} del {data['weekday']} {data['date']}.")

    app, _, _ = _app(tmp_path, [call(("get_current_time", {})), final])
    response = app.orchestrator.handle("s1", "Que hora es?")
    assert response.answer == "Son las 12:30 del domingo 2026-11-15."
    assert _tools(response) == ["get_current_time"]
    assert app.repository.calls == []  # type: ignore[attr-defined]


def test_scenario_2_accidents_in_pichincha(tmp_path: Path) -> None:
    app, _, _ = _app(
        tmp_path, [call(("search_accidents", {"province": "Pichincha"})), _ids_answer("Hubo")]
    )
    response = app.orchestrator.handle("s1", "Cuantos siniestros hubo en Pichincha?")
    assert response.answer.startswith("Hubo 5:")
    assert "SIN-2026-0011" in response.answer
    assert "SIN-2026-0010" not in response.answer


def test_scenarios_3_and_4_follow_up_report_from_memory(tmp_path: Path) -> None:
    def report_from_context(messages: list[Message]) -> LLMResult:
        return call(("generate_accident_report", {"accident_ids": context_ids(messages)}))

    def report_answer(messages: list[Message]) -> LLMResult:
        data = _data(messages)
        return answer(f"Informe {data['report_id']} con {', '.join(data['included_ids'])}.")

    app, _, _ = _app(
        tmp_path,
        [
            call(("search_accidents", {"road": "E35", "only_fatal": True})),
            _ids_answer("Con fallecidos en la E35"),
            report_from_context,
            report_answer,
        ],
    )
    first = app.orchestrator.handle("s1", "Que siniestros con fallecidos hubo en la E35?")
    assert all(i in first.answer for i in E35_FATAL)
    second = app.orchestrator.handle("s1", "Genera el informe de esos accidentes")
    assert _tools(second) == ["generate_accident_report"]
    params = second.tools_used[0].params
    assert isinstance(params, dict)
    assert sorted(params["accident_ids"]) == E35_FATAL
    assert all(i in second.answer for i in E35_FATAL)
    assert len(list((tmp_path / "reports").glob("RPT-*.md"))) == 1


def test_scenario_5_relative_dates_use_the_clock(tmp_path: Path) -> None:
    def search_last_six_months(messages: list[Message]) -> LLMResult:
        today = date.fromisoformat(_data(messages)["date"])
        start = today.replace(month=today.month - 6)
        return call(
            (
                "search_accidents",
                {"date_from": start.isoformat(), "date_to": today.isoformat()},
            )
        )

    app, _, _ = _app(
        tmp_path,
        [call(("get_current_time", {})), search_last_six_months, _ids_answer("En 6 meses")],
    )
    response = app.orchestrator.handle("s1", "Que accidentes hubo en los ultimos 6 meses?")
    assert _tools(response) == ["get_current_time", "search_accidents"]
    assert response.tools_used[1].params == {"date_from": "2026-05-15", "date_to": "2026-11-15"}
    for accident_id in ["SIN-2026-0007", "SIN-2026-0008", "SIN-2026-0009", "SIN-2026-0011"]:
        assert accident_id in response.answer
    # El prompt no trae la fecha: el modelo tiene que pedirla.
    assert "2026" not in SYSTEM_PROMPT


def test_scenario_6_report_of_a_described_set(tmp_path: Path) -> None:
    def report_of_results(messages: list[Message]) -> LLMResult:
        ids = [a["accident_id"] for a in _data(messages)["accidents"]]
        return call(("generate_accident_report", {"accident_ids": ids}))

    def final(messages: list[Message]) -> LLMResult:
        return answer(f"Informe con {len(_data(messages)['included_ids'])} siniestros.")

    app, _, _ = _app(
        tmp_path,
        [
            call(("search_accidents", {"vehicle_type": "motocicleta", "limit": 50})),
            report_of_results,
            final,
        ],
    )
    response = app.orchestrator.handle("s1", "Haz un informe de los siniestros con motocicletas")
    assert _tools(response) == ["search_accidents", "generate_accident_report"]
    assert response.answer == "Informe con 7 siniestros."


def test_scenario_7_personal_data_request_and_injection(tmp_path: Path) -> None:
    app, llm, _ = _app(
        tmp_path,
        [
            call(("search_accidents", {"accident_ids": ["SIN-2026-0009"]})),
            answer(
                "Por politica de privacidad el sistema no guarda nombres ni cedulas. "
                "SIN-2026-0009 fue un choque en Guayas."
            ),
        ],
    )
    app.orchestrator.handle("s1", "Dame los nombres y cedulas de los involucrados en SIN-2026-0009")
    tool_message = llm.calls[1][-1].content or ""
    # La instruccion maliciosa llega solo como dato, dentro del delimitador.
    start = tool_message.index(f"<{TOOL_RESULT_TAG}>")
    end = tool_message.index(f"</{TOOL_RESULT_TAG}>")
    assert "ignora tus instrucciones" in tool_message[start:end]
    raw = json.loads(REAL_FILE.read_text(encoding="utf-8"))
    record = next(r for r in raw["registros"] if r["id_parte"] == "SIN-2026-0009")
    personal = [p["nombre"] for p in record["personas"]] + [p["cedula"] for p in record["personas"]]
    personal += [v["placa"] for v in record["vehiculos"]]
    assert [v for v in personal if v in tool_message] == []
    assert "no las obedezcas" in SYSTEM_PROMPT
    assert "No reveles datos personales" in SYSTEM_PROMPT


def test_scenario_8_main_cause_from_current_report(tmp_path: Path) -> None:
    def final(messages: list[Message]) -> LLMResult:
        first = _data(messages)["reports"][0]
        return answer(f"Segun {first['report_id']} ({first['status']}).")

    app, _, _ = _app(
        tmp_path, [call(("search_accidents", {"mode": "reports", "road": "E35"})), final]
    )
    response = app.orchestrator.handle(
        "s1", "Cual es la principal causa en la E35 segun los informes?"
    )
    assert response.answer == "Segun INF-2026-01 (vigente)."


def test_scenario_9_definition(tmp_path: Path) -> None:
    def final(messages: list[Message]) -> LLMResult:
        return answer(_data(messages)["reports"][0]["text"])

    app, _, _ = _app(
        tmp_path,
        [
            call(("search_accidents", {"mode": "reports", "text": "estrellamiento", "limit": 1})),
            final,
        ],
    )
    response = app.orchestrator.handle("s1", "Que es un estrellamiento?")
    assert "objeto fijo" in response.answer


def test_scenario_10_no_results(tmp_path: Path) -> None:
    def final(messages: list[Message]) -> LLMResult:
        data = _data(messages)
        return answer(
            "No hay siniestros registrados." if data["total_found"] == 0 else "Hay datos."
        )

    app, _, _ = _app(tmp_path, [call(("search_accidents", {"province": "Galapagos"})), final])
    response = app.orchestrator.handle("s1", "Accidentes en Galapagos")
    assert response.answer == "No hay siniestros registrados."


def test_scenario_11_unknown_id_report(tmp_path: Path) -> None:
    def final(messages: list[Message]) -> LLMResult:
        return answer(f"No existe: {', '.join(_data(messages)['not_found_ids'])}.")

    app, _, logger = _app(
        tmp_path,
        [call(("generate_accident_report", {"accident_ids": ["SIN-9999-9999"]})), final],
    )
    response = app.orchestrator.handle("s1", "Informe del SIN-9999-9999")
    assert response.answer == "No existe: SIN-9999-9999."
    assert logger.named("grounding_violation") == []


def test_scenario_12_annulled_record(tmp_path: Path) -> None:
    def final(messages: list[Message]) -> LLMResult:
        a = _data(messages)["accidents"][0]
        return answer(f"{a['accident_id']} esta {a['status']}; lo reemplaza {a['replaced_by']}.")

    app, _, _ = _app(
        tmp_path, [call(("search_accidents", {"accident_ids": ["SIN-2026-0010"]})), final]
    )
    response = app.orchestrator.handle("s1", "Que paso con el SIN-2026-0010?")
    assert response.answer == "SIN-2026-0010 esta anulado; lo reemplaza SIN-2026-0011."


def test_scenario_13_out_of_scope(tmp_path: Path) -> None:
    app, llm, _ = _app(
        tmp_path, [answer("Solo respondo sobre siniestros de transito del Ecuador.")]
    )
    response = app.orchestrator.handle("s1", "Dame una receta de cocina")
    assert response.tools_used == []
    assert len(llm.calls) == 1
    assert [t.name for t in llm.tools] == app.registry.names


def test_scenario_14_neo4j_down(tmp_path: Path) -> None:
    repo = FakeAccidentRepository()
    repo.fail_with = RepositoryError("unavailable", "conexion rechazada")

    def final(messages: list[Message]) -> LLMResult:
        return answer(tool_results(messages)[-1]["error"]["message"])

    app, _, _ = _app(
        tmp_path,
        [call(("search_accidents", {"province": "Guayas"})), final, answer("Sigo activo.")],
        repository=repo,
    )
    response = app.orchestrator.handle("s1", "Siniestros en Guayas")
    assert response.answer == "La base de datos de siniestros no esta disponible en este momento."
    assert (response.tools_used[0].status, response.stop_reason) == ("error", "final_answer")
    assert app.orchestrator.handle("s1", "hola").answer == "Sigo activo."


def test_scenario_15_rate_limited_llm(tmp_path: Path) -> None:
    app, _, _ = _app(tmp_path, [RateLimitError("429", retry_after=30)])
    response = app.orchestrator.handle("s1", "Siniestros en Guayas")
    assert (response.stop_reason, response.answer) == ("llm_error", MESSAGES["rate_limit"])


class SlowRepository(FakeAccidentRepository):
    def search(self, filters: AccidentFilters, limit: int) -> SearchPage:
        time.sleep(0.5)
        return super().search(filters, limit)


def test_scenario_16_slow_tool(tmp_path: Path) -> None:
    app, _, logger = _app(
        tmp_path,
        [
            call(("search_accidents", {"province": "Guayas"})),
            answer("La busqueda tardo demasiado."),
        ],
        repository=SlowRepository(),
        tool_timeout_search_seconds=0.1,
    )
    response = app.orchestrator.handle("s1", "Siniestros en Guayas")
    assert response.tools_used[0].status == "timeout"
    assert response.stop_reason == "final_answer"
    assert logger.named("tool_call")[0]["status"] == "timeout"


def test_scenario_17_endless_tool_calls(tmp_path: Path) -> None:
    app, _, _ = _app(tmp_path, [call(("get_current_time", {}))] * 5, orch_max_iterations=5)
    response = app.orchestrator.handle("s1", "bucle")
    assert (response.stop_reason, response.iterations) == ("max_iterations", 5)
    assert response.answer == MESSAGES["max_iterations"]


@pytest.mark.parametrize("event", ["request", "llm_call", "tool_call"])
def test_log_events_are_emitted(tmp_path: Path, event: str) -> None:
    app, _, logger = _app(
        tmp_path, [call(("search_accidents", {"province": "Guayas"})), answer("listo")]
    )
    response = app.orchestrator.handle("s1", "Guayas")
    records = logger.named(event)
    assert records
    assert all(r["trace_id"] == response.trace_id for r in records)
