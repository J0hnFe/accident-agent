"""Registro de herramientas (tarea 4.3). Agregar una herramienta no cambia el orquestador."""

from typing import Any

from accident_agent.core.tool import Tool, ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool[Any, Any]] = {}

    def register(self, tool: Tool[Any, Any]) -> None:
        if tool.name in self._tools:
            raise ValueError(f"herramienta duplicada: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool[Any, Any] | None:
        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    @property
    def names(self) -> list[str]:
        return list(self._tools)
