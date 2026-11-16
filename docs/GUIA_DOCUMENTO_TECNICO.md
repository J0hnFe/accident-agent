# Guia del documento tecnico

- **Proyecto:** Prueba tecnica BIT - Orquestador multiagente con RAG sobre Neo4j.
- **Version de la guia:** 1.0 (2026-11-15).
- **Documento final que produce:** documento tecnico del desarrollo (entregable obligatorio).
- **Referencias:** `docs/PLAN_DESARROLLO.md`, `docs/enunciado/GUIA_PRUEBA_TECNICA.md`, `docs/GUIA_DOCUMENTO_FUNCIONAL.md`.

## Indice

1. Como usar esta guia
2. Datos del documento final
3. Reparto de contenido con los otros entregables
4. Tabla de avance
5. Estructura del documento final
6. Diagramas a incluir
7. Registro de evidencias por etapa
8. Preguntas que el documento debe responder
9. Lista de verificacion final

## 1. Como usar esta guia

- El documento tecnico explica **como se construyo la solucion y por que**. No es un manual de uso (eso va en el documento funcional) ni una guia de instalacion (eso va en el README).
- Se redacta de forma incremental: al cerrar cada etapa del plan se completan las secciones que dependen de ella (seccion 4).
- Cada etapa del plan tiene una tarea "Registro para los documentos" (instruccion en `CLAUDE.md`). Esa tarea guarda la evidencia de la seccion 7 y deja un resumen en `docs/evidencias/etapa-<N>_notas.md` con decisiones, cifras y problemas resueltos. Es la materia prima de este documento.
- Para cada seccion del documento final, la seccion 5 indica:
  - **Objetivo:** para que sirve la seccion.
  - **Contenido:** que debe incluir.
  - **Fuentes:** de donde sale la informacion (plan, tareas, archivos del repositorio).
  - **Evidencia:** que salida, captura o ejemplo real la respalda.
  - **Requisito:** que exigencia del enunciado cubre.
- Todo dato, cifra, captura o ejemplo debe salir de la ejecucion real del sistema o del repositorio. Nada se inventa ni se escribe de memoria.

## 2. Datos del documento final

| Aspecto | Definicion |
| --- | --- |
| Audiencia | Evaluador tecnico de BIT (ingeniero de software) |
| Proposito | Demostrar el diseno, las decisiones tomadas y el cumplimiento de los requisitos |
| Formato final | Word o PDF (decision pendiente, seccion 12 del plan) |
| Extension orientativa | 15 a 25 paginas sin anexos |
| Idioma | Espanol; los nombres de codigo se escriben en ingles, tal como aparecen en el repositorio |
| Ortografia | Espanol con ortografia completa: tildes, enie y signos de apertura. Esta guia, como el resto del repositorio, se mantiene en ASCII |
| Version descrita | Indicar el tag o commit del repositorio que describe el documento |

## 3. Reparto de contenido con los otros entregables

| Tema | README | Documento tecnico | Documento funcional |
| --- | --- | --- | --- |
| Instalacion y comando unico | Detalle paso a paso | Diseno de la infraestructura; remite al README | Resumen para el usuario |
| Analisis de datos y modelo de grafo | - | Completo | Solo los conceptos que necesita el usuario |
| Arquitectura, contratos y orquestador | - | Completo | - |
| Uso de la CLI y la API | Comandos basicos | - | Completo, con ejemplos |
| Pruebas | Como ejecutarlas | Estrategia, resultados y evidencia | - |
| Errores | Problemas de instalacion | Diseno del manejo de errores | Que ve el usuario y que hacer |

## 4. Tabla de avance

| # | Seccion del documento final | Se completa al cerrar | Estado |
| --- | --- | --- | --- |
| 1 | Portada y control del documento | Etapa 6 | [x] |
| 2 | Resumen ejecutivo | Etapa 6 | [x] |
| 3 | Alcance y cumplimiento de requisitos | Etapa 5 | [x] |
| 4 | Analisis de los datos | Etapa 1 | [x] |
| 5 | Normalizacion y carga | Etapa 2 | [x] |
| 6 | Modelo de grafo | Etapa 2 | [x] |
| 7 | Arquitectura de la solucion | Etapa 4 | [x] |
| 8 | Orquestador | Etapa 4 | [x] |
| 9 | Herramientas y contratos | Etapa 3 | [x] |
| 10 | Flujo RAG | Etapas 3 y 4 | [x] |
| 11 | Integracion con el proveedor de IA | Etapa 4 | [x] |
| 12 | Observabilidad | Etapa 4 | [x] |
| 13 | Seguridad y privacidad | Etapa 5 | [x] |
| 14 | Infraestructura y reproducibilidad | Etapas 2 y 5 | [x] |
| 15 | Pruebas | Etapa 5 | [x] |
| 16 | Limitaciones conocidas y trabajo futuro | Etapa 5 | [x] |
| 17 | Anexos | Etapa 6 | [x] |

**Ultima actualizacion:** cierre de la Etapa 5 (2026-11-15). `[x]` indica que el material de la seccion esta completo; la redaccion final es la tarea 6.2.

- **Etapa 0:** la evidencia (`docs/evidencias/0.*` y `etapa-0_notas.md`) alimenta las secciones 11 (proveedor de IA), 12 (Langfuse), 13 (pre-commit y gitleaks) y 14 (entorno, versiones y configuracion).
- **Etapa 1:** completa la seccion 4 (analisis de los datos: `docs/datos/`, `1.1_perfilado.json` y el reporte de calidad). Alimenta ademas la 5 (reglas y normalizadores; falta la carga de la Etapa 2), la 13 (politica de datos personales y prompt injection), la 15 (pruebas unitarias) y la 16 (riesgos residuales de privacidad). Resumen en `etapa-1_notas.md`.
- **Etapa 2:** completa la seccion 5 (normalizacion y carga: pipeline, carga atomica e idempotente, verificacion) y la 6 (modelo de grafo: `docs/modelo_grafo.md`, consultas de ejemplo y muestra frente al JSON). Alimenta ademas la 13 (verificacion de datos personales en el grafo, Cypher parametrizado), la 14 (Dockerfile, compose y arranque desde cero; se completa en la Etapa 5) y la 15 (pruebas de integracion). Resumen en `etapa-2_notas.md`.
- **Etapa 3:** completa la seccion 9 (herramientas y contratos: `3.7_ejemplos_herramientas.md`, `3.7_informe_generado.md`). Alimenta la 10 (parte de recuperacion del RAG; el ciclo con el LLM es la Etapa 4), la 13 (Cypher de solo lectura, escape de Lucene, DTOs en lista blanca) y la 15 (pruebas de contrato fake y Neo4j). Resumen en `etapa-3_notas.md`.
- **Etapa 4:** completa las secciones 7 (arquitectura), 8 (orquestador), 10 (flujo RAG) y 11 (proveedor de IA): transcripciones reales `4.11_transcripciones_*.json`, consumo y limites en `etapa-4_notas.md`. La 12 (observabilidad) tiene logs y verificacion de Langfuse (`4.11_logs_solicitud.jsonl`, `4.11_langfuse_verificacion.txt`); se marca con la captura de Langfuse. Alimenta tambien la 13 (delimitacion, redaccion, escenario 7 con el LLM real).
- **Etapa 5:** completa las secciones 13 (seguridad y privacidad: `5.4_busqueda_datos_personales.txt`, `5.4_cypher_solo_lectura.txt`, `5.6_gitleaks.txt`), 14 (arranque desde cero en un clon limpio: `5.5_arranque_desde_cero.txt`), 15 (pruebas: `5.9_pytest_cobertura.txt`, escenarios reales en `func_5.2_transcripciones_escenarios.json` y fallos en `func_5.3_mensajes_error.md`) y 16 (limitaciones y mejoras en `etapa-5_notas.md`). La 12 queda completa con la captura `4.11_langfuse_traza.png` de la etapa 4 y el arbol de las trazas de los escenarios 4 a 6 (`5.2_langfuse_escenarios_4_5_6.txt`); las capturas `[R]` de esos escenarios estan en `5.2_langfuse_escenario_4.png`, `_5.png` y `_6.png` (2026-11-16). La 3 (alcance) tiene los resultados, pero se marca al recorrer la lista de verificacion en la tarea 6.5. Resumen en `etapa-5_notas.md`.

## 5. Estructura del documento final

### 5.1 Portada y control del documento

- **Contenido:**
  - Titulo, autor, fecha y version del documento.
  - Enlace al repositorio y tag o commit descrito.
  - Tabla de versiones del documento e indice.

### 5.2 Resumen ejecutivo

- **Objetivo:** que el evaluador entienda la solucion en una pagina.
- **Contenido:**
  - El problema, en dos lineas.
  - La solucion, en cuatro o cinco lineas.
  - Decisiones clave: orquestador propio, plantillas Cypher, OpenRouter y minima exposicion de datos personales.
  - Resultados: pruebas que pasan y valores de control que coinciden.
  - Como probar la solucion con un comando.
- **Fuentes:** secciones 1 y 2 del plan.
- **Nota:** se escribe al final, cuando el resto del documento esta cerrado.

### 5.3 Alcance y cumplimiento de requisitos

- **Objetivo:** mostrar, requisito por requisito, como se cumple el enunciado.
- **Contenido:**
  - Objetivos del enunciado.
  - Tabla requisito, como se cumple y evidencia, adaptada de la matriz de trazabilidad.
  - Lo que queda fuera de alcance y por que.
- **Fuentes:** secciones 1 y 11 del plan; seccion 7 de `docs/enunciado/GUIA_PRUEBA_TECNICA.md`.
- **Evidencia:** la lista de verificacion de la guia completada.

### 5.4 Analisis de los datos

- **Objetivo:** demostrar que se entendio el JSON antes de modelarlo.
- **Contenido:**
  - Vision general:
    - metadata: fuente ficticia, zona horaria y formato de fechas;
    - 31 registros y 5 informes.
  - Diccionario de campos: campo, tipo esperado, tipos observados, ejemplo, significado y tratamiento.
  - Valores faltantes e inconsistentes, con cifras (p. ej. 4 formatos de fecha, 12 variantes de proteccion).
  - Casos especiales:
    - version duplicada;
    - registro anulado;
    - resumen inconsistente;
    - fallecido diferido;
    - peatones sin vehiculo.
  - Datos personales detectados y trampas:
    - el informe reservado INF-RES-01;
    - la prompt injection en la narrativa de SIN-2026-0009.
  - Papel de los informes embebidos:
    - INF-2026-02 como diccionario de datos y fuente de catalogos;
    - un informe reemplazado por otro.
- **Fuentes:** seccion 4 del plan; tareas 1.1 a 1.5; `docs/datos/analisis_datos.md` y `docs/datos/reporte_calidad_datos.md`.
- **Evidencia:** salida del perfilado y tabla de anomalias con su decision.
- **Requisito:** analizar y documentar estructura, campos, tipos y valores faltantes o inconsistentes.

### 5.5 Normalizacion y carga

- **Objetivo:** explicar como se limpian y cargan los datos sin alterar el original.
- **Contenido:**
  - El original no se modifica: SHA-256 antes y despues, y montaje de solo lectura.
  - Reglas de normalizacion con ejemplos reales de antes y despues, en una tabla.
  - Pipeline de ingesta, paso a paso:
    1. lectura;
    2. validacion permisiva;
    3. normalizacion;
    4. eliminacion de la version duplicada;
    5. tratamiento de anulados;
    6. control de consistencia;
    7. descarte de datos personales;
    8. escritura en Neo4j.
  - Idempotencia de la carga y verificacion posterior con los valores de control.
- **Fuentes:** tareas 1.4, 1.7, 2.2, 2.3 y 2.6; `docs/datos/reglas_normalizacion.md`; carpeta `ingestion/`.
- **Evidencia:** salida del loader con los conteos y resultado de las pruebas de los normalizadores.
- **Requisito:** toda limpieza o normalizacion se hace por codigo y se documenta.

### 5.6 Modelo de grafo

- **Objetivo:** justificar como se representan los datos en Neo4j.
- **Contenido:**
  - Diagrama del modelo.
  - Tabla de nodos: etiqueta, clave y propiedades.
  - Tabla de relaciones.
  - Justificacion campo por campo (nodo, relacion o propiedad) y criterio aplicado.
  - Restricciones e indices.
  - De 3 a 5 consultas Cypher de ejemplo con su resultado.
  - Alternativas descartadas, p. ej. condiciones como nodos o personas con identidad entre siniestros.
- **Fuentes:** seccion 6 del plan; tarea 2.1; `docs/modelo_grafo.md`.
- **Evidencia:** captura de Neo4j Browser con el subgrafo de un siniestro y resultados de las consultas.
- **Requisito:** definir el modelo y justificar que campos son nodos, relaciones o propiedades.

### 5.7 Arquitectura de la solucion

- **Objetivo:** mostrar el diseno propio, que es lo que se evalua.
- **Contenido:**
  - Estilo de puertos y adaptadores, y su motivo.
  - Diagrama de componentes.
  - Estructura de carpetas.
  - Aplicacion de SOLID, con un ejemplo de codigo real por principio.
  - La raiz de composicion, `bootstrap.py`.
  - Como agregar una herramienta nueva paso a paso, para demostrar el principio abierto/cerrado.
  - Decisiones y alternativas descartadas (LangGraph, Text2Cypher, embeddings, SDK del proveedor). Para cada una: contexto, decision y consecuencia.
- **Fuentes:** secciones 2 y 5 del plan; carpeta `core/`, `bootstrap.py` y la prueba OCP (tarea 4.10).
- **Requisito:** SOLID; frameworks detras de abstracciones propias.

### 5.8 Orquestador

- **Objetivo:** explicar como se interpreta la solicitud y como se controla la ejecucion.
- **Contenido:**
  - Diagrama de secuencia de una solicitud: usuario, interfaz, orquestador, LLM, herramienta, Neo4j y respuesta.
  - Como interpreta, selecciona y secuencia herramientas: function calling y llamadas en paralelo.
  - Limites (iteraciones, timeout por herramienta, timeout del LLM), con sus valores y el motivo de cada uno.
  - Manejo de errores: envoltura estructurada y `stop_reason`.
  - Memoria conversacional y como se resuelve "ese accidente".
  - Prompt de sistema: reglas y un extracto.
  - Guardia de grounding.
- **Fuentes:** seccion 7.5 del plan; tareas 4.2 a 4.5; `core/orchestrator.py` y `core/prompts.py`.
- **Evidencia:** transcripciones de los escenarios 4 (seguimiento) y 5 (hora y luego busqueda), con sus logs.
- **Requisito:** ejecucion controlada, contexto conversacional, y un orquestador que interpreta, selecciona, secuencia, ejecuta y compone.

### 5.9 Herramientas y contratos

- **Objetivo:** documentar el contrato de cada herramienta.
- **Contenido:**
  - Contrato base: puerto `Tool`, envoltura de resultados y JSON Schema generado.
  - Por cada herramienta:
    - proposito;
    - tabla de campos de entrada con sus validaciones;
    - salida;
    - errores posibles;
    - timeout;
    - un ejemplo real de llamada y respuesta (JSON recortado).
- **Fuentes:** secciones 7.1 a 7.4 del plan; tareas 3.1 a 3.5; carpeta `tools/`.
- **Requisito:** tres herramientas, cada una con un contrato de entrada y salida explicito y validado.

### 5.10 Flujo RAG

- **Objetivo:** demostrar que las respuestas se apoyan solo en el grafo.
- **Contenido:**
  - Por que plantillas parametrizadas y no Text2Cypher ni embeddings.
  - El recorrido completo:
    1. pregunta;
    2. filtros validados;
    3. normalizacion de valores;
    4. Cypher;
    5. hechos;
    6. respuesta que cita los ids.
  - Busqueda full-text sobre narrativas e informes.
  - La regla de "solo hechos del grafo" y como se verifica: prompt, guardia de ids e informes deterministas.
  - Narrativas tratadas como datos no confiables.
  - Informes vigentes frente a reemplazados, y anulados excluidos.
- **Fuentes:** seccion 7.3 del plan; tareas 3.4 y 4.5; `graph/queries.py`.
- **Evidencia:** escenarios 3, 7 (prompt injection), 8 y 10 (sin resultados).
- **Requisito:** RAG sobre el grafo como unica fuente de los hechos.

### 5.11 Integracion con el proveedor de IA

- **Objetivo:** justificar el proveedor y demostrar que se toleran sus limites.
- **Contenido:**
  - Por que OpenRouter, y los modelos principal y de respaldo con su motivo.
  - Limites del plan gratuito, verificados con fecha y fuente.
  - Como se toleran esos limites:
    - reintentos con backoff y respeto de `Retry-After`;
    - modelos de respaldo;
    - unas 2 llamadas por turno;
    - LLM simulado en las pruebas.
  - Puerto `LLMProvider` y como cambiar de proveedor sin tocar el nucleo.
  - Configuracion mediante variables de entorno.
- **Fuentes:** tareas 0.3 y 4.1; seccion 7.6 del plan; `providers/openrouter.py`; `docs/evidencias/`.
- **Requisito:** API key gratuita; verificar los limites del plan gratuito y tolerarlos.

### 5.12 Observabilidad

- **Objetivo:** mostrar como se entiende lo que paso en cada solicitud.
- **Contenido:**
  - Formato de los logs JSON y eventos `tool_call`, `llm_call` y `request`.
  - Ejemplo real con las lineas de log de una solicitud completa.
  - Redaccion de datos personales y claves.
  - `trace_id` para correlacionar eventos.
  - `[R]` Trazas en Langfuse: puerto `Tracer`, activacion por claves y capturas.
- **Fuentes:** secciones 7.8 y 7.9 del plan; tareas 4.6 y 4.6b; `logs/agent.jsonl`.
- **Requisito:** registros estructurados de herramienta, parametros, duracion y resultado.

### 5.13 Seguridad y privacidad

- **Objetivo:** demostrar la minima exposicion de datos personales y la gestion de secretos.
- **Contenido:**
  - Decisiones de minima exposicion:
    - nombre, cedula y placa no se cargan;
    - INF-RES-01 queda excluido;
    - se usan identificadores sinteticos.
  - Defensa ante prompt injection: datos delimitados, datos personales ausentes del grafo y prueba dedicada.
  - Cypher de solo lectura y parametrizado.
  - Gestion de secretos: `.env`, `.env.example`, gitleaks e historial limpio.
  - Datos enviados a terceros (OpenRouter y Langfuse) y su redaccion.
- **Fuentes:** tareas 1.5, 5.4 y 5.6.
- **Evidencia:** resultado de la busqueda por regex en salidas, informes y logs; escenario 7.
- **Requisito:** minima exposicion de datos personales; sin claves en el repositorio ni en su historial.

### 5.14 Infraestructura y reproducibilidad

- **Objetivo:** demostrar que cualquiera puede levantar el sistema desde cero.
- **Contenido:**
  - Servicios de Docker Compose y su orden: healthcheck, loader de una sola ejecucion, `api` y `cli`.
  - El comando unico y lo que ocurre al ejecutarlo.
  - Tabla de variables de entorno, sin valores secretos.
  - Gestion de dependencias: uv, versiones fijadas y `requirements.txt` exportado.
  - Prueba de arranque desde cero.
- **Fuentes:** tareas 0.4, 2.4, 2.5 y 5.5.
- **Evidencia:** salidas de `docker compose up -d --build` y `docker compose ps`, y tiempo de arranque.
- **Requisito:** un solo comando prepara la base y los datos; configuracion por entorno; dependencias fijadas.

### 5.15 Pruebas

- **Objetivo:** demostrar que la solucion funciona en casos normales y ante fallos.
- **Contenido:**
  - Estrategia:
    - unitarias;
    - de integracion con Neo4j;
    - de punta a punta con LLM simulado;
    - manuales con el LLM real.
  - Dobles de prueba (`FakeLLMProvider`, `FakeAccidentRepository`, `Clock` fijo) y por que se usan.
  - Tabla de escenarios (seccion 9 del plan) con su resultado.
  - Pruebas de fallos.
  - Cobertura.
  - Como ejecutarlas (remite al README).
- **Fuentes:** Etapa 5 del plan; carpeta `tests/`.
- **Evidencia:** salida de pytest con resumen y cobertura; transcripciones.
- **Requisito:** pruebas reproducibles; un fallo de herramienta no termina el sistema.

### 5.16 Limitaciones conocidas y trabajo futuro

- **Objetivo:** declarar con honestidad lo que la solucion no cubre.
- **Contenido:**
  - Limitaciones:
    - sesiones en memoria;
    - cuota diaria del LLM gratuito;
    - sin busqueda semantica;
    - API sin autenticacion;
    - datos solo hasta 2026-09-02;
    - coordenadas referenciales;
    - modelos gratuitos que pueden retirarse.
  - Mejoras propuestas:
    - persistencia de sesiones;
    - busqueda hibrida con embeddings;
    - autenticacion;
    - integracion continua;
    - mas herramientas;
    - un segundo proveedor.
- **Fuentes:** tarea 5.8; seccion 10 del plan.

### 5.17 Anexos

- Glosario tecnico.
- Diccionario de campos completo.
- Consultas Cypher.
- Ejemplo completo de un informe generado.
- Transcripcion completa de una conversacion.
- Salida completa de las pruebas.
- Registro de decisiones.

## 6. Diagramas a incluir

| Diagrama | Seccion | Contenido |
| --- | --- | --- |
| Componentes | 5.7 | Interfaces, orquestador, puertos, adaptadores y Neo4j |
| Secuencia de una solicitud | 5.8 | Flujo con dos herramientas encadenadas (escenario 6) |
| Modelo de grafo | 5.6 | Nodos y relaciones con sus propiedades clave |
| Pipeline de ingesta | 5.5 | Del JSON original al grafo |
| Despliegue | 5.14 | Servicios de Docker Compose y sus dependencias |

**Recomendacion:** escribir los diagramas en Mermaid dentro de `docs/diagramas/` (archivos `.mmd`) y exportarlos a PNG para el documento final. Asi quedan versionados y GitHub los muestra directamente.

## 7. Registro de evidencias por etapa

**Convencion de nombres:** `docs/evidencias/<tarea>_<descripcion>.<ext>`, p. ej. `0.3_limites_openrouter.md` o `2.6_salida_loader.txt`.

Ademas de estos archivos, cada etapa deja un resumen en `docs/evidencias/etapa-<N>_notas.md`, segun `CLAUDE.md`. Las decisiones y alternativas de ese resumen alimentan sobre todo las secciones 5.6, 5.7, 5.10 y 5.11.

| Etapa | Evidencia | Seccion que la usa |
| --- | --- | --- |
| 0 | Limites verificados de OpenRouter (y de Langfuse), con fecha y enlace a la fuente | 5.11 |
| 0 | Prueba de tool calling con el modelo elegido | 5.11 |
| 1 | Salida del perfilado del JSON | 5.4 |
| 1 | Reporte de calidad de datos generado | 5.4 |
| 1 | Resultado de las pruebas de normalizadores | 5.5 |
| 1 | SHA-256 del JSON original | 5.5 |
| 2 | Salida del loader con los conteos de control | 5.5 |
| 2 | Captura de Neo4j Browser con el subgrafo de un siniestro | 5.6 |
| 2 | Resultados de las consultas Cypher de ejemplo | 5.6 |
| 2 | Salidas de `docker compose up -d --build` y `docker compose ps` | 5.14 |
| 3 | Ejemplos reales de entrada y salida de cada herramienta | 5.9 |
| 3 | Ejemplo de informe generado | 5.9 y anexos |
| 4 | Transcripciones de los escenarios 4, 5 y 6 con su `trace_id` | 5.8 |
| 4 | Lineas de log de una solicitud completa | 5.12 |
| 4 | `[R]` Capturas de trazas en Langfuse | 5.12 |
| 5 | Salida de pytest con cobertura | 5.15 |
| 5 | Resultados de las pruebas de fallos | 5.8 y 5.15 |
| 5 | Busqueda de datos personales en salidas, informes y logs | 5.13 |
| 5 | Resultado de gitleaks o de la revision del historial | 5.13 |
| 5 | Arranque desde cero siguiendo el README | 5.14 |

## 8. Preguntas que el documento debe responder

El evaluador probablemente se hara estas preguntas. El documento debe responderlas de forma explicita:

- Por que el modelo de grafo tiene estos nodos y no otros?
- Como se garantiza que el agente no invente datos?
- Que pasa con el registro anulado, la version duplicada y el resumen inconsistente?
- Como se protegen los datos personales? Que ocurre con la instruccion maliciosa de SIN-2026-0009?
- Como se agrega una herramienta o un proveedor nuevo sin tocar el nucleo?
- Por que un orquestador propio y no LangGraph?
- Por que plantillas Cypher y no Text2Cypher o embeddings?
- Que ocurre si cae Neo4j, si el proveedor limita las solicitudes o si una herramienta tarda demasiado?
- Como se resuelve "genera el informe de ese accidente"?
- Como reproduce el evaluador todo desde cero?

## 9. Lista de verificacion final

- [x] Todas las secciones de la tabla de avance estan completas.
- [x] Cada requisito del enunciado tiene su evidencia (seccion 5.3).
- [x] Las cifras coinciden con los valores de control y con la ejecucion real.
- [x] Los fragmentos de codigo coinciden con el repositorio en el tag entregado.
- [x] Los diagramas son legibles y estan actualizados.
- [x] No hay claves, nombres ni cedulas en el documento ni en sus capturas.
- [x] Cada decision incluye las alternativas descartadas y su motivo.
- [x] Las limitaciones estan declaradas.
- [x] Todas las preguntas de la seccion 8 tienen respuesta.
- [x] No hay contradicciones con el README ni con el documento funcional.

## Avance de entrega (2026-11-16)

Version 1.1 en `docs/entrega/` (Markdown y PDF): URL publica, referencia de entrega (tag `entrega-1.0`), capturas de Langfuse de los escenarios 4 a 6 y respuesta explicita a los fallos de la seccion 8. Lista de verificacion de la seccion 9 recorrida en la tarea 6.5; resultado en `docs/evidencias/etapa-6_notas.md`. Envio pendiente (6.6).
