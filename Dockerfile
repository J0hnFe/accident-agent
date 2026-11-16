# Imagen unica para loader, api y cli (tarea 2.4).
# Versiones fijadas con al menos dos semanas de publicadas (seccion 12 del plan).
FROM python:3.12.15-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencias primero: esta capa solo se reconstruye si cambia el lockfile.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# Usuario sin privilegios; data/ se monta como solo lectura en el loader.
RUN useradd --create-home --uid 1000 app && mkdir -p reports logs && chown app reports logs
USER app

CMD ["accident-agent", "--help"]
