# Etapa 3 - Notas de cierre

- **Fecha de cierre:** 2026-11-15.
- **Tareas:** 3.1 a 3.7. La subtarea `[O]` de 3.5 (parrafo de analisis con IA en el informe) no se implemento: el plan la deja desactivada por defecto y el informe se mantiene determinista.
- **DoD verificada:** los criterios de 7.2, 7.3 y 7.4 estan cubiertos por pruebas que pasan: 622 unitarias (107 nuevas) y 28 de integracion (19 nuevas). Ruff, mypy, `ascii_guard` y pre-commit sin errores. El compose reconstruido carga y verifica con los indices nuevos.

## Contratos finales

| Herramienta | Entrada | Salida | Errores |
| --- | --- | --- | --- |
| `get_current_time` | `timezone` IANA opcional (por defecto `DEFAULT_TIMEZONE`) | `iso_datetime`, `date`, `time`, `weekday` (espanol), `timezone`, `utc_offset`, `unix_timestamp` | Zona invalida: `validation`, sin repetir el valor |
| `search_accidents` | `mode` (`search`, `stats`, `reports`), `accident_ids` (max. 20), `province`, `canton`, `road`, `accident_type`, `cause`, `weather`, `surface`, `lighting`, `vehicle_type`, `date_from`, `date_to`, `only_fatal`, `text` (max. 200), `group_by`, `include_annulled`, `limit` (1 a 50) | `mode`, `total_found`, `accidents`, `stats`, `reports`, `applied_filters`, `warnings` | Entrada invalida: `validation` con sugerencias; base caida: `execution` o `timeout` con mensaje amigable |
| `generate_accident_report` | `accident_ids` (1 a 20), `title`, `include_narrative`, `save_file` | `report_id`, `title`, `generated_at`, `included_ids`, `not_found_ids`, `content_markdown`, `file_path`, `warnings` | Igual que la busqueda; error al guardar: advertencia, no fallo |

Envoltura comun (`core/tool.py`): `{"ok": true, "data": ...}` o `{"ok": false, "error": {"type", "message"}}`. El JSON Schema para el LLM sale del modelo de entrada, sin `$ref` ni `title`, con los enums visibles y `additionalProperties: false`.

## Plantillas Cypher

En `src/accident_agent/graph/queries.py`, todas constantes y de solo lectura:

- `SEARCH_IDS`: filtro comun con parametros opcionales `($p IS NULL OR ...)`; devuelve total e ids de la pagina, por relevancia si hay texto o por fecha descendente.
- `ACCIDENT_DETAILS`: detalle por ids con ubicacion, via, tipo, causa, reemplazos, vehiculos y personas (subconsultas `CALL (a)`).
- `STATS_QUERIES`: una consulta completa por agrupacion (7), fijada al importar.
- `FULLTEXT_ACCIDENTS`, `REPORTS_BY_TEXT`, `REPORTS_ALL` (vigentes primero) y `DATASET_INFO`.

## Decisiones y alternativas descartadas

| Area | Decision | Alternativas descartadas y motivo |
| --- | --- | --- |
| Cypher | Consultas estaticas con filtros opcionales `($p IS NULL OR ...)` | Componer fragmentos segun los filtros presentes: algo mas eficiente, pero mas dificil de auditar; con 30 siniestros la diferencia no importa |
| Full-text | Copias sin tildes (`narrative_search`, `title_search`, `text_search`) indexadas con el analizador `spanish`; la consulta se pliega igual | Texto original: el stemmer espanol solo quita tildes en palabras de 5 letras o mas (`via` no encontraba `vía`, comprobado); analizador `standard-folding`: pierde plurales |
| Texto libre | Se pliega y se escapan los operadores de Lucene | Pasarlo tal cual: un `:` o un `(` del usuario rompia la consulta o activaba operadores |
| DTOs | Listas blancas (`extra="ignore"`) | Mapear todas las propiedades del nodo: una propiedad inesperada saldria al LLM |
| Fake | `FakeAccidentRepository` con pruebas de contrato compartidas con Neo4j (14 x 2) | Mocks por prueba: no garantizan que el fake se comporte como la base |
| Entradas categoricas | Enums visibles en el esquema y validador que acepta las escrituras del catalogo, con sugerencias | Solo enums estrictos: el LLM fallaria con `Choque` o `VELOCIDAD EXCESIVA` |
| Via | Codigo (`E35`) por codigo; si no hay codigo, fragmento del nombre | Solo nombre exacto: `Panamericana` no encontraria nada |
| Anulados | Excluidos por defecto; incluidos si se piden por id, con su reemplazo | Excluirlos siempre: el escenario 12 no tendria respuesta |
| Ids explicitos | El limite sube para cubrirlos todos | Limite fijo: con 20 ids y `limit=10` la mitad se reportaba como inexistente |
| Advertencias | Explicitas: sin resultados, recorte, anulados, reemplazos, resumen inconsistente, fallecimiento diferido, ids inexistentes, filtros ignorados | Dejar que el LLM lo deduzca: riesgo de completar datos |
| Informe | Plantilla Jinja2 ASCII con `StrictUndefined`; hechos reconsultados por id; anulados sin sumar; fuente con SHA-256; id determinista | Texto generado por el LLM: no garantiza que los hechos salgan del grafo |
| Reintentos del driver | 3 s (antes 15 s) | Con 15 s, una herramienta con Neo4j caido superaba su timeout de 10 s; ahora falla en 3.1 s (medido) |
| Mensajes de error | Campo y motivo, sin repetir lo recibido | Mensajes de Pydantic completos: pueden incluir lo que escribio el usuario |

## Cifras relevantes

| Indicador | Valor |
| --- | --- |
| Escenarios del plan cubiertos con datos reales | 2, 3, 4, 5, 6, 8, 9, 10, 11 y 12 (fake y Neo4j) |
| Pruebas unitarias nuevas | 107: busqueda 38, informe 20, base de herramientas 15, contrato con el fake 14, hora 11, repositorio Neo4j 8, writer 1 |
| Pruebas de integracion nuevas | 19: contrato contra Neo4j 14, herramientas contra Neo4j 5 |
| Busqueda `via` en narrativas | 5 resultados (antes 0) |
| Falla con Neo4j caido | 3.1 s |
| Suite unitaria | 0.6 s |

## Problemas encontrados y solucion

| Problema | Solucion |
| --- | --- |
| `via` no encontraba `vía` en el full-text | Copias sin tildes indexadas; el writer recrea un indice cuyas propiedades cambiaron (`CREATE ... IF NOT EXISTS` no lo modifica). Verificado en local y en Docker |
| Los DTOs fallaban con campos nulos | Neo4j no guarda propiedades nulas y `{.*}` las omite: valores `None` por defecto en los campos opcionales |
| La suite unitaria paso de 0.5 s a 31 s | El driver reintentaba 30 s contra un servidor inexistente; revelo que el reintento de la aplicacion (15 s) superaba el timeout de la herramienta. Se bajo a 3 s |
| Mensajes con el valor recibido (`'Marte/Olimpo'`) y concordancia (`provincia no reconocido`) | Detectados al revisar la evidencia real; mensajes sin el valor y en forma neutra (`valor de provincia no reconocido`), con prueba |
| `trim_blocks` de Jinja2 quitaba lineas en blanco tras `{% endif %}` al final de linea | Lineas en blanco adicionales en la plantilla; revisado el informe renderizado |
| Una asercion con `and` aceptaba palabras de advertencias distintas | Cada asercion exige ambas partes en la misma advertencia |

## Archivos y modulos clave

- Codigo: `src/accident_agent/core/tool.py`, `core/clock.py`; `graph/repository.py`, `graph/queries.py`, `graph/neo4j_repository.py`; `tools/current_time.py`, `tools/accident_search.py`, `tools/accident_report.py`, `tools/templates/report.md.j2`. Cambios en `ingestion/neo4j_writer.py` (copias sin tildes, migracion de indices), `graph/connection.py` (reintentos) y `domain/catalogs.py` (`display_label`).
- Pruebas: `tests/fakes.py`; `tests/contract/test_repository_contract.py`; `tests/unit/test_tool_base.py`, `test_current_time.py`, `test_accident_search.py`, `test_accident_report.py`, `test_neo4j_repository.py`; `tests/integration/test_tools_neo4j.py`.
- Scripts y documentos: `scripts/export_catalog.py`; `docs/modelo_grafo.md` (copias sin tildes).

## Evidencias guardadas

| Archivo | Contenido | Seccion de la guia |
| --- | --- | --- |
| `docs/evidencias/3.7_ejemplos_herramientas.md` | Entradas y salidas reales de las 3 herramientas contra Neo4j (15 casos, incluidos errores) | Tecnica 5.9 |
| `docs/evidencias/3.7_informe_generado.md` | Informe completo del escenario 4 | Tecnica 5.9 y anexos |
| `docs/evidencias/func_3.7_catalogo_valores.md` | Catalogo de valores y escrituras aceptadas, exportado desde el codigo | Funcional 4.8 y anexos |

Las tres se revisaron contra la nomina completa: 0 nombres, cedulas o placas.

## Secciones de los documentos finales que alimenta

- **Documento tecnico:** 5.9 Herramientas y contratos (material completo); 5.10 Flujo RAG (parte de recuperacion: plantillas, full-text, filtros y advertencias; el ciclo con el LLM es la Etapa 4); 5.13 Seguridad (Cypher de solo lectura y parametrizado, escape de Lucene, DTOs en lista blanca, mensajes sin datos del usuario); 5.15 Pruebas (contrato fake y Neo4j).
- **Documento funcional:** 4.4 Capacidades del agente (que responde cada herramienta); 4.8 Como formular consultas (catalogo de valores); 4.10 Informes generados (ejemplo del escenario 4); 4.12 Comportamiento ante errores (sin resultados, id inexistente, valor no reconocido, base no disponible).
