# Guia del documento funcional

- **Proyecto:** Prueba tecnica BIT - Orquestador multiagente con RAG sobre Neo4j.
- **Version de la guia:** 1.0 (2026-11-15).
- **Documento final que produce:** documento funcional del desarrollo (entregable obligatorio).
- **Referencias:** `docs/PLAN_DESARROLLO.md`, `docs/enunciado/GUIA_PRUEBA_TECNICA.md`, `docs/GUIA_DOCUMENTO_TECNICO.md`.

## Indice

1. Como usar esta guia
2. Datos del documento final
3. Tabla de avance
4. Estructura del documento final
5. Capturas y evidencias a recolectar
6. Recomendaciones de redaccion
7. Lista de verificacion final

## 1. Como usar esta guia

- El documento funcional explica **que hace el agente y como se usa**, desde el punto de vista de quien lo utiliza. No explica como esta construido (documento tecnico) ni la instalacion detallada (README).
- Se completa sobre todo en las Etapas 4 y 5, cuando el sistema ya funciona de punta a punta.
- Cada etapa del plan tiene una tarea "Registro para los documentos" (instruccion en `CLAUDE.md`). La evidencia del documento funcional se guarda con el prefijo `func_` (seccion 5), y el resumen de cada etapa queda en `docs/evidencias/etapa-<N>_notas.md`.
- Para cada seccion del documento final, la seccion 4 indica objetivo, contenido, fuentes y evidencia.
- Todos los ejemplos, mensajes y capturas se copian de ejecuciones reales guardadas en `docs/evidencias/`. Ningun ejemplo se redacta de memoria.

## 2. Datos del documento final

| Aspecto | Definicion |
| --- | --- |
| Audiencia | Evaluador de BIT y cualquier persona que consulte siniestros (analista o usuario no tecnico) |
| Proposito | Explicar capacidades, uso, ejemplos, informes y comportamiento ante errores |
| Formato final | Word o PDF (decision pendiente, seccion 12 del plan) |
| Extension orientativa | 10 a 15 paginas sin anexos |
| Tono | Lenguaje sencillo, frases cortas y sin jerga. Si un termino tecnico es inevitable, se explica |
| Ortografia | Espanol con ortografia completa: tildes, enie y signos de apertura. Esta guia, como el resto del repositorio, se mantiene en ASCII |
| Version descrita | Indicar el tag o commit del repositorio que describe el documento |

## 3. Tabla de avance

| # | Seccion del documento final | Se completa al cerrar | Estado |
| --- | --- | --- | --- |
| 1 | Portada y control del documento | Etapa 6 | [x] |
| 2 | Introduccion | Etapa 4 | [x] |
| 3 | Conceptos basicos | Etapa 2 | [x] |
| 4 | Capacidades del agente | Etapa 4 | [x] |
| 5 | Puesta en marcha (resumen) | Etapa 5 | [x] |
| 6 | Uso desde la linea de comandos | Etapa 4 | [x] |
| 7 | Uso desde la API REST | Etapa 4 | [x] |
| 8 | Como formular consultas | Etapa 4 | [x] |
| 9 | Ejemplos de conversacion | Etapa 5 | [x] |
| 10 | Informes generados | Etapa 5 | [x] |
| 11 | Privacidad y tratamiento de datos | Etapa 5 | [x] |
| 12 | Comportamiento ante errores y ausencia de datos | Etapa 5 | [x] |
| 13 | Limitaciones para el usuario | Etapa 5 | [x] |
| 14 | Preguntas frecuentes | Etapa 6 | [x] |
| 15 | Anexos | Etapa 6 | [x] |

**Ultima actualizacion:** cierre de la Etapa 5 (2026-11-15). `[x]` indica que el material de la seccion esta completo; la redaccion final es la tarea 6.3.

- **Etapa 0:** no produce evidencia `func_`; solo prepara el entorno.
- **Etapa 1:** no produce evidencia `func_`. Sus documentos alimentan la seccion 3 (conceptos basicos: tipos de siniestro y gravedad de INF-2026-02, en `docs/datos/catalogo_anomalias.md`), la 11 (privacidad: `docs/datos/politica_datos_personales.md`) y la 13 (limitaciones: riesgos residuales de privacidad).
- **Etapa 2:** no produce evidencia `func_`. Completa la seccion 3 (conceptos basicos: tipos de siniestro con su definicion de INF-2026-02 en el grafo, gravedad, registros anulados e informes reemplazados; ver `docs/modelo_grafo.md`) y alimenta la 5 (puesta en marcha: comando unico y `NEO4J_PASSWORD` obligatoria).
- **Etapa 3:** produce `func_3.7_catalogo_valores.md` (seccion 8 y anexos). Alimenta la 4 (capacidades de cada herramienta), la 10 (ejemplo de informe en `3.7_informe_generado.md`) y la 12 (sin resultados, id inexistente, valor no reconocido con sugerencias, base no disponible). Ninguna seccion se completa: dependen del agente de punta a punta (Etapas 4 y 5).
- **Etapa 4:** produce `func_4.11_api_chat.json` (POST /chat con seguimiento) y `func_4.11_cli_verbose.txt`. Completa las secciones 2 (introduccion), 4 (capacidades) y 8 (como formular consultas, con ejemplos reales). Las 6 (CLI) y 7 (API) se marcan con las capturas de la CLI y de Swagger.
- **Etapa 5:** produce `func_5.2_transcripciones_escenarios.json` (escenarios 1 a 13 con el LLM real), `func_5.2_informe_escenario_6.md` (informe completo) y `func_5.3_mensajes_error.md` (mensajes reales de cada situacion de error). Completa las secciones 9 (ejemplos), 10 (informes), 11 (privacidad: `5.4_busqueda_datos_personales.txt` y escenario 7), 12 (errores) y 13 (limitaciones, en `etapa-5_notas.md`). Las 6 (CLI) y 7 (API) quedan completas con las capturas `func_4.11_cli_verbose.png` y `func_4.11_swagger.png` de la etapa 4. La 5 (puesta en marcha) tiene los pasos verificados en `5.5_arranque_desde_cero.txt`, pero depende del README (tarea 6.1).

## 4. Estructura del documento final

### 4.1 Portada y control del documento

- **Contenido:**
  - Titulo, autor, fecha y version del documento.
  - Enlace al repositorio y tag o commit descrito.
  - Tabla de versiones del documento e indice.

### 4.2 Introduccion

- **Objetivo:** que el lector sepa en un minuto que es el agente y para que le sirve.
- **Contenido:**
  - Que es el agente y que problema resuelve.
  - A quien va dirigido.
  - Resumen de lo que puede y no puede hacer.
  - De donde salen los datos: un extracto ficticio de partes de transito (ANT / ECU 911). Contiene 29 siniestros vigentes entre el 2025-01-12 y el 2026-09-02, en 17 provincias.
- **Fuentes:** seccion 1 del plan; metadata del JSON; valores de control de la Etapa 2.

### 4.3 Conceptos basicos

- **Objetivo:** explicar los terminos que el usuario vera en las respuestas.
- **Contenido:**
  - **Siniestro y parte:** que es cada uno y el formato de su identificador (`SIN-AAAA-NNNN`).
  - **Tipos de siniestro y niveles de gravedad:** segun el diccionario de datos INF-2026-02 (choque, estrellamiento, atropello, volcamiento, perdida de pista; fallecido, herido grave, herido leve, ileso).
  - **Registro vigente y registro anulado:** que significa cada uno y por que un anulado no se cuenta.
  - **Informes del sistema e informes generados:** los primeros vienen en los datos (vigentes o reemplazados); los segundos los crea el agente a pedido.
  - **Sesion de conversacion:** que recuerda el agente dentro de una sesion.
- **Fuentes:** seccion 4 del plan; informe INF-2026-02.

### 4.4 Capacidades del agente

- **Objetivo:** mostrar todo lo que se puede pedir, con un ejemplo por capacidad.
- **Contenido:** tabla de capacidades, como la siguiente. La columna de ejemplos se valida con ejecuciones reales.

| Capacidad | Que permite | Ejemplo de pregunta |
| --- | --- | --- |
| Buscar siniestros | Filtrar por provincia, canton, via, fechas, tipo, causa, clima, superficie, iluminacion, tipo de vehiculo, gravedad o identificador | "Que siniestros con fallecidos hubo en la E35?" |
| Estadisticas | Obtener conteos y totales agrupados por provincia, causa, tipo, mes, anio, clima o tipo de vehiculo | "Cuantos siniestros hubo por provincia?" |
| Informes y definiciones | Buscar en los informes vigentes del sistema | "Que es un estrellamiento?" |
| Hora actual | Consultar la hora de Ecuador o de otra zona horaria | "Que hora es?" |
| Fechas relativas | Combinar la hora actual con una busqueda | "Que accidentes hubo en los ultimos 6 meses?" |
| Generar informes | Crear un informe en Markdown de uno o varios siniestros | "Haz un informe de los siniestros con motocicletas" |
| Seguimiento | Usar los ultimos siniestros consultados en la sesion | "Genera el informe de ese accidente" |

- **Fuentes:** seccion 7 del plan (contratos) y seccion 9 (escenarios).

### 4.5 Puesta en marcha (resumen)

- **Objetivo:** que el usuario sepa que necesita para empezar. El detalle esta en el README.
- **Contenido:**
  - Requisitos: Docker y una clave gratuita de OpenRouter.
  - Tres pasos:
    1. Copiar `.env.example` a `.env` y colocar la clave.
    2. Ejecutar `docker compose up -d --build`.
    3. Elegir la CLI o la API.
  - Remision al README para el detalle y la solucion de problemas.
- **Fuentes:** README (tarea 6.1).

### 4.6 Uso desde la linea de comandos (CLI)

- **Objetivo:** ensenar a conversar con el agente desde la terminal.
- **Contenido:**
  - Como iniciar el chat: `docker compose run --rm cli` o, en local, `uv run accident-agent chat`.
  - Comandos internos: `/salir`, `/reiniciar` e `/historial`.
  - Pregunta unica, sin chat: `accident-agent ask "..."`.
  - Opcion `--verbose`: que muestra (herramientas usadas, parametros y duracion) y cuando conviene usarla.
  - Captura de una sesion real.
- **Fuentes:** tarea 4.8.
- **Evidencia:** captura del chat con una consulta y con `--verbose`.

### 4.7 Uso desde la API REST

- **Objetivo:** ensenar a usar el agente desde otra aplicacion o con curl.
- **Contenido:**
  - URL base y documentacion interactiva en `/docs` (Swagger).
  - `POST /chat`:
    - ejemplo real de solicitud y respuesta;
    - como reutilizar `session_id` para hacer seguimientos.
  - `GET /health`: que informa.
  - `[O] GET /reports/{report_id}`, si se implementa.
  - Codigos de respuesta y su significado (200, 422, 500, 503).
  - Ejemplo completo con curl.
- **Fuentes:** seccion 7.7 del plan; tarea 4.9.
- **Evidencia:** captura de Swagger y solicitudes y respuestas reales, incluido un seguimiento con el mismo `session_id`.

### 4.8 Como formular consultas

- **Objetivo:** que el usuario obtenga buenas respuestas a la primera.
- **Contenido:**
  - Tabla de filtros que el agente entiende, con una frase de ejemplo para cada uno.
  - Valores aceptados: remite al catalogo del anexo.
  - Fechas absolutas ("en marzo de 2025") y relativas ("en los ultimos 6 meses").
  - Limite de resultados: 10 por defecto y 50 como maximo; como pedir mas.
  - Consejos:
    - ser especifico;
    - usar el identificador para un siniestro concreto;
    - hacer una pregunta por mensaje, para ahorrar cuota del modelo gratuito.
- **Fuentes:** seccion 7.3 del plan; `domain/catalogs.py`.

### 4.9 Ejemplos de conversacion

- **Objetivo:** mostrar el agente en accion con casos reales.
- **Contenido:**
  - Los escenarios 1 a 13 de la seccion 9 del plan.
  - Para cada uno: la pregunta, la respuesta real (recortada si es larga) y las herramientas usadas (vistas con `--verbose`).
  - Como minimo deben aparecer:
    - un seguimiento (escenario 3 seguido del 4);
    - una secuencia de varias herramientas (escenario 5 o 6);
    - una consulta sin resultados (escenario 10);
    - una solicitud de datos personales rechazada (escenario 7).
- **Fuentes:** seccion 9 del plan.
- **Evidencia:** transcripciones guardadas en la tarea 5.2.

### 4.10 Informes generados

- **Objetivo:** explicar como pedir un informe y que contiene.
- **Contenido:**
  - Tres formas de pedirlo: por identificador, a partir de una busqueda o como seguimiento ("de esos accidentes").
  - Estructura del informe:
    - encabezado;
    - resumen agregado;
    - detalle por siniestro;
    - advertencias de calidad de datos;
    - nota de privacidad.
  - Donde se guarda (`reports/` y formato del nombre del archivo) y como obtenerlo por la API.
  - Que pasa con identificadores inexistentes o con siniestros anulados.
  - El ejemplo completo va en el anexo.
- **Fuentes:** seccion 7.4 del plan; tarea 3.5.
- **Evidencia:** el informe completo generado en el escenario 6.

### 4.11 Privacidad y tratamiento de datos

- **Objetivo:** explicar que datos se muestran, cuales no y por que.
- **Contenido:**
  - Datos que nunca se muestran (nombres, cedulas y placas) y el motivo: minima exposicion.
  - Datos que si se muestran: rol, edad, sexo, condicion, proteccion y alcoholemia.
  - Registros anulados: no se cuentan y se informa cual los reemplaza.
  - Informes reemplazados: se indica cual es el vigente.
  - Informes reservados: no estan disponibles en el sistema.
  - Aviso de que todos los datos son ficticios.
- **Fuentes:** tarea 1.5; secciones 4 y 7.3 del plan.

### 4.12 Comportamiento ante errores y ausencia de datos

- **Objetivo:** que el usuario sepa que esperar y que hacer cuando algo no sale bien.
- **Contenido:** tabla de situaciones. Los textos de la columna central se reemplazan por los mensajes reales observados en la tarea 5.3.

| Situacion | Que ve el usuario | Que puede hacer |
| --- | --- | --- |
| No hay resultados | Aviso de que no hay siniestros con esos criterios, sin datos inventados | Ampliar los filtros o revisar los valores |
| Identificador inexistente | Aviso de identificador no encontrado | Verificar el identificador |
| Registro anulado | Aviso de anulacion e identificador del reemplazo | Consultar el registro que lo reemplaza |
| Pregunta fuera de alcance | Explicacion de lo que el agente puede hacer | Reformular dentro del tema |
| Pedido de datos personales | Negativa explicada | - |
| Valor no reconocido (p. ej. una provincia mal escrita) | Advertencia con sugerencias | Usar un valor del catalogo |
| Base de datos no disponible | Mensaje de servicio no disponible; el sistema sigue activo | Revisar `docker compose ps` y reintentar |
| Limite del proveedor de IA o clave invalida | Mensaje de limite alcanzado o de configuracion | Esperar o revisar la clave en `.env` |
| Herramienta demasiado lenta | Aviso de tiempo agotado | Reintentar o simplificar la consulta |
| Limite de iteraciones | Respuesta parcial con aviso | Dividir la pregunta |
| Mensaje invalido en la API (vacio o muy largo) | Error 422 con el detalle | Corregir el mensaje |

- **Fuentes:** escenarios 10 a 17 de la seccion 9 del plan; tarea 5.3.

### 4.13 Limitaciones para el usuario

- **Objetivo:** fijar expectativas realistas.
- **Contenido:**
  - Datos ficticios y acotados: 29 siniestros vigentes, del 2025-01-12 al 2026-09-02. Varias provincias, como Galapagos, no tienen registros.
  - La conversacion se pierde al reiniciar el sistema.
  - Cuota diaria limitada del modelo de IA gratuito.
  - Coordenadas solo referenciales.
  - Respuestas en espanol.
  - La interpretacion de preguntas ambiguas depende del modelo gratuito.
- **Fuentes:** tarea 5.8; seccion 10 del plan.

### 4.14 Preguntas frecuentes

- **Contenido sugerido:**
  - Puedo consultar un siniestro por su identificador?
  - Por que no veo nombres ni cedulas?
  - Como pido un informe de varios siniestros?
  - Que significa "anulado"?
  - Por que una respuesta puede tardar?
  - Que hago si aparece un aviso de limite de solicitudes?
  - Donde quedan guardados los informes?

### 4.15 Anexos

- Catalogo de valores aceptados: provincias, tipos, causas, clima, superficie, iluminacion y tipos de vehiculo. Se genera desde `domain/catalogs.py` para que coincida con el codigo.
- Ejemplo completo de un informe generado.
- Glosario para el usuario.

## 5. Capturas y evidencias a recolectar

Se usa la misma carpeta y convencion que en la guia del documento tecnico (`docs/evidencias/<tarea>_<descripcion>.<ext>`), con el prefijo `func_` en el nombre.

| Evidencia | Seccion que la usa | Momento |
| --- | --- | --- |
| Captura del chat en la CLI, con una consulta normal y con `--verbose` | 4.6 | Etapa 4 |
| Captura de Swagger en `/docs` | 4.7 | Etapa 4 |
| Solicitud y respuesta reales de `POST /chat`, incluido un seguimiento con el mismo `session_id` | 4.7 | Etapa 4 |
| Catalogo de valores exportado desde el codigo | 4.8 y anexos | Etapa 3 |
| Transcripciones de los escenarios 1 a 13 | 4.9 | Etapa 5 |
| Informe completo generado en el escenario 6 | 4.10 y anexos | Etapa 5 |
| Mensajes reales de cada situacion de error | 4.12 | Etapa 5 |

## 6. Recomendaciones de redaccion

- Escribir para alguien que nunca vio el sistema.
- Una idea por parrafo; usar tablas para capacidades y errores.
- Mostrar primero el ejemplo y despues la explicacion.
- Las capturas deben ser legibles y no mostrar claves ni datos sensibles (cuidado con un `.env` visible en la terminal).
- Usar los mismos terminos que el documento tecnico: siniestro, informe y sesion.
- No prometer capacidades que no esten implementadas y probadas.

## 7. Lista de verificacion final

- [x] Todas las secciones de la tabla de avance estan completas.
- [x] Cada capacidad tiene al menos un ejemplo real.
- [x] Hay un ejemplo de seguimiento ("ese accidente") y otro de varias herramientas encadenadas.
- [x] Todas las situaciones de la seccion 4.12 estan documentadas con el mensaje real.
- [x] Los ejemplos coinciden con la version entregada del sistema.
- [x] Ningun ejemplo muestra nombres, cedulas, placas ni claves.
- [x] El catalogo de valores coincide con el codigo.
- [x] No hay contradicciones con el README ni con el documento tecnico.

## Avance de entrega (2026-11-16)

Version 1.1 en `docs/entrega/` (Markdown y PDF): URL publica, referencia de entrega (tag `entrega-1.0`), paso de clonado y revision de anexos (encabezados, ortografia y catalogo contrastado con `scripts/export_catalog.py`). Lista de verificacion de la seccion 7 recorrida en la tarea 6.5; resultado en `docs/evidencias/etapa-6_notas.md`. Envio pendiente (6.6).
