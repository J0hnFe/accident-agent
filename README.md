# accident-agent

Orquestador propio en Python con tres herramientas: consultas RAG sobre Neo4j,
hora actual e informes Markdown. CLI y API REST comparten el mismo nucleo.
Los datos son ficticios: 29 siniestros vigentes entre 2025-01-12 y 2026-09-02,
18 fallecidos y 44 heridos; un registro anulado se conserva por trazabilidad.

## Requisitos

- Docker Engine o Docker Desktop en ejecucion, con Docker Compose v2 que soporte
  `env_file.required` (2.24 o posterior), acceso a Internet para descargar imagenes.
- Puertos locales 7474, 7687 y 8000 disponibles.
- Una clave de OpenRouter para conversar. La carga y las pruebas simuladas no la necesitan.
- Para desarrollo local: Python 3.12 y uv. Las versiones estan en `uv.lock`.

## Instalacion y comando unico

Desde la raiz de una copia del repositorio:

```sh
cp .env.example .env
```

Editar `.env`: definir `NEO4J_PASSWORD` (al menos 8 caracteres) y
`OPENROUTER_API_KEY`. No publicar este archivo. Conservar `NEO4J_USER=neo4j`.
Los modelos configurados en `.env.example` son los usados en las evidencias;
su disponibilidad depende del proveedor. `LANGFUSE_PUBLIC_KEY` y
`LANGFUSE_SECRET_KEY` son opcionales: sin ambas se utiliza `NoopTracer`.

```sh
docker compose up -d --build
docker compose ps -a
docker compose logs loader
curl -s http://localhost:8000/health
```

Neo4j debe estar saludable, el loader terminar con codigo 0 y la API estar activa.
`up -d` inicia servicios; la API puede necesitar unos segundos adicionales.
El loader verifica SHA-256, normaliza el original montado en solo lectura y carga
30 nodos Accident (29 vigentes), 4 informes y ningun nombre, cedula ni placa.
Los conteos incluyen 7 siniestros vigentes con motocicleta.

- Swagger: <http://localhost:8000/docs>.
- Neo4j Browser: <http://localhost:7474> (usuario `neo4j` y clave de `.env`).
- Health informa `status`, `neo4j` y `llm_configured`. Este ultimo solo comprueba
  que exista una clave; no comprueba su validez ni su cuota.

## CLI

```sh
docker compose run --rm cli ask "Cuantos siniestros hubo en Pichincha?" --verbose
docker compose run --rm cli chat --verbose
```

En el chat: `/ayuda`, `/historial`, `/reiniciar` y `/salir`.
Probar "Que siniestros con fallecidos hubo en la E35?" y luego
"Genera el informe de esos accidentes". `ask` crea una sesion nueva por ejecucion;
para seguimientos usar `chat`. `--verbose` muestra herramientas, parametros,
estado, duracion, `trace_id` y motivo de parada.

## API REST

```sh
curl -s http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo","message":"Que siniestros con fallecidos hubo en la E35?"}'
curl -s http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo","message":"Genera el informe de esos accidentes"}'
curl -i -X DELETE http://localhost:8000/sessions/demo
```

`POST /chat` devuelve `session_id`, `answer`, `tools_used`, `trace_id` y
`stop_reason`. Si se omite la sesion, se crea una nueva. El mensaje admite
1 a 2000 caracteres y no puede contener solo espacios. La sesion admite
1 a 64 letras ASCII, numeros, guiones o guiones bajos.

| Ruta | Resultado |
| --- | --- |
| `GET /health` | 200; `ok` o `degraded` segun Neo4j |
| `POST /chat` | 200 con respuesta; revisar `stop_reason`, incluso ante fallo del LLM |
| `GET /reports/{report_id}` | Markdown (200) o informe no encontrado (404) |
| `DELETE /sessions/{session_id}` | 204 o sesion no encontrada (404) |

Entradas invalidas: 422; error interno: 500. Los errores HTTP usan
`{"error":{"type":"...","message":"..."}}`, con `details` en validaciones.
Los fallos de herramientas se comunican al orquestador para que pueda responder.

## Informes y persistencia

Usar el `report_id` devuelto por la conversacion:

```sh
curl -f http://localhost:8000/reports/RPT-AAAAMMDD-HHMMSS-abcdef -o informe.md
```

Reemplazar el identificador de ejemplo por uno real. El endpoint solo encuentra
los informes creados en el proceso/contenedor de la API. En Compose, `reports/`
y `logs/` no tienen volumen: se pierden al recrear el contenedor; el contenedor
CLI con `--rm` se elimina al salir. Para conservar informes de CLI, montar las rutas:

```sh
mkdir -p reports logs
docker compose run --rm -v "$PWD/reports:/app/reports" -v "$PWD/logs:/app/logs" cli chat
```

Neo4j si persiste en el volumen `neo4j_data`. `docker compose down` conserva ese
volumen. `docker compose down -v` elimina los datos: usarlo solo si se quiere
reconstruir la base desde el JSON. No hace falta para el arranque habitual.

## Desarrollo y pruebas

```sh
uv sync --frozen
uv run accident-agent version
uv run accident-agent ask "Que hora es?" --verbose
uv run uvicorn accident_agent.interfaces.api:app --host 127.0.0.1 --port 8000
```

La API local usa `NEO4J_URI=bolt://localhost:7687` y un solo worker. Detener la API
Docker antes de ocupar el mismo puerto. Para recargar: `uv run accident-agent ingest`.
Alternativa pip, dentro de un entorno Python 3.12: `pip install -r requirements.txt`
y `pip install --no-deps -e .`; uv tambien instala las herramientas de desarrollo.

```sh
uv run pytest
uv run pytest -m 'not e2e' --cov=accident_agent --cov-report=term-missing
uv run ruff check
uv run ruff format --check
uv run mypy src tests scripts
uv run pre-commit install
```

La suite por defecto incluye escenarios con LLM simulado, sin Neo4j ni cuota.
El segundo comando incluye integracion y requiere el Neo4j cargado de Compose.
`uv run pytest -m integration` ejecuta solo integracion.
`uv run pytest -m e2e` usa OpenRouter real, consume cuota y puede omitirse si el
proveedor no esta disponible; no es requisito para la suite reproducible.
Resultados historicos de etapa 5: 748 pasan, 1 omitida; cobertura 97% total,
99% en `core/` y 98% en `tools/`. Ver [evidencia](docs/evidencias/5.9_pytest_cobertura.txt).

## Configuracion

Todas las variables y sus valores iniciales estan en [.env.example](.env.example).

| Grupo | Variables / valores iniciales |
| --- | --- |
| Grafo | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` |
| IA | `OPENROUTER_API_KEY`, `OPENROUTER_MODELS` (lista separada por comas) |
| Trazas opcionales | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` |
| Limites | `ORCH_MAX_ITERATIONS=5`, `ORCH_MAX_TOOL_CALLS_PER_ITERATION=4` |
| Tiempo en segundos | `LLM_TIMEOUT_SECONDS=30`; herramientas hora 2, busqueda 10, informe 15 |
| Memoria | `MEMORY_MAX_TURNS=10` |
| General | `DEFAULT_TIMEZONE=America/Guayaquil`, `LOG_LEVEL=INFO` |
| Rutas | `DATA_FILE`, `REPORTS_DIR`, `LOGS_DIR` |

Compose fija el host Neo4j a `neo4j` dentro de su red. Aplicar cambios de entorno
recreando los servicios. Cambiar la clave en `.env` no cambia automaticamente la
clave de una base ya inicializada: debe coincidir con la del volumen existente.

## Solucion de problemas

| Sintoma | Comprobacion o accion |
| --- | --- |
| Compose pide una clave | Completar `NEO4J_PASSWORD` en `.env` |
| Neo4j no esta saludable | `docker compose logs neo4j`; comprobar clave, memoria y puertos |
| Loader falla | `docker compose logs loader`; verificar el JSON original y conexion |
| API aun no responde | Esperar al loader; consultar `docker compose logs api` |
| Clave IA invalida | Corregir `OPENROUTER_API_KEY` y recrear la API |
| Limite de uso | Reintentar mas tarde; un respaldo no evita una cuota de cuenta agotada |
| Modelo no disponible | Actualizar `OPENROUTER_MODELS` con modelos que admitan herramientas |
| Informe 404 | Revisar id, origen API/CLI y si se recreo el contenedor |
| Sin coincidencias | Ampliar filtros; el dataset es cerrado y no se consulta Internet |
| Pregunta de seguimiento sin contexto | Reutilizar `session_id` o permanecer en el mismo chat |

## Estructura y documentos

- `src/accident_agent/core/`: contratos, memoria, registro y orquestador.
- `ingestion/`, `domain/`, `graph/`: normalizacion, catalogos y repositorio Neo4j.
- `tools/`, `providers/`, `observability/`, `interfaces/`: adaptadores y entradas.
- `tests/`: pruebas unitarias, contrato, integracion y escenarios.
- [Plan y estado de entrega](docs/PLAN_DESARROLLO.md).
- [Documento tecnico (PDF)](docs/entrega/DOCUMENTO_TECNICO.pdf) y [fuente](docs/entrega/DOCUMENTO_TECNICO.md).
- [Documento funcional (PDF)](docs/entrega/DOCUMENTO_FUNCIONAL.pdf) y [fuente](docs/entrega/DOCUMENTO_FUNCIONAL.md).
- [Evidencias](docs/evidencias/etapa-5_notas.md) y [modelo del grafo](docs/modelo_grafo.md).

El enunciado original `Prueba_Tecnica_Orquestador_Multiagente_BIT.docx` se conserva
localmente y no se publica; su guia reorganizada esta en `docs/enunciado/`.

## Alcance y limitaciones

Sin interfaz grafica, embeddings, autenticacion ni persistencia de sesiones.
Puertos Docker publicados solo en localhost; no exponer la API directamente.
Las coordenadas son referenciales y los datos no representan estadistica nacional.
La guardia de grounding advierte ids no recuperados, pero no valida cada cifra.
El informe es determinista; la redaccion conversacional depende del modelo.

El JSON original se distribuye tal cual por decision documentada del candidato;
contiene datos personales ficticios. Esos campos y el informe reservado INF-RES-01
se excluyen del grafo. Logs y trazas aplican redaccion; no enviar datos personales
en las preguntas: el mensaje enviado al proveedor y su respuesta no tienen la
misma garantia de redaccion que los logs. Langfuse es opcional y externo.
