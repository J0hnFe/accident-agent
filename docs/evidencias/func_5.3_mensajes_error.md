# 5.3 Mensajes reales ante errores y ausencia de datos

- **Fecha:** 2026-11-15 (America/Guayaquil).
- **Entorno:** servicio `api` de docker compose, Neo4j 5.26 cargado y LLM real de OpenRouter, salvo donde se indica. Las ejecuciones se hicieron durante la etapa, entre los commits `44c3eda` y `d036847`; los cambios entre ambos (reintentos del driver y validacion de la CLI) no tocan el orquestador, el prompt ni las herramientas, y cada caso afectado se indica abajo.
- **Uso:** alimenta la tabla de la seccion 4.12 del documento funcional y la 5.15 del tecnico.

Los mensajes del sistema (orquestador y herramientas) son fijos y van sin tildes porque el codigo es ASCII. Las respuestas redactadas por el LLM llevan tildes; se citan entre comillas invertidas.

## Resumen por situacion

| Situacion | Que ve el usuario (mensaje real) | Como se obtuvo |
| --- | --- | --- |
| No hay resultados | `No hay siniestros registrados en la provincia de **Galápagos** en la base de datos.` | Escenario 10, LLM real |
| Identificador inexistente | `El siniestro **SIN-9999-9999** no existe en la base de datos. Por eso no se pudo generar ningún informe.` | Escenario 11, LLM real; no se crea archivo de informe |
| Registro anulado | `El siniestro **SIN-2026-0010** está **ANULADO** y no cuenta en las estadísticas oficiales.` y `Lo reemplaza: SIN-2026-0011` | Escenario 12, LLM real |
| Pregunta fuera de alcance | `Lo siento, pero mi función es responder consultas sobre siniestros de tránsito en Ecuador. No puedo proporcionar recetas de cocina.` | Escenario 13, LLM real, sin herramientas |
| Pedido de datos personales | `No puedo proporcionar nombres ni números de cédula. El sistema no almacena esos datos personales por política de privacidad.` | Escenario 7, LLM real (tarea 4.11) |
| Valor no reconocido | La herramienta responde al LLM `valor de provincia no reconocido; quiza: Pichincha. Valores validos: ...` | Herramienta real con `province=Pichincah` |
| Base de datos no disponible | `La base de datos de siniestros no está disponible en este momento, por lo que no puedo consultar la cantidad de siniestros en Guayas. Por favor, inténtalo más tarde.` | `docker compose stop neo4j` y `POST /chat`, LLM real; `GET /health` responde `degraded` |
| Clave del proveedor invalida | `La clave del proveedor de inteligencia artificial falta o no es valida. Revisa OPENROUTER_API_KEY en el archivo .env.` | CLI real con una clave invalida (HTTP 401, sin probar los modelos de respaldo) |
| Limite del proveedor (429) | `El servicio de inteligencia artificial alcanzo su limite de uso (por minuto o diario). Intenta de nuevo mas tarde.` | 429 real de OpenRouter con la cuota diaria agotada (CLI) y 429 simulado con respx en los 3 modelos |
| Herramienta demasiado lenta | La herramienta responde al LLM `la herramienta search_accidents supero 1 s`; el ciclo continua y el LLM redacta la respuesta | Neo4j real con una demora inyectada de 3 s y timeout de 1 s |
| Limite de iteraciones | `No pude completar la respuesta dentro del limite de pasos permitido. Intenta dividir la pregunta en partes mas simples.` | LLM guionizado que pide herramientas sin parar |
| Mensaje invalido en la API | HTTP 422 `{"error": {"type": "validation", "message": "solicitud no valida", "details": [{"field": "message", "message": "String should have at least 1 character"}]}}` | `POST /chat` real con mensaje vacio, de 2001 caracteres, de otro tipo o JSON roto |
| Mensaje vacio en la CLI | `La pregunta esta vacia.` (codigo de salida 2, sin llamar al LLM) | CLI real; antes de la correccion de esta etapa el mensaje vacio llegaba al LLM |

En todos los casos el proceso sigue activo y la respuesta lleva `trace_id` para cruzarla con los logs.

## 1. Base de datos no disponible (escenario 14)

La medicion de la herramienta dentro de esta ejecucion (7543 ms) es anterior a la correccion de los reintentos del driver (ver `etapa-5_notas.md`); despues de corregirla, la misma herramienta falla en 3.46 s como maximo (seccion 1.1).

```text
$ docker compose stop neo4j
 Container accident-agent-neo4j-1 Stopping
 Container accident-agent-neo4j-1 Stopped

$ curl -s -w "\nHTTP %{http_code}\n" localhost:8000/health
{"status":"degraded","neo4j":"unavailable","llm_configured":true}
HTTP 200

$ curl -s -X POST localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Cuantos siniestros hubo en Guayas?"}'
{"session_id":"a8928c693ffc49a7b89436af5caa462f","answer":"La base de datos de siniestros no está disponible en este momento, por lo que no puedo consultar la cantidad de siniestros en Guayas. Por favor, inténtalo más tarde.","tools_used":[{"name":"search_accidents","params":{"mode":"stats","province":"Guayas","group_by":"province"},"duration_ms":7543,"status":"error","error_type":"execution"}],"trace_id":"d80f1a56f83943a8b07c9a9c303ebb9b","stop_reason":"final_answer"}
HTTP 200
(segundos: 15)

$ docker compose start neo4j  # y espera a que este healthy
 Container accident-agent-neo4j-1 Starting
 Container accident-agent-neo4j-1 Started
neo4j: healthy

$ curl -s -w "\nHTTP %{http_code}\n" localhost:8000/health
{"status":"ok","neo4j":"ok","llm_configured":true}
HTTP 200
```

### 1.1 Tiempo de fallo de la herramienta tras la correccion

Ocho llamadas a `search_accidents` dentro del contenedor `api`, con Neo4j detenido y sin LLM:

```text
segundos por llamada: [2.5, 2.85, 3.46, 2.72, 3.12, 2.98, 2.79, 2.82]
maximo: 3.46
resultado: {'ok': False, 'error': {'type': 'execution', 'message': 'La base de datos de siniestros no esta disponible en este momento.'}}
```

## 2. Clave del proveedor invalida (escenario 15)

```text
$ OPENROUTER_API_KEY=clave-invalida uv run accident-agent ask "Cuantos siniestros hubo en Guayas?" --verbose
La clave del proveedor de inteligencia artificial falta o no es valida. Revisa OPENROUTER_API_KEY en el
archivo .env.
trace_id=75af458e8f7e4b77aab7b4a279418314 iteraciones=1 stop_reason=llm_error
(codigo de salida: 1, segundos: 1)
```

Evento `llm_call` de esa solicitud en `logs/agent.jsonl`: `status=error`, `error_type=AuthenticationError`, `duration_ms=91`.

## 3. Fallos simulados con componentes reales (escenarios 15, 16 y 17)

Neo4j, herramientas, orquestador y `OpenRouterProvider` reales; solo se inyecta el fallo (respuestas HTTP de OpenRouter con respx, demora en el repositorio o LLM guionizado). Con 429 en el modelo principal, el proveedor reintenta una vez y pasa al siguiente modelo de la lista.

```text

=== 429 en el modelo principal
{
 "answer": "Respuesta del modelo de respaldo.",
 "tools_used": [],
 "trace_id": "743d1da971f24026b52d68eb65f01c0b",
 "iterations": 1,
 "stop_reason": "final_answer"
}
--- eventos de log
{"level": "info", "event": "llm_call", "trace_id": "743d1da971f24026b52d68eb65f01c0b", "session_id": "demo", "iteration": 1, "status": "ok", "model": "nvidia/nemotron-3.5-super-vl:free", "duration_ms": 1014, "tokens": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}, "retries": 2, "tool_calls": []}
{"level": "info", "event": "request", "trace_id": "743d1da971f24026b52d68eb65f01c0b", "session_id": "demo", "iterations": 1, "stop_reason": "final_answer", "tools": [], "duration_ms": 1015}
--- peticiones HTTP por modelo, en orden: ['nvidia/nemotron-3-ultra-550b-a55b:free', 'nvidia/nemotron-3-ultra-550b-a55b:free', 'nvidia/nemotron-3.5-super-vl:free']
--- segundos: 1.0

=== 429 en todos los modelos
{
 "answer": "El servicio de inteligencia artificial alcanzo su limite de uso (por minuto o diario). Intenta de nuevo mas tarde.",
 "tools_used": [],
 "trace_id": "8a12cc619973490c8f00d452a8be79a7",
 "iterations": 1,
 "stop_reason": "llm_error"
}
--- eventos de log
{"level": "warning", "event": "llm_call", "trace_id": "8a12cc619973490c8f00d452a8be79a7", "session_id": "demo", "iteration": 1, "status": "error", "error_type": "RateLimitError", "duration_ms": 3028}
{"level": "info", "event": "request", "trace_id": "8a12cc619973490c8f00d452a8be79a7", "session_id": "demo", "iterations": 1, "stop_reason": "llm_error", "tools": [], "duration_ms": 3031}
--- peticiones HTTP por modelo, en orden: ['nvidia/nemotron-3-ultra-550b-a55b:free', 'nvidia/nemotron-3-ultra-550b-a55b:free', 'nvidia/nemotron-3.5-super-vl:free', 'nvidia/nemotron-3.5-super-vl:free', 'google/gemma-4-31b-it:free', 'google/gemma-4-31b-it:free']
--- segundos: 3.0

=== Timeout de herramienta (busqueda de 3 s, limite 1 s)
{
 "answer": "La consulta tardo demasiado; intenta de nuevo.",
 "tools_used": [
  {
   "name": "search_accidents",
   "params": {
    "province": "Guayas"
   },
   "duration_ms": 1006,
   "status": "timeout",
   "error_type": "timeout"
  }
 ],
 "trace_id": "7c040f0b7b0944df8597695d5b039e88",
 "iterations": 2,
 "stop_reason": "final_answer"
}
--- eventos de log
{"level": "info", "event": "tool_call", "trace_id": "7c040f0b7b0944df8597695d5b039e88", "session_id": "demo", "iteration": 1, "tool": "search_accidents", "params": {"province": "Guayas"}, "duration_ms": 1006, "status": "timeout", "result_summary": {}, "error_type": "timeout"}
--- resultado que recibe el LLM: {"ok": false, "error": {"type": "timeout", "message": "la herramienta search_accidents supero 1 s"}}

=== Limite de iteraciones (el LLM pide herramientas sin parar)
{
 "answer": "No pude completar la respuesta dentro del limite de pasos permitido. Intenta dividir la pregunta en partes mas simples.",
 "tools_used": [
  {
   "name": "get_current_time",
   "params": {},
   "duration_ms": 0,
   "status": "ok",
   "error_type": null
  },
  {
   "name": "get_current_time",
   "params": {},
   "duration_ms": 0,
   "status": "ok",
   "error_type": null
  },
  {
   "name": "get_current_time",
   "params": {},
   "duration_ms": 0,
   "status": "ok",
   "error_type": null
  },
  {
   "name": "get_current_time",
   "params": {},
   "duration_ms": 0,
   "status": "ok",
   "error_type": null
  },
  {
   "name": "get_current_time",
   "params": {},
   "duration_ms": 0,
   "status": "ok",
   "error_type": null
  }
 ],
 "trace_id": "98d46cea37fa47d1846e185f73db358b",
 "iterations": 5,
 "stop_reason": "max_iterations"
}
--- eventos de log
{"level": "info", "event": "request", "trace_id": "98d46cea37fa47d1846e185f73db358b", "session_id": "demo", "iterations": 5, "stop_reason": "max_iterations", "tools": ["get_current_time", "get_current_time", "get_current_time", "get_current_time", "get_current_time"], "duration_ms": 8}

=== Entrada invalida enviada por el LLM a las herramientas (envoltura de error)
{"tool": "search_accidents", "arguments": {"date_from": "2026-06-01", "date_to": "2026-01-01"}, "result": {"ok": false, "error": {"type": "validation", "message": "argumentos: Value error, date_from no puede ser posterior a date_to"}}}
{"tool": "search_accidents", "arguments": {"accident_type": "explosion"}, "result": {"ok": false, "error": {"type": "validation", "message": "accident_type: Value error, valor de tipo no reconocido. Valores validos: atropello, choque, estrellamiento, perdida_de_pista, volcamiento"}}}
{"tool": "search_accidents", "arguments": {"mode": "stats"}, "result": {"ok": false, "error": {"type": "validation", "message": "argumentos: Value error, group_by es obligatorio cuando mode=stats"}}}
{"tool": "search_accidents", "arguments": {"limit": 500}, "result": {"ok": false, "error": {"type": "validation", "message": "limit: Input should be less than or equal to 50"}}}
{"tool": "generate_accident_report", "arguments": {"accident_ids": ["SIN-26-1"]}, "result": {"ok": false, "error": {"type": "validation", "message": "accident_ids.0: String should match pattern '^SIN-\\d{4}-\\d{4}$'"}}}
{"tool": "generate_accident_report", "arguments": {"accident_ids": []}, "result": {"ok": false, "error": {"type": "validation", "message": "accident_ids: List should have at least 1 item after validation, not 0"}}}
{"tool": "get_current_time", "arguments": {"timezone": "Marte/Olympus"}, "result": {"ok": false, "error": {"type": "validation", "message": "timezone: Value error, zona horaria IANA no valida (p. ej. America/Guayaquil)"}}}
{"tool": "search_accidents", "arguments": "{no es json", "result": {"ok": false, "error": {"type": "validation", "message": "los argumentos no son JSON valido"}}}
```

## 3.1 Limite real del proveedor (429 de OpenRouter)

Al final de la etapa se agoto la cuota diaria del plan gratuito (`used 51` de 50, contador UTC). La prueba `-m e2e` con el LLM real se omitio de forma controlada (`proveedor no disponible`) y la CLI mostro el mensaje del sistema. El texto del mensaje se ajusto en esta etapa: antes decia "Intenta de nuevo en unos minutos", que no sirve cuando se agoto el limite diario.

```text
$ uv run accident-agent ask "Que hora es?" --verbose   # cuota diaria del plan gratuito agotada (used 51 de 50)
El servicio de inteligencia artificial alcanzo su limite de uso (por minuto o diario). Intenta de nuevo mas
tarde.
trace_id=ea30b4c7e6a042e3a255502bfaf0a787 iteraciones=1 stop_reason=llm_error
(codigo de salida: 1, segundos: 4)

$ tail -2 logs/agent.jsonl
{"trace_id": "ea30b4c7e6a042e3a255502bfaf0a787", "session_id": "2adf57dbc34044159ff89f9c8f7bbdb1", "iteration": 1, "status": "error", "error_type": "RateLimitError", "duration_ms": 3333, "event": "llm_call", "level": "warning", "timestamp": "2026-11-16T04:01:36.688907Z"}
{"trace_id": "ea30b4c7e6a042e3a255502bfaf0a787", "session_id": "2adf57dbc34044159ff89f9c8f7bbdb1", "iterations": 1, "stop_reason": "llm_error", "tools": [], "duration_ms": 3338, "event": "request", "level": "info", "timestamp": "2026-11-16T04:01:36.691931Z"}
```

Peticiones HTTP del `OpenRouterProvider` real en esa situacion, registradas con un event hook de httpx (segundos desde el inicio, modelo, estado, `Retry-After`, `X-RateLimit-Remaining` y el inicio del mensaje de error):

```text
(0.15, 'nvidia/nemotron-3-ultra-550b-a55b:free', 429, None, '0', 'Rate limit exceeded: free-models-per-day. Add 10 credits to ')
(1.2, 'nvidia/nemotron-3-ultra-550b-a55b:free', 429, None, '0', 'Rate limit exceeded: free-models-per-day. Add 10 credits to ')
(1.24, 'nvidia/nemotron-3.5-super-vl:free', 429, None, '0', 'Rate limit exceeded: free-models-per-day. Add 10 credits to ')
(2.27, 'nvidia/nemotron-3.5-super-vl:free', 429, None, '0', 'Rate limit exceeded: free-models-per-day. Add 10 credits to ')
(2.34, 'google/gemma-4-31b-it:free', 429, None, '0', 'Rate limit exceeded: free-models-per-day. Add 10 credits to ')
(3.38, 'google/gemma-4-31b-it:free', 429, None, '0', 'Rate limit exceeded: free-models-per-day. Add 10 credits to ')
error: RateLimitError
```

Cada modelo recibe un reintento con 1 s de espera y luego se pasa al siguiente; en total 3.4 s. Con la cuota diaria agotada los respaldos no ayudan (el limite es de la cuenta); OpenRouter lo indica en el mensaje (`free-models-per-day`), lo que permitiria cortar antes (ver limitaciones en `etapa-5_notas.md`).

## 4. Entrada invalida en la API y en la CLI

```text
$ curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{}'
{"error":{"type":"validation","message":"solicitud no valida","details":[{"field":"message","message":"Field required"}]}}
HTTP 422

$ curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"message": ""}'
{"error":{"type":"validation","message":"solicitud no valida","details":[{"field":"message","message":"String should have at least 1 character"}]}}
HTTP 422

$ curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"message": "aaa...a" (2001 caracteres)}'
{"error":{"type":"validation","message":"solicitud no valida","details":[{"field":"message","message":"String should have at most 2000 characters"}]}}
HTTP 422

$ curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"message": 123}'
{"error":{"type":"validation","message":"solicitud no valida","details":[{"field":"message","message":"Input should be a valid string"}]}}
HTTP 422

$ curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"message": "hola"'
{"error":{"type":"validation","message":"solicitud no valida","details":[{"field":"18","message":"JSON decode error"}]}}
HTTP 422

$ curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' -d '{"session_id": "x y/../z", "message": "hola"}'
{"error":{"type":"validation","message":"solicitud no valida","details":[{"field":"session_id","message":"String should match pattern '^[A-Za-z0-9_-]{1,64}$'"}]}}
HTTP 422

$ curl -s localhost:8000/reports/..%2F..%2Fetc%2Fpasswd
{"error":{"type":"not_found","message":"recurso no encontrado"}}
HTTP 404

$ curl -s localhost:8000/reports/RPT-NOEXISTE
{"error":{"type":"not_found","message":"informe no encontrado"}}
HTTP 404

$ uv run accident-agent ask ""
La pregunta esta vacia.
(codigo de salida: 2)

$ uv run accident-agent ask "   "
La pregunta esta vacia.
(codigo de salida: 2)
```

## 5. Valores no reconocidos y sin resultados (herramienta real)

```text
{"arguments": {"province": "Pichincah"}, "result": {"ok": false, "error": {"type": "validation", "message": "province: Value error, valor de provincia no reconocido; quiza: Pichincha. Valores validos: Azuay, Bolivar, Canar, Carchi, Chimborazo, Cotopaxi, El Oro, Esmeraldas, Galapagos, Guayas, Imbabura, Loja, Los Rios, Manabi, Morona Santiago, Napo, Orellana, Pastaza, Pichincha, Santa Elena, Santo Domingo de los Tsachilas, Sucumbios, Tungurahua, Zamora Chinchipe"}}}
{"arguments": {"province": "Galapagos"}, "result": {"ok": true, "data": {"total_found": 0, "applied_filters": {"mode": "search", "limit": 10, "province": "Galapagos"}, "warnings": ["No hay siniestros que cumplan los filtros aplicados; no completes con otros datos."]}}}
{"arguments": {"road": "E99"}, "result": {"ok": true, "data": {"total_found": 0, "applied_filters": {"mode": "search", "limit": 10, "road_code": "E99"}, "warnings": ["No hay siniestros que cumplan los filtros aplicados; no completes con otros datos."]}}}
{"arguments": {"vehicle_type": "monopatin"}, "result": {"ok": false, "error": {"type": "validation", "message": "vehicle_type: Value error, valor de tipo de vehiculo no reconocido. Valores validos: automovil, bus, camion, camion_liviano, camion_pesado, camioneta, motocicleta, suv, taxi, trailer"}}}
```
