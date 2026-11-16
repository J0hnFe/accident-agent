"""Patrones de datos personales (regla P6 de `docs/datos/politica_datos_personales.md`).

Son genericos: no dependen de los valores ficticios del JSON (todas sus cedulas empiezan con 99
y todas sus placas son de auto). Los usan la verificacion posterior a la carga (tarea 2.6) y la
redaccion de logs y trazas (tarea 4.6).
"""

import re
from typing import Final

# (tipo, patron, reemplazo). El orden importa: el RUC contiene una cedula.
_PATTERNS: Final = (
    ("ruc", re.compile(r"\b\d{13}\b"), "[CEDULA]"),
    ("cedula", re.compile(r"\b\d{10}\b"), "[CEDULA]"),
    ("cedula_guion", re.compile(r"\b\d{9}-\d\b"), "[CEDULA]"),
    # (?!-\d) evita tomar "SIN-2026" de "SIN-2026-0009" como placa.
    ("placa_auto", re.compile(r"\b[A-Z]{3}-?\d{3,4}\b(?!-\d)", re.IGNORECASE), "[PLACA]"),
    ("placa_moto", re.compile(r"\b[A-Z]{2}-?\d{3}[A-Z]\b", re.IGNORECASE), "[PLACA]"),
)


def find_personal_data(text: str) -> list[str]:
    """Tipos de dato personal presentes en el texto, sin devolver los valores."""
    return [kind for kind, pattern, _ in _PATTERNS if pattern.search(text)]


def redact(text: str) -> str:
    for _, pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
