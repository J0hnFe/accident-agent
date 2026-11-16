"""Memoria de conversacion por sesion (tarea 4.4).

Guarda los ultimos N turnos (pregunta y respuesta final, sin los mensajes de herramientas) y los
ids de los ultimos siniestros consultados, que resuelven seguimientos como "genera el informe de
esos accidentes". Vive en memoria: se pierde al reiniciar (limitacion documentada).
"""

import threading
from collections import deque
from collections.abc import Sequence
from typing import Protocol

from accident_agent.core.llm import Message


class ConversationMemory(Protocol):
    def history(self, session_id: str) -> list[Message]: ...

    def add_turn(self, session_id: str, user: str, assistant: str) -> None: ...

    def last_accident_ids(self, session_id: str) -> list[str]: ...

    def set_last_accident_ids(self, session_id: str, ids: Sequence[str]) -> None: ...

    def reset(self, session_id: str) -> bool: ...


class InMemoryConversationMemory:
    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max_turns
        self._turns: dict[str, deque[tuple[str, str]]] = {}
        self._ids: dict[str, list[str]] = {}
        # La API atiende solicitudes en hilos distintos.
        self._lock = threading.Lock()

    def history(self, session_id: str) -> list[Message]:
        with self._lock:
            turns = list(self._turns.get(session_id, ()))
        messages = []
        for user, assistant in turns:
            messages += [
                Message(role="user", content=user),
                Message(role="assistant", content=assistant),
            ]
        return messages

    def add_turn(self, session_id: str, user: str, assistant: str) -> None:
        with self._lock:
            turns = self._turns.setdefault(session_id, deque(maxlen=self._max_turns))
            turns.append((user, assistant))

    def last_accident_ids(self, session_id: str) -> list[str]:
        with self._lock:
            return list(self._ids.get(session_id, []))

    def set_last_accident_ids(self, session_id: str, ids: Sequence[str]) -> None:
        with self._lock:
            self._ids[session_id] = list(ids)

    def reset(self, session_id: str) -> bool:
        with self._lock:
            existed = session_id in self._turns or session_id in self._ids
            self._turns.pop(session_id, None)
            self._ids.pop(session_id, None)
            return existed
