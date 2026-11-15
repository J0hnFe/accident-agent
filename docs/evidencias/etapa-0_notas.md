# Etapa 0 - Notas de cierre

- **Fecha de cierre:** 2026-11-15.
- **Tareas:** 0.1 a 0.6, todas cerradas (0.3b `[R]` incluida).

## Decisiones tecnologicas y alternativas descartadas

| Area | Decision | Alternativas descartadas y motivo |
| --- | --- | --- |
| Entorno de Python | uv con Python 3.12 (`.python-version`) | Python del sistema (3.9.6, no cumple el minimo de 3.10); pip y venv, sin lockfile nativo; Poetry, mas lento y sin gestion del interprete |
| Dependencias | `==` en `pyproject.toml`, `uv.lock` y `requirements.txt` exportado | Solo `requirements.txt`, sin separar dependencias directas de transitivas ni grupos de desarrollo |
| Antiguedad de versiones | `exclude-newer = 2026-11-01` en `[tool.uv]` | Ultimas versiones del dia: mayor riesgo de regresiones recien publicadas |
| Orquestacion | Orquestador propio con function calling nativo | LangGraph: el ciclo es pequeno, habria que envolverlo igual en abstracciones propias y anade dependencias de LangChain |
| Proveedor de IA | OpenRouter con modelos `:free` y lista de respaldo | Google AI Studio y Groq (ejemplos del enunciado): OpenRouter da acceso a varios fabricantes con una sola clave y una API compatible con OpenAI, lo que permite el respaldo entre proveedores |
| Trazas | Langfuse Cloud (Hobby, region US) detras de un puerto `Tracer` | Langfuse autoalojado: requiere unos 6 contenedores; sin trazas: se pierde evidencia visual para el documento tecnico |
| Imagen de Neo4j | `neo4j:5.26.31-community` (5.26 LTS) | 5.26.32 y 5.26.33, con menos de dos semanas; rama 2026.x, que no es LTS |
| Enunciado `.docx` | En `docs/enunciado/`, no versionado (`*.docx` en `.gitignore`) | Publicarlo: es material de BIT |
| JSON original | Versionado y publicado en `data/` | Excluirlo del repositorio: rompe la carga con un solo comando. Decision del candidato del 2026-11-15; la PII sigue sin cargarse en Neo4j |
| Calidad | ruff, mypy estricto y pre-commit con gitleaks | Revisar los secretos solo a mano: propenso a errores |

## Modelos de IA elegidos

De 467 modelos de OpenRouter, 14 eran `:free` con `tools`. Se probaron 3 con una llamada de tool calling real (ver `0.3_prueba_tool_calling.md`):

| Orden | Modelo | Resultado de la prueba |
| --- | --- | --- |
| Principal | `nvidia/nemotron-3-ultra-550b-a55b:free` | Tool call correcto; 0.9 s y 2.6 s; buen espanol |
| Respaldo 1 | `nvidia/nemotron-3.5-super-vl:free` | Tool call correcto; 3.2 s y 2.5 s; buen espanol |
| Respaldo 2 | `google/gemma-4-31b-it:free` | 429 upstream en 2 intentos; se conserva porque usa otro proveedor (Google) |

## Cifras relevantes

- **OpenRouter (plan gratuito):** 20 solicitudes por minuto y 50 por dia (1000 por dia con 10 creditos o mas comprados).
- **Langfuse Hobby:** 50 000 unidades por mes, 30 dias de acceso a datos e ingesta de 1 000 solicitudes por minuto. Uso estimado: unas 7 500 unidades al mes, el 15 % del plan.
- **Arbol de dependencias:** 56 paquetes en `uv.lock`, 11 directas de ejecucion y 6 de desarrollo.
- **SHA-256 del JSON original:** `77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280`, identico antes y despues de moverlo a `data/` y tras ejecutar los hooks.
- **Pruebas:** 4 de 4 pasan; ruff, ruff format, mypy estricto (16 archivos) y los 9 hooks de pre-commit pasan.

## Versiones fijadas

| Componente | Version |
| --- | --- |
| uv | 0.13.8 |
| Python | 3.12.16 |
| Docker Engine / Compose | 29.9.3 / v5.7.0 |
| Neo4j (imagen) | 5.26.31-community |
| fastapi / uvicorn | 0.162.0 / 0.54.0 |
| neo4j (driver) | 6.4.1 |
| httpx | 0.28.1 |
| pydantic / pydantic-settings | 2.14.2 / 2.16.2 |
| jinja2 | 3.1.6 |
| typer / rich | 0.27.3 / 15.0.0 |
| structlog | 26.1.0 |
| tzdata | 2026.6 |
| pytest / pytest-cov / respx | 9.2.0 / 7.1.0 / 0.23.1 |
| ruff / mypy / pre-commit | 0.17.3 / 2.4.1 / 4.7.0 |
| Hooks | pre-commit-hooks v6.0.0, ruff-pre-commit v0.17.3, gitleaks v8.30.1 |

## Problemas encontrados y solucion

| Problema | Solucion |
| --- | --- |
| uv no estaba instalado y el Python del sistema era 3.9.6 | `brew install uv` y `uv python install 3.12` |
| `google/gemma-4-31b-it:free` respondio 429 upstream en dos intentos | Queda como ultimo respaldo; se confirma la necesidad de reintentos y de modelos de respaldo (escenario 15) |
| El contador `free_model_daily_requests` seguia en 0 tras 6 solicitudes | Se registra como observado (posible retraso); el diseno asume el limite de 50 por dia |
| Typer ejecutaba la aplicacion de un solo comando como ese comando (`accident-agent version` fallaba) | `@app.callback()` para forzar el grupo de comandos |
| mypy marco como innecesarios los `type: ignore` sobre `Settings(_env_file=None)` | Se eliminaron; el plugin de Pydantic ya reconoce el argumento |
| El panel de Langfuse entrega `LANGFUSE_BASE_URL`, no el `LANGFUSE_HOST` del plan | Se adopto `LANGFUSE_BASE_URL` en la configuracion, `.env.example` y el plan |
| Las variables exportadas en la shell podian alterar las pruebas de configuracion | La fixture borra todas las variables que lee `Settings` |
| `GUIA_PRUEBA_TECNICA.md` tenia tildes, contra la regla de solo ASCII | Se movio a `docs/enunciado/` y se registro como excepcion en `CLAUDE.md` y en el plan |

## Archivos y modulos clave

- **Proyecto:** `pyproject.toml`, `uv.lock`, `requirements.txt`, `.python-version`, `.gitignore`, `.env.example` y `.pre-commit-config.yaml`.
- **Codigo:**
  - `src/accident_agent/config.py`: `Settings` con secretos como `SecretStr` y validacion de la zona horaria.
  - `src/accident_agent/interfaces/cli.py`: CLI minima del entry point `accident-agent`.
- **Pruebas:** `tests/unit/test_config.py`.
- **Datos:** `data/siniestros_raw.json` y `data/siniestros_raw.json.sha256`.
- **Documentacion:** `docs/enunciado/` (guia de la prueba y `.docx` local); `CLAUDE.md` actualizado con la excepcion al ASCII y la publicacion del JSON.
- **Repositorio:** git local en la rama `main`, commit inicial `5db0a2a`.

## Evidencias guardadas

- `0.2_entorno_local.md`: versiones de uv, Python y Docker.
- `0.3_limites_openrouter.md`: limites del plan gratuito con fecha y fuente.
- `0.3_prueba_tool_calling.md`: prueba real de tool calling con 3 modelos.
- `0.3b_limites_langfuse.md`: limites del plan Hobby y verificacion de las claves.
- `0.4_esqueleto_proyecto.md`: SHA-256, politica de versiones y verificacion.
- `0.5_git_precommit.md`: hooks y su ejecucion sobre todos los archivos.

## Secciones de los documentos finales que alimenta

- **Documento tecnico:**
  - 5.11 Integracion con el proveedor de IA: limites, modelos y prueba de tool calling.
  - 5.12 Observabilidad: plan y limites de Langfuse.
  - 5.13 Seguridad y privacidad: gitleaks, `.env` ignorado y publicacion del JSON.
  - 5.14 Infraestructura y reproducibilidad: uv, versiones fijadas y variables de entorno.
  - 5.16 Limitaciones: cuota diaria de 50 solicitudes.
- **Documento funcional:** ninguna seccion en esta etapa.
