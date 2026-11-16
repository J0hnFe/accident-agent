# Etapa 5 - Notas de cierre

- **Fecha de cierre:** 2026-11-15.
- **Tareas:** 5.1 a 5.9. Queda pendiente la subtarea `[R]` de 5.2: capturas de pantalla de las trazas de los escenarios 4, 5 y 6 en Langfuse. Las trazas existen y su arbol esta en `5.2_langfuse_escenarios_4_5_6.txt`; la captura la toma el candidato desde el panel.
- **DoD verificada:** todas las verificaciones pasan y la evidencia esta guardada:
  - suite completa: 748 pruebas pasan y la e2e con el LLM real se omite de forma controlada por cuota agotada;
  - escenarios 1 a 17 automatizados y escenarios 1 a 13 con el LLM real;
  - fallos, privacidad, Cypher, reproducibilidad, secretos, ruff y mypy.

## Resultados

| Verificacion | Resultado | Evidencia |
| --- | --- | --- |
| Suite completa (5.1) | 749 pruebas: 719 por defecto (unitarias, contrato y escenarios con LLM simulado), 29 de integracion y 1 e2e. 748 pasan y la e2e se omite por la cuota diaria agotada (paso en la etapa 4). 11.8 s | `5.9_pytest_cobertura.txt` |
| Cobertura (5.1 `[R]`, meta 80%) | `core/` 99%, `tools/` 98%, total 97% | `5.9_pytest_cobertura.txt` |
| Escenarios 1 a 17 con LLM simulado (5.2) | 19 pruebas en `tests/e2e/test_scenarios.py`, en la suite por defecto | `5.9_pytest_cobertura.txt` |
| Escenarios 1 a 13 con LLM real (5.2) | Los 13 cumplen el resultado esperado. 1, 6 y 8 a 13 se ejecutaron en esta etapa; 2 a 5 y 7 vienen de la 4.11 (mismo orquestador y prompt). Latencia de 2.6 a 51.2 s | `func_5.2_transcripciones_escenarios.json` |
| Fallos (5.3) | Neo4j detenido, clave invalida, 429 real y simulado, timeout de herramienta, limite de iteraciones y entrada invalida: mensaje controlado y el proceso sigue activo | `func_5.3_mensajes_error.md` |
| Prompt injection (5.4) | Escenario 7 automatizado (dato dentro del delimitador, sin PII) y escape de la etiqueta de cierre (`test_orchestrator.py`). Con el LLM real, el agente nombro la instruccion inyectada y no la obedecio (4.11) | `func_5.2_transcripciones_escenarios.json` |
| Datos personales (5.4) | 0 coincidencias de la nomina (61 nombres, 80 cedulas, 49 placas) en 47 archivos y en 150 observaciones de Langfuse (36 trazas). Las 53 coincidencias de patrones genericos son falsos positivos (`SHA-256`, descripciones de formato, un `unix_timestamp`). Control positivo sobre el JSON original: 87 nombres, 87 cedulas, 126 placas. Sonda de punta a punta: la cedula y la placa del mensaje llegan como `[CEDULA]` y `[PLACA]` a los logs y a Langfuse | `5.4_busqueda_datos_personales.txt` |
| Cypher (5.4) | Las 13 plantillas son `LiteralString` y Neo4j las clasifica como lectura (`EXPLAIN`, `query_type=r`). Una escritura enviada por el repositorio falla con `Neo.ClientError.Statement.AccessMode` | `5.4_cypher_solo_lectura.txt` |
| Reproducibilidad (5.5) | Clon limpio, `docker compose down -v` y borrado de la imagen. `up -d --build` en 12 s, con todos los valores de control en `[ok]`. Respuesta real correcta (Pichincha: 5 siniestros, 4 fallecidos, 9 heridos, USD 68 300, verificado en el grafo) y 719 + 30 pruebas pasan desde el clon. Build sin cache: 5 s; uv descargo las 47 dependencias | `5.5_arranque_desde_cero.txt` |
| Secretos (5.6) | gitleaks: historial (8 commits) sin hallazgos. Arbol de trabajo: 3 hallazgos, todos en `.env`, que esta ignorado y nunca se commiteo. `.env.example` sin valores | `5.6_gitleaks.txt` |
| Calidad (5.7) | `ruff check`, `ruff format --check` y `mypy src tests scripts` (81 archivos) sin errores; pre-commit pasa | Commit de la etapa |
| Cuota del LLM | 23 solicitudes en la etapa (el contador diario, en UTC, paso de 28 a 51 de 50): 13 de los escenarios 1 y 8 a 13, 3 del escenario 6, 2 de Neo4j detenido, 2 del clon limpio y 3 del defecto de la CLI | `func_5.3_mensajes_error.md` (3.1) |

## Defectos encontrados y corregidos

| Defecto | Como se encontro | Correccion | Prueba |
| --- | --- | --- | --- |
| Con Neo4j detenido, `search_accidents` tardaba 7.5 s en fallar dentro de Docker; las notas de la etapa 3 decian 3.1 s | Prueba 5.3 con el LLM real. La medicion repetida dio 3.3 o 6.8 s segun el azar | `max_transaction_retry_time` paso de 3 a 2 s. El driver inicia otro reintento mientras no se haya superado ese tiempo y espera 1, 2 y 4 s con jitter: con 3 s a veces entraba un tercer reintento (peor caso unos 8.4 s, cerca del timeout de 10 s). Con 2 s el tercero nunca empieza: maximo 3.46 s en 8 llamadas | `test_configured_driver_fails_well_before_the_tool_timeout` (detecta el valor anterior en parte de las corridas, por el jitter) |
| `accident-agent ask ""` enviaba el mensaje vacio al LLM, que invento una pregunta ("ultimos 6 meses"), la respondio y gasto 3 solicitudes | Prueba 5.3 de entrada invalida; la API ya devolvia 422 | La CLI aplica las reglas de `POST /chat` (no vacio, hasta 2000 caracteres) antes de crear el contenedor. `MAX_MESSAGE_CHARS` vive en el nucleo y la usan ambas interfaces; `chat` avisa y sigue | 4 pruebas en `test_cli.py` |
| Con la cuota diaria agotada el mensaje decia "Intenta de nuevo en unos minutos", pero el contador se reinicia a las 00:00 UTC | 429 real de OpenRouter al final de la etapa | Texto: "alcanzo su limite de uso (por minuto o diario). Intenta de nuevo mas tarde." | Las pruebas usan la constante `MESSAGES` |
| `SafeTracer` solo tenia probado el fallo al iniciar la traza (`core/tracer.py` al 62%) | Informe de cobertura 5.1 | Sin cambios de codigo: 8 casos parametrizados (fallo en cada operacion: inicio, update y cierre de generation y span, cierre de traza) y uno de `flush`. Cobertura del modulo: 100% | `test_orchestrator.py` |

## Decisiones y alternativas descartadas

| Area | Decision | Alternativas descartadas y motivo |
| --- | --- | --- |
| Pruebas de fallos | Componentes reales con el fallo inyectado en un solo punto: `OpenRouterProvider` real con HTTP simulado (respx), Neo4j real con una demora, Neo4j detenido de verdad y clave invalida real | Solo pruebas unitarias con dobles: no muestran el mensaje que ve el usuario ni el tiempo real |
| Presupuesto de cuota | Escenarios con el LLM real solo donde faltaban (1, 6 y 8 a 13); 2 a 5 y 7 se reutilizan de la 4.11 | Repetir los 13: unas 30 solicitudes, mas que la cuota que quedaba |
| Cypher de solo lectura | `EXPLAIN` de cada plantilla (Neo4j informa `query_type`) mas el rechazo del servidor a escrituras en modo READ | Revisar las plantillas con expresiones regulares: no prueba lo que el servidor ejecutaria |
| Busqueda de datos personales | Valores exactos de la nomina, con control positivo, mas patrones genericos P6, sobre todas las salidas incluidas las trazas descargadas de Langfuse | Solo patrones: no distingue un `SHA-256` de una placa real. Solo la nomina: no cubre datos que escriba el usuario |
| Sonda de redaccion | Mensaje con cedula y placa de prueba por el orquestador real con Langfuse real y LLM guionizado | Usar el LLM real: gasta cuota y no aporta nada a la redaccion |
| Reproducibilidad | Clon limpio con `.env` nuevo (sin Langfuse, para probar tambien `NoopTracer`), `down -v` y borrado de la imagen. Ademas, build sin cache | Probar en el directorio de trabajo: arrastraria `.env`, caches y archivos sin versionar |

## Problemas encontrados y solucion

| Problema | Solucion |
| --- | --- |
| El README completo es de la tarea 6.1 | La prueba 5.5 siguio las instrucciones versionadas de `.env.example` y `docker-compose.yml`. Se repite con el README final en la tarea 6.5 |
| El proyecto compose tiene nombre fijo (`accident-agent`): el clon y el directorio de trabajo comparten contenedores y volumen | Se aprovecho para `down -v` real. Al terminar, el stack se recreo desde el directorio de trabajo (`--force-recreate`), con Langfuse otra vez |
| Los informes generados por la API se perdieron al recrear el contenedor (`reports/` sin volumen) | Para la evidencia, el informe del escenario 6 se copio con `docker cp` justo despues de generarlo. Queda como limitacion |
| Las trazas de Langfuse de los escenarios 4 y 5 son anteriores a la correccion de la latencia de las generations (etapa 4) | Repetirlos costaba unas 7 solicitudes y la cuota se agoto. El escenario 6 de esta etapa si mide cada llamada: 7.9 + 8.6 + 6.7 s, dentro de los 23.7 s de la solicitud |
| La cuota diaria se agoto antes de la corrida final: la e2e con el LLM real se omitio | La omision es controlada (`proveedor no disponible`). El 429 real se uso como evidencia del escenario 15 |
| Langfuse acepto una consulta con la clave publica enmascarada (el script de verificacion formateo un `SecretStr`) | La API publica autentica solo con la clave secreta. El script se corrigio; la aplicacion no usa esa API |

## Limitaciones conocidas (tarea 5.8)

Alimentan las secciones 5.16 del documento tecnico y 4.13 del funcional.

| Limitacion | Impacto | Mitigacion actual | Mejora propuesta |
| --- | --- | --- | --- |
| Sesiones en memoria del proceso | La conversacion y `last_accident_ids` se pierden al reiniciar; la API debe correr con un solo worker | Documentado; `DELETE /sessions/{id}` y `/reiniciar` | Persistencia (p. ej. Redis) detras del puerto `ConversationMemory` |
| Cuota del plan gratuito de OpenRouter: 50 solicitudes al dia y 20 por minuto | Con 2 o 3 llamadas por turno, unas 16 a 25 preguntas al dia | Pruebas sin cuota (LLM simulado); reintentos y respaldo; mensaje claro | Cuenta con creditos (1000 al dia) o un segundo proveedor |
| Un 429 diario se trata igual que uno por minuto | Con la cuota diaria agotada se prueban los 3 modelos (unos 3.4 s) aunque el limite es de la cuenta | Mensaje generico "por minuto o diario" | Leer `free-models-per-day` del cuerpo del 429 y cortar sin respaldos |
| Modelos gratuitos: pueden retirarse o cambiar, y su calidad y latencia varian | Respuestas de 2.6 a 51.2 s; la redaccion depende del modelo | Lista de respaldo configurable (`OPENROUTER_MODELS`); prompt con reglas; guardia de grounding | Evaluacion periodica con los escenarios reales; modelo de pago |
| Sin busqueda semantica | El full-text (Lucene sobre copias sin tildes) no entiende sinonimos ni parafrasis | Filtros estructurados con catalogos y sugerencias ante valores no reconocidos | Busqueda hibrida con embeddings en Neo4j |
| API sin autenticacion ni limite de solicitudes | Cualquiera con acceso al puerto puede consumir la cuota del LLM | Los puertos se publican solo en `127.0.0.1` | Clave de API o OAuth y limite por cliente |
| Informes y logs dentro del contenedor, sin volumen | Al recrear el contenedor `api` se pierden los informes (`GET /reports/{id}` deja de encontrarlos) y `logs/agent.jsonl`; los logs siguen en `docker compose logs` | Un informe se puede regenerar desde el grafo con los mismos ids | Volumenes para `reports/` y `logs/` |
| Datos ficticios y acotados | 29 siniestros vigentes, del 2025-01-12 al 2026-09-02; varias provincias (p. ej. Galapagos) sin registros | El agente dice que no hay datos y no inventa | - |
| Coordenadas referenciales (INF-2026-02) | No sirven para analisis espacial fino | Se muestran como referencia | - |
| Edad exacta y combinacion de atributos | En datos reales, edad, sexo, fecha y lugar podrian reidentificar a alguien | Sin nombres, cedulas ni placas; datos ficticios | Rangos de edad si los datos fueran reales |
| La respuesta del LLM no se redacta (solo logs y trazas) | Si el usuario escribe una cedula, el modelo podria repetirla en la respuesta a ese mismo usuario | El grafo no tiene datos personales; logs y Langfuse redactados | Redaccion opcional de la respuesta |
| La guardia de grounding advierte pero no bloquea | Una cifra inventada sin id no se detecta | Prompt con reglas; informes deterministas desde el grafo | Verificacion de cifras contra los resultados de las herramientas |
| Un hilo de herramienta que vence su timeout sigue corriendo | Ocupa un hilo hasta que vence el timeout nativo de Neo4j (10 s) | Timeouts nativos del driver y de httpx | - |
| Solo espanol | Preguntas en otro idioma dependen del modelo | Prompt en espanol | - |
| Langfuse Cloud es un tercero | Las trazas salen del equipo | Opcional; desactivado sin claves; redaccion previa | Autoalojar Langfuse si fuera necesario |
| Prueba e2e con el LLM real fuera de la suite por defecto | Depende de la cuota y de la disponibilidad del proveedor | `uv run pytest -m e2e` a mano; se omite de forma controlada si no hay cuota | Integracion continua con una cuota dedicada |

## Archivos y modulos clave modificados

- `src/accident_agent/graph/connection.py`: reintentos del driver.
- `src/accident_agent/interfaces/cli.py`: validacion del mensaje.
- `src/accident_agent/core/orchestrator.py`: `MAX_MESSAGE_CHARS` y texto del 429.
- `src/accident_agent/interfaces/api.py`: usa `MAX_MESSAGE_CHARS`.
- Pruebas:
  - `tests/unit/test_orchestrator.py`: fallos de `SafeTracer`.
  - `tests/unit/test_cli.py`: mensaje vacio y largo.
  - `tests/unit/test_neo4j_repository.py`: fallo rapido del driver.
  - `tests/integration/test_tools_neo4j.py`: `EXPLAIN` de las plantillas y codigo `AccessMode`.

## Evidencias guardadas

| Archivo | Contenido | Seccion de la guia |
| --- | --- | --- |
| `docs/evidencias/5.9_pytest_cobertura.txt` | Suite completa con cobertura por modulo y por paquete | Tecnica 5.15 |
| `docs/evidencias/func_5.2_transcripciones_escenarios.json` | Escenarios 1 a 13 con el LLM real, resultado esperado y origen | Funcional 4.9; tecnica 5.8 y 5.15 |
| `docs/evidencias/func_5.2_informe_escenario_6.md` | Informe completo generado por el agente en el escenario 6 | Funcional 4.10 y anexos |
| `docs/evidencias/5.2_langfuse_escenarios_4_5_6.txt` | Arbol de observaciones de las trazas de los escenarios 4, 5 y 6 | Tecnica 5.12 |
| `docs/evidencias/func_5.3_mensajes_error.md` | Mensajes reales de cada situacion de error, con las salidas completas | Funcional 4.12; tecnica 5.8 y 5.15 |
| `docs/evidencias/5.4_busqueda_datos_personales.txt` | Busqueda de la nomina y de patrones en salidas, informes, logs y Langfuse; sonda de redaccion | Tecnica 5.13 |
| `docs/evidencias/5.4_cypher_solo_lectura.txt` | Puntos de ejecucion, `EXPLAIN` de las 13 plantillas y pruebas dedicadas | Tecnica 5.13 |
| `docs/evidencias/5.5_arranque_desde_cero.txt` | Clon limpio, `down -v`, `up -d --build`, valores de control, consulta real y pruebas | Tecnica 5.14; funcional 4.5 |
| `docs/evidencias/5.6_gitleaks.txt` | gitleaks sobre el historial y el arbol de trabajo; `.env` nunca versionado | Tecnica 5.13 |

Todas revisadas contra la nomina completa: 0 coincidencias (ver `5.4_busqueda_datos_personales.txt`).

## Secciones de los documentos finales que alimenta

- **Documento tecnico:**
  - 5.3 Alcance: resultados para la matriz de trazabilidad; la lista de verificacion se recorre en 6.5.
  - 5.8 Orquestador: fallos y limites con mensajes reales.
  - 5.12 Observabilidad: trazas de los escenarios 4 a 6 y redaccion verificada en Langfuse.
  - 5.13 Seguridad y privacidad: busqueda de datos personales, Cypher de solo lectura, gitleaks y prompt injection.
  - 5.14 Infraestructura: arranque desde cero.
  - 5.15 Pruebas: suite, cobertura, escenarios y fallos.
  - 5.16 Limitaciones y trabajo futuro.
- **Documento funcional:**
  - 4.5 Puesta en marcha: pasos verificados; falta el README.
  - 4.9 Ejemplos de conversacion: escenarios 1 a 13.
  - 4.10 Informes: escenario 6.
  - 4.11 Privacidad.
  - 4.12 Errores: tabla con mensajes reales.
  - 4.13 Limitaciones para el usuario.
