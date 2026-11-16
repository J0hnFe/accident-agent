import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ascii_guard.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ascii_guard", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ascii_guard"] = module
    spec.loader.exec_module(module)
    return module


guard = _load()

# Las muestras se arman con chr() para no depender de la propia guardia en este archivo.
E_ACUTE = chr(0xE9)
N_TILDE = chr(0xF1)
EN_DASH = chr(0x2013)
EMOJI = chr(0x1F600)


def _run(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(compile(source, "<muestra>", "exec"), namespace)  # noqa: S102
    return namespace["value"]


@pytest.mark.parametrize(
    "literal",
    [
        f'"P{E_ACUTE}rdida de pista"',
        f"'Ca{N_TILDE}ar'",
        f'"VIA CUENCA{EN_DASH}AZOGUES"',
        f'"""texto\nde varias l{E_ACUTE}neas"""',
        f'b"x" + "{E_ACUTE}".encode() and "{EMOJI}"',
    ],
)
def test_string_literals_are_escaped_without_changing_value(literal: str) -> None:
    source = f"value = {literal}\n"
    fixed, problems = guard.fix_python(source)
    assert problems == []
    assert fixed.isascii()
    assert _run(fixed) == _run(source)


def test_escape_format() -> None:
    fixed, _ = guard.fix_python(f'value = ("{E_ACUTE}", "{EMOJI}")\n')
    assert fixed == 'value = ("\\u00e9", "\\U0001f600")\n'


def test_ascii_source_is_unchanged() -> None:
    source = 'value = "Perdida de pista"  # sin tildes\n'
    assert guard.fix_python(source) == (source, [])


def test_fix_is_idempotent() -> None:
    once, _ = guard.fix_python(f'value = "{E_ACUTE}"\n')
    assert guard.fix_python(once) == (once, [])


@pytest.mark.parametrize(
    ("source", "fragment"),
    [
        (f"value = 1  # funci{E_ACUTE}n\n", "comment"),
        (f'"""M{E_ACUTE}dulo."""\nvalue = 1\n', "docstring"),
        (f'def f():\n    """Cami{E_ACUTE}n."""\n    return 1\nvalue = 1\n', "docstring"),
        (f'value = r"\\d+ {E_ACUTE}"\n', "raw"),
        (f"a{N_TILDE}o = 1\nvalue = 1\n", "name"),
        (f'x = 1\nvalue = f"{{x}} {E_ACUTE}"\n', "fstring"),
    ],
)
def test_problems_that_are_not_fixed_automatically(source: str, fragment: str) -> None:
    fixed, problems = guard.fix_python(source)
    assert fixed == source
    assert len(problems) == 1
    assert fragment in problems[0].message


def test_markdown_allows_code_spans_and_fences() -> None:
    text = (
        "Valores originales: `Rumi" + N_TILDE + "ahui` y `P" + E_ACUTE + "rdida`.\n"
        "```\n"
        "Pe" + "at" + chr(0xF3) + "n en la v" + chr(0xED) + "a\n"
        "```\n"
        "Texto en ASCII.\n"
    )
    assert guard.check_markdown(text) == []


def test_markdown_rejects_text_outside_code() -> None:
    text = "linea uno\nCanci" + chr(0xF3) + "n fuera de codigo `ok`\n"
    problems = guard.check_markdown(text)
    assert [(p.line, p.column) for p in problems] == [(2, 5)]


def test_markdown_rejects_emoji_even_in_code() -> None:
    assert len(guard.check_markdown(f"`{EMOJI}`\n")) == 1


def test_plain_files_must_be_ascii() -> None:
    assert guard.check_plain("a = 1\nb = 2\n") == []
    assert [p.line for p in guard.check_plain(f"a = 1\nb = '{E_ACUTE}'\n")] == [2]


def test_main_rewrites_python_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = tmp_path / "sample.py"
    module.write_text(f'value = "{E_ACUTE}"\n', encoding="utf-8")
    notes = tmp_path / "notes.md"
    notes.write_text(f"`{E_ACUTE}` ok\n", encoding="utf-8")

    assert guard.main(["--check", str(module), str(notes)]) == 1
    assert module.read_text(encoding="utf-8") == f'value = "{E_ACUTE}"\n'

    assert guard.main([str(module), str(notes)]) == 1
    assert module.read_text(encoding="utf-8") == 'value = "\\u00e9"\n'
    assert guard.main([str(module), str(notes)]) == 0
    assert "literales escapados" in capsys.readouterr().out
