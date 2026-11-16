"""Dobles de prueba. `FakeAccidentRepository` cumple el mismo contrato que el adaptador Neo4j
(lo comprueba `tests/contract/test_repository_contract.py`), sin base de datos."""

import json
import re
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from accident_agent.core.llm import LLMResult, Message, ToolCall
from accident_agent.core.prompts import TOOL_RESULT_TAG
from accident_agent.core.tool import ToolSpec
from accident_agent.domain.catalogs import ReportStatus
from accident_agent.domain.models import Accident, CleanDataset
from accident_agent.graph.repository import (
    AccidentFilters,
    AccidentView,
    DatasetSummary,
    GroupBy,
    PersonView,
    ReportHit,
    RepositoryError,
    SearchPage,
    StatsRow,
    VehicleView,
)
from accident_agent.ingestion.normalizers import normalize_key
from accident_agent.ingestion.pipeline import run_pipeline

REAL_FILE = Path(__file__).resolve().parents[1] / "data" / "siniestros_raw.json"


def _view(accident: Accident, replaces: str | None) -> AccidentView:
    loc = accident.location
    return AccidentView(
        **accident.model_dump(exclude={"location", "vehicles", "people"}),
        province=loc.province,
        canton=loc.canton,
        parish=loc.parish,
        road=loc.road,
        road_code=loc.road_code,
        km=loc.km,
        latitude=loc.latitude,
        longitude=loc.longitude,
        replaces=replaces,
        vehicles=[VehicleView(**v.model_dump()) for v in accident.vehicles],
        people=[PersonView(**p.model_dump()) for p in accident.people],
    )


def _score(text: str, query: str) -> int:
    # Aproximacion del full-text: cuenta los terminos de la consulta presentes en el texto.
    folded = normalize_key(text)
    return sum(term in folded for term in normalize_key(query).split())


class FakeAccidentRepository:
    def __init__(self, dataset: CleanDataset | None = None) -> None:
        self.dataset = dataset or run_pipeline(REAL_FILE)
        replaces = {a.replaced_by: a.accident_id for a in self.dataset.accidents if a.replaced_by}
        self.views = {
            a.accident_id: _view(a, replaces.get(a.accident_id)) for a in self.dataset.accidents
        }
        self.fail_with: RepositoryError | None = None
        self.calls: list[str] = []

    def _check(self, operation: str) -> None:
        self.calls.append(operation)
        if self.fail_with is not None:
            raise self.fail_with

    def _matches(self, a: AccidentView, f: AccidentFilters) -> bool:
        vehicle_types = {v.vehicle_type for v in a.vehicles}
        return all(
            [
                a.is_active or f.include_annulled or bool(f.accident_ids),
                not f.accident_ids or a.accident_id in f.accident_ids,
                not f.text or _score(a.narrative, f.text) > 0,
                f.province is None or a.province is f.province,
                f.canton is None or a.canton == f.canton,
                f.road_code is None or a.road_code == f.road_code,
                f.road_text is None or f.road_text in a.road.lower(),
                f.accident_type is None or a.accident_type is f.accident_type,
                f.cause is None or a.cause is f.cause,
                f.weather is None or a.weather is f.weather,
                f.surface is None or a.surface is f.surface,
                f.lighting is None or a.lighting is f.lighting,
                f.date_from is None or a.date >= f.date_from,
                f.date_to is None or a.date <= f.date_to,
                not f.only_fatal or a.deaths > 0,
                f.vehicle_type is None or f.vehicle_type in vehicle_types,
            ]
        )

    def _filtered(self, filters: AccidentFilters) -> list[AccidentView]:
        found = [a for a in self.views.values() if self._matches(a, filters)]
        found.sort(key=lambda a: a.accident_id)
        found.sort(key=lambda a: a.occurred_at, reverse=True)
        if filters.text:
            found.sort(key=lambda a: _score(a.narrative, filters.text or ""), reverse=True)
        return found

    def search(self, filters: AccidentFilters, limit: int) -> SearchPage:
        self._check("search")
        found = self._filtered(filters)
        return SearchPage(total_found=len(found), accidents=found[:limit])

    def get_by_ids(self, accident_ids: Sequence[str]) -> list[AccidentView]:
        self._check("get_by_ids")
        return [self.views[i] for i in accident_ids if i in self.views]

    def stats(self, filters: AccidentFilters, group_by: GroupBy) -> list[StatsRow]:
        self._check("stats")
        groups: dict[str, list[AccidentView]] = defaultdict(list)
        for a in self._filtered(filters):
            keys = {
                GroupBy.PROVINCE: [a.province.value],
                GroupBy.CAUSE: [a.cause.value],
                GroupBy.ACCIDENT_TYPE: [a.accident_type.value],
                GroupBy.MONTH: [a.date.isoformat()[:7]],
                GroupBy.YEAR: [str(a.date.year)],
                GroupBy.WEATHER: [a.weather.value],
                GroupBy.VEHICLE_TYPE: sorted({v.vehicle_type.value for v in a.vehicles}),
            }[group_by]
            for key in keys:
                groups[key].append(a)
        rows = [
            StatsRow(
                group=key,
                accidents=len(items),
                deaths=sum(a.deaths for a in items),
                injured=sum(a.injured for a in items),
                damages_usd=sum(a.damages_usd for a in items),
            )
            for key, items in groups.items()
        ]
        return sorted(rows, key=lambda r: (-r.accidents, r.group))

    def search_reports(
        self, text: str | None, road_code: str | None, limit: int
    ) -> list[ReportHit]:
        self._check("search_reports")
        superseded_by = {r.supersedes: r.report_id for r in self.dataset.reports if r.supersedes}
        hits = []
        for report in self.dataset.reports:
            if road_code is not None and report.road_code != road_code:
                continue
            for section in report.sections:
                score = _score(f"{section.title} {section.text}", text) if text else None
                if text and not score:
                    continue
                hits.append(
                    ReportHit(
                        report_id=report.report_id,
                        title=report.title,
                        date=report.date,
                        status=report.status,
                        road_code=report.road_code,
                        section_order=section.order,
                        section_title=section.title,
                        text=section.text,
                        score=score,
                        supersedes=report.supersedes,
                        superseded_by=superseded_by.get(report.report_id),
                    )
                )
        hits.sort(key=lambda h: (h.report_id, h.section_order))
        hits.sort(key=lambda h: (h.score or 0) if text else h.date.toordinal(), reverse=True)
        hits.sort(key=lambda h: h.status is not ReportStatus.VIGENTE)
        return hits[:limit]

    def dataset_info(self) -> DatasetSummary:
        self._check("dataset_info")
        info = self.dataset.info
        return DatasetSummary(
            source=info.source,
            source_file=info.source_file,
            sha256=info.sha256,
            generated=info.generated,
        )


# --- Proveedor de IA guionizado (tarea 4.10) ---

Step = LLMResult | Exception | Callable[[list[Message]], LLMResult]


def answer(text: str) -> LLMResult:
    return LLMResult(content=text, tool_calls=[], model="fake/llm")


def call(*calls: tuple[str, dict[str, Any]]) -> LLMResult:
    return LLMResult(
        content=None,
        tool_calls=[
            ToolCall(id=f"call_{i}", name=name, arguments=json.dumps(args))
            for i, (name, args) in enumerate(calls, start=1)
        ],
        model="fake/llm",
    )


_TOOL_BLOCK = re.compile(rf"<{TOOL_RESULT_TAG}>\n(.*)\n</{TOOL_RESULT_TAG}>", re.S)


def tool_results(messages: list[Message]) -> list[dict[str, Any]]:
    """Resultados de herramientas del turno actual, tal como los recibe el LLM."""
    last_user = max(i for i, m in enumerate(messages) if m.role == "user")
    results = []
    for message in messages[last_user:]:
        if message.role == "tool" and message.content:
            match = _TOOL_BLOCK.search(message.content)
            assert match, "resultado de herramienta sin delimitar"
            results.append(json.loads(match.group(1)))
    return results


def context_ids(messages: list[Message]) -> list[str]:
    """Ids del contexto de la sesion que el orquestador entrega al LLM."""
    for message in messages:
        if (
            message.role == "system"
            and message.content
            and "Contexto de la sesion" in message.content
        ):
            return re.findall(r"SIN-\d{4}-\d{4}", message.content)
    return []


class FakeLLMProvider:
    """Cada llamada consume un paso: un resultado, una excepcion o una funcion de los mensajes."""

    def __init__(self, steps: list[Step]) -> None:
        self.steps = list(steps)
        self.calls: list[list[Message]] = []
        self.tools: list[ToolSpec] = []

    def complete(self, messages: Any, tools: Any) -> LLMResult:
        self.calls.append(list(messages))
        self.tools = list(tools)
        if not self.steps:
            raise AssertionError("el guion del LLM simulado se agoto")
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(list(messages))
        return step


class ListLogger:
    """Logger de eventos que guarda (nivel, evento, campos) para las aserciones."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, event: str, **fields: Any) -> None:
        self.events.append(("info", event, fields))

    def warning(self, event: str, **fields: Any) -> None:
        self.events.append(("warning", event, fields))

    def named(self, event: str) -> list[dict[str, Any]]:
        return [fields for _, name, fields in self.events if name == event]
