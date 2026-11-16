"""Guardia de la convencion "solo ASCII" del repositorio (CLAUDE.md).

- Python: los caracteres no ASCII dentro de literales de texto se reescriben como escapes
  `\\uXXXX`; el valor en ejecucion no cambia. En comentarios, docstrings, identificadores,
  f-strings y cadenas raw son error: ahi se escribe sin tildes o se escapa a mano.
- Markdown: solo se permiten dentro de `codigo` y de bloques ``` (valores originales del JSON).
  Los emojis son error en cualquier lugar.
- Otros archivos (TOML, YAML): todo el archivo debe ser ASCII.

Uso: uv run python scripts/ascii_guard.py [--check] ARCHIVO...
Sale con 1 si reescribio algun archivo o encontro errores, como espera pre-commit.
"""

import argparse
import io
import re
import sys
import tokenize
from pathlib import Path
from typing import NamedTuple

_CODE_SPAN = re.compile(r"`[^`]*`")
_EMOJI_START = 0x1F000
_STATEMENT_START = {None, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT}
_IGNORED = {tokenize.NL, tokenize.COMMENT}


class Problem(NamedTuple):
    line: int
    column: int
    message: str


def _escape(text: str) -> str:
    return "".join(
        ch if ch.isascii() else (f"\\u{ord(ch):04x}" if ord(ch) <= 0xFFFF else f"\\U{ord(ch):08x}")
        for ch in text
    )


def _is_raw(token_text: str) -> bool:
    prefix = token_text[: min(i for i in (token_text.find('"'), token_text.find("'")) if i >= 0)]
    return "r" in prefix.lower()


def fix_python(source: str) -> tuple[str, list[Problem]]:
    """Devuelve el codigo con los literales escapados y los problemas que no se arreglan solos."""
    if source.isascii():
        return source, []
    tokens = [t for t in tokenize.generate_tokens(io.StringIO(source).readline)]
    significant = [t for t in tokens if t.type not in _IGNORED]
    line_starts = [0]
    for line in source.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    replacements: list[tuple[int, int, str]] = []
    problems: list[Problem] = []
    for token in tokens:
        if token.string.isascii():
            continue
        (row, col), (end_row, end_col) = token.start, token.end
        if token.type != tokenize.STRING:
            kind = tokenize.tok_name[token.type].lower()
            problems.append(Problem(row, col, f"caracter no ASCII en {kind}"))
            continue
        index = significant.index(token)
        before = significant[index - 1].type if index > 0 else None
        after = significant[index + 1].type if index + 1 < len(significant) else None
        if before in _STATEMENT_START and after in {tokenize.NEWLINE, tokenize.ENDMARKER}:
            message = "caracter no ASCII en docstring: escribir sin tildes"
            problems.append(Problem(row, col, message))
        elif _is_raw(token.string):
            problems.append(Problem(row, col, "caracter no ASCII en cadena raw: escapar a mano"))
        else:
            start = line_starts[row - 1] + col
            end = line_starts[end_row - 1] + end_col
            replacements.append((start, end, _escape(token.string)))

    for start, end, text in reversed(replacements):
        source = source[:start] + text + source[end:]
    return source, problems


def check_markdown(text: str) -> list[Problem]:
    problems: list[Problem] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        for column, ch in enumerate(line):
            if ord(ch) >= _EMOJI_START:
                problems.append(Problem(number, column, "emoji"))
                break
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Se reemplaza cada span por espacios para conservar las columnas.
        visible = _CODE_SPAN.sub(lambda m: " " * len(m.group()), line)
        for column, ch in enumerate(visible):
            if not ch.isascii():
                problems.append(Problem(number, column, "caracter no ASCII fuera de `codigo`"))
                break
    return problems


def check_plain(text: str) -> list[Problem]:
    return [
        Problem(number, next(c for c, ch in enumerate(line) if not ch.isascii()), "no ASCII")
        for number, line in enumerate(text.splitlines(), start=1)
        if not line.isascii()
    ]


def process(path: Path, *, write: bool) -> tuple[bool, list[Problem]]:
    """Revisa un archivo; devuelve si lo reescribio (o lo reescribiria) y sus problemas."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        fixed, problems = fix_python(text)
        changed = fixed != text
        if changed and write:
            path.write_text(fixed, encoding="utf-8")
        return changed, problems
    if path.suffix == ".md":
        return False, check_markdown(text)
    return False, check_plain(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true", help="no reescribe, solo informa")
    args = parser.parse_args(argv)

    failed = False
    for path in args.files:
        changed, problems = process(path, write=not args.check)
        if changed:
            failed = True
            action = "requiere escapes" if args.check else "literales escapados"
            print(f"{path}: {action}")
        for problem in problems:
            failed = True
            print(f"{path}:{problem.line}:{problem.column + 1}: {problem.message}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
