import pytest
from pydantic import ValidationError

from accident_agent.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OPENROUTER_MODELS", "DEFAULT_TIMEZONE", "ORCH_MAX_ITERATIONS", "LANGFUSE_HOST"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_without_env_file() -> None:
    settings = Settings(_env_file=None)

    assert settings.default_timezone == "America/Guayaquil"
    assert settings.orch_max_iterations == 5
    assert settings.llm_timeout_seconds == 30
    assert settings.openrouter_models == []
    assert settings.langfuse_enabled is False


def test_models_are_parsed_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_MODELS", " model-a:free , model-b:free,,")

    settings = Settings(_env_file=None)

    assert settings.openrouter_models == ["model-a:free", "model-b:free"]


def test_invalid_timezone_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEFAULT_TIMEZONE", "Mars/Olympus")

    with pytest.raises(ValidationError, match="Zona horaria IANA invalida"):
        Settings(_env_file=None)


def test_secrets_are_not_exposed_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-secret")

    settings = Settings(_env_file=None)

    assert "sk-test-secret" not in repr(settings)
    assert settings.openrouter_api_key.get_secret_value() == "sk-test-secret"
