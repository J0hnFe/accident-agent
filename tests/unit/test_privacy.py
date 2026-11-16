import pytest

from accident_agent.domain.privacy import find_personal_data, redact

# Casos de la regla P6 de docs/datos/politica_datos_personales.md.
POSITIVE = ["1712345678", "171234567-8", "1712345678001", "PBX-1234", "gye123", "IA123B", "ABC-123"]
NEGATIVE = ["SIN-2026-0009", "INF-2026-02", "41000", "12+000", "E35", "BT-50", "CG 150", "T800"]


@pytest.mark.parametrize("value", POSITIVE)
def test_personal_data_is_detected(value: str) -> None:
    assert find_personal_data(f"dato: {value}.")


@pytest.mark.parametrize("value", NEGATIVE)
def test_domain_values_are_not_flagged(value: str) -> None:
    assert find_personal_data(f"dato: {value}.") == []


def test_kinds_are_reported_without_values() -> None:
    assert find_personal_data("cedula 1712345678 y placa PBX-1234") == ["cedula", "placa_auto"]


def test_redact_replaces_every_match() -> None:
    text = "Conductor 1712345678 en PBX-1234, siniestro SIN-2026-0009"
    assert redact(text) == "Conductor [CEDULA] en [PLACA], siniestro SIN-2026-0009"
