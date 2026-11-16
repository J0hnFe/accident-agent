# Etapa 2 - Notas de cierre

- **Fecha:** 2026-11-15.
- **Tareas:** 2.1 a 2.8.
- **DoD verificada:**
  - `docker compose down -v --rmi local && docker compose up -d --build` deja los datos cargados y verificados en 12 s con la cache de construccion (`2.8_docker_compose_up.txt`); el loader sale con 0 (`2.6_salida_loader.txt`).
  - Todos los valores de control coinciden, mas los conteos de nodos por etiqueta y de relaciones por tipo.
  - Muestra revisada: SIN-2025-0001 en el grafo coincide campo por campo con el JSON (`2.8_consultas_ejemplo.txt`, seccion "Muestra") y en Neo4j Browser (`2.8_subgrafo_neo4j_browser.png`: 15 nodos, las 4 personas en sus vehiculos, sin datos personales ni metadatos de texto en el PNG).
  - 515 pruebas unitarias y 9 de integracion en verde; ruff, mypy, `ascii_guard` y pre-commit sin errores.

## Decisiones y alternativas descartadas

| Area | Decision | Alternativas descartadas y motivo |
| --- | --- | --- |
| `km` | Propiedad de `ON_ROAD` (posicion en la via) | En `Accident` y en `ON_ROAD`, como proponia el plan: dato duplicado |
| Rol y condicion de la persona | Solo en `Person` | Tambien en `PARTICIPATED_IN`: la persona pertenece a un solo siniestro, duplicaria el dato |
| Canton y parroquia | Ids sinteticos `<provincia>\|<canton>[\|<parroquia>]` | Clave por nombre: hay dos parroquias `San Rafael` (Otavalo y Ruminahui) que se habrian fusionado |
| Procedencia | Nodo `Dataset` con fuente y SHA-256 | Sin nodo: los informes no podrian citar el archivo verificado |
| Full-text | Analizador `spanish` en `accident_narratives` y `report_texts` (titulo y texto) | `standard`: no reduce tildes ni plurales (`vehiculo` encuentra `vehículo` y `neblinas` encuentra `neblina`, comprobado) |
| Carga | Borrado y recarga completa en una transaccion, con `UNWIND` y conteo de nodos y relaciones creados por sentencia | `MERGE` incremental: mas complejo para 30 siniestros; un `MATCH` fallido no da error en Cypher y dejaria el grafo incompleto en silencio |
| Esquema | `IF NOT EXISTS` en transacciones propias | En la misma transaccion que los datos: Neo4j no lo permite |
| Valores de control | Exigidos solo si el SHA-256 es el del archivo conocido | Exigirlos siempre: una version nueva del JSON romperia la carga sin que haya error |
| Datos personales en el grafo | Verificacion por nombre de propiedad y por los patrones P6 (`domain/privacy.py`, compartido con la tarea 4.6) | Solo por nombre de propiedad: no detectaria una cedula dentro de un texto |
| Fechas hacia Neo4j | Desfase fijo `-05:00` en lugar de `ZoneInfo` | `ZoneInfo`: fallo de segmentacion en Python 3.12.15 (ver problemas) |
| Imagen | `python:3.12.15-slim-trixie` y uv 0.13.6, ambas con mas de dos semanas | 3.12.16 y uv 0.13.8 (publicadas hace 7 y 3 dias) |
| Contrasena de Neo4j | Obligatoria en `.env`; compose se detiene con un mensaje si falta | Valor por defecto en el repositorio: seria un secreto versionado |
| Servicio `api` | API minima con `GET /health` (Neo4j y LLM, sin claves) | Esperar a la tarea 4.9: el servicio del compose no tendria que arrancar |

## Cifras relevantes

| Indicador | Valor |
| --- | --- |
| Nodos / relaciones | 287 / 438 |
| Nodos por etiqueta | Accident 30, Person 80, Vehicle 49, Parish 30, Canton 22, Road 20, Province 17, Cause 10, VehicleType 10, ReportSection 9, AccidentType 5, Report 4, Dataset 1 |
| Restricciones / indices | 13 de unicidad; 6 de rango; 2 full-text |
| Valores de control | Todos coinciden (30 siniestros, 29 vigentes, 18 fallecidos, 44 heridos, 15 con fallecidos, 7 con moto, Pichincha y Guayas 5/5, E35 6 y 4 con fallecidos, 4 informes, 0 datos personales) |
| Tiempo de la carga | Unos 1.5 s (pipeline, escritura y verificacion) |
| Arranque completo | 12 s con cache de construccion; la primera construccion sin cache tardo unos 4 min |
| Pruebas | 515 unitarias (60 nuevas en la etapa: pipeline 18, privacidad 17, verificacion 10, writer 7, dominio 5, API 3) y 9 de integracion |

## Problemas encontrados y solucion

| Problema | Solucion |
| --- | --- |
| El loader terminaba con codigo 139 (fallo de segmentacion) solo en el contenedor | Con `python -X faulthandler` se ubico en `neo4j.time._utc_offset`: el driver pasa su propio tipo de fecha a `ZoneInfo.utcoffset`, y la implementacion en C de Python 3.12.15 no valida el tipo (la 3.12.16 local lanza `TypeError`, que el driver captura). Se envian las fechas con desfase fijo; se verifico en 3.12.15 antes de aplicar, y una prueba de regresion exige que ninguna fecha llegue con `ZoneInfo` |
| `uv_build>=0.13.8` en `pyproject.toml` obligaba a usar uv 0.13.8 (publicada hace 3 dias) | Requisito bajado a `>=0.13.6`, que la version local sigue cumpliendo |
| Se esperaban 29 parroquias y se crearon 30 | No era un error: hay dos `San Rafael` en cantones distintos. Se corrigio la cifra y se uso como justificacion del id compuesto |
| Dos pruebas asumian datos de SIN-2025-0001 copiados de un ejemplo (provincia y causa) | Se comprobaron en el JSON (Tungurahua, `invadir_carril`) antes de corregirlas |
| La consulta del subgrafo con `-[*1..3]-` arrastraba otros siniestros de la misma via | Se reemplazo por recorridos explicitos con `CALL (a) { ... UNION ... }` |
| `via` no encuentra `vía` en el full-text, aunque no es palabra vacia del analizador | Limitacion observada del stemmer con palabras cortas; otras palabras funcionan. Se revisara en la tarea 3.4 |
| `.env` no tenia `NEO4J_PASSWORD` | Se agrego una contrasena aleatoria local (sin mostrarla); `.env.example` explica que es obligatoria y como generarla |

## Archivos y modulos clave

- Codigo: `src/accident_agent/ingestion/pipeline.py`, `neo4j_writer.py`, `verification.py`, `__main__.py`; `src/accident_agent/graph/connection.py`; `src/accident_agent/domain/privacy.py`; `src/accident_agent/interfaces/api.py`. Cambios en `domain/models.py` (`DatasetInfo`, definiciones en `CleanDataset`) y `raw_models.py` (`to_json_value`).
- Infraestructura: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example`, `pyproject.toml` (`uv_build`, filtro de aviso de Starlette).
- Pruebas: `tests/unit/test_pipeline.py`, `test_neo4j_writer.py`, `test_verification.py`, `test_privacy.py`, `test_api_health.py`; `tests/integration/test_graph_load.py` y `example_queries.py`.
- Documentos: `docs/modelo_grafo.md`; `docs/datos/reglas_normalizacion.md` (correspondencia de `km` y rol).

## Evidencias guardadas

| Archivo | Contenido | Seccion de la guia tecnica |
| --- | --- | --- |
| `docs/evidencias/2.6_salida_loader.txt` | Salida del loader con los conteos de control y `GET /health` | 5.5 |
| `docs/evidencias/2.8_docker_compose_up.txt` | `docker compose up -d --build` desde cero y `docker compose ps -a` | 5.14 |
| `docs/evidencias/2.8_consultas_ejemplo.txt` | Resultados de las 8 consultas de ejemplo y muestra de SIN-2025-0001 frente al JSON | 5.6 |
| `docs/evidencias/2.8_subgrafo_neo4j_browser.png` | Captura de Neo4j Browser con el subgrafo de SIN-2025-0001 (tomada por el candidato y revisada) | 5.6 |

La etapa no produce evidencia `func_`.

## Secciones de los documentos finales que alimenta

- **Documento tecnico:** 5.5 Normalizacion y carga (material completo: reglas, pipeline, carga, idempotencia y verificacion); 5.6 Modelo de grafo (material completo); 5.13 Seguridad (patrones P6, verificacion de PII en el grafo, Cypher parametrizado); 5.14 Infraestructura (Dockerfile, compose, healthcheck, arranque); 5.15 Pruebas (integracion).
- **Documento funcional:** 4.3 Conceptos basicos (tipos de siniestro con su definicion en `AccidentType`, gravedad, anulados y reemplazos); 4.5 Puesta en marcha (comando unico y `NEO4J_PASSWORD`).
