# Etapa 1 - Notas de cierre

- **Fecha de cierre:** 2026-11-15.
- **Tareas:** 1.1 a 1.10, todas cerradas (1.9 `[R]` incluida).
- **DoD verificada:** `docs/evidencias/1.10_verificacion_cierre.txt` (SHA-256 sin cambios, 54 rutas con tratamiento documentado, 42 de 42 anomalias con decision, 455 pruebas en verde, ruff, mypy y `ascii_guard` sin errores).

## Decisiones y alternativas descartadas

| Area | Decision | Alternativas descartadas y motivo |
| --- | --- | --- |
| Perfilado | Modulo propio (`quality_report`) con anomalias por codigo y sin mostrar PII | ydata-profiling o pandas: pesados para 31 registros anidados y sin control sobre la exclusion de PII |
| Fechas | 4 formatos explicitos con `strptime`, dia primero, zona America/Guayaquil | `dateutil.parser`: puede leer `03/02/2025` como 2 de marzo |
| Montos | El ultimo separador es el decimal; expresiones completas | Quitar separadores sin validar: `1,000.000,00` produciria un numero equivocado |
| Catalogos | `StrEnum` por catalogo y tablas de clave normalizada; sinonimos que chocan fallan al importar | Diccionarios sueltos: un sinonimo duplicado pisaria otro en silencio |
| Provincia | Catalogo cerrado de las 24 provincias | Solo las 17 observadas: "Galapagos" (escenario 10) seria un error de validacion y no "sin resultados" |
| Canton, parroquia y via | Dimensiones abiertas: nombre derivado de la clave (`display_name`) y alias `e35` | Catalogo cerrado: exigiria 221 cantones y mas de mil parroquias de una fuente externa |
| Valor desconocido | Error de carga (`NormalizationError`) | Entrar como valor nuevo: ensuciaria estadisticas sin aviso |
| Edad | Exacta, decidida por el candidato | Rangos: menos detalle sin mejora real de privacidad sin nombre, cedula ni placa |
| Prompt injection (SIN-2026-0009) | Narrativa sin editar; defensa estructural (sin PII en el grafo, datos delimitados, prueba dedicada) | Neutralizar la frase: modifica el dato y solo cubre esa frase |
| INF-RES-01 | Excluido al leer el archivo (`RawDataset`) y no construible como `Report` | Excluirlo en el pipeline: su texto con PII llegaria a un modelo |
| Modelos | Crudos permisivos con los tipos observados; dominio estricto e inmutable con conteos calculados | Conteos como campos llenados por el pipeline: podrian contradecir a las personas |
| Redaccion de PII | Patrones genericos de cedula, RUC y placas de auto y moto | `99\d{8}`: solo reconoce las cedulas ficticias (observacion del candidato) |
| Convencion ASCII | `scripts/ascii_guard.py` escapa solos los literales de Python y revisa Markdown; regla en una tabla de `CLAUDE.md` | Escapar a mano (fallo 3 veces) y comprobar con `grep` (contradecia la excepcion de datos) |

## Anomalias nuevas

El catalogo final tiene 30 decisiones (`A01` a `A30`): las 23 de la seccion 4 del plan y 7 nuevas.

- **A13:** raya `–` en 11 nombres de via, que `normalize_key` no convertia.
- **A20:** claves presentes en un solo registro (`motivo_anulacion`, `reemplaza_a`, `dias_hasta_deceso`).
- **A22:** `via_analizada` nula o escrita distinto que en los registros.
- **A23:** fecha de los informes como texto `dd/mm/aaaa`.
- **A26:** 17 nombres repetidos con cedulas distintas: el nombre no identifica.
- **A29:** nombres de campo distintos al diccionario (`estado` frente a `estado_registro`).
- **A30:** registros no ordenados; ademas, la v2 de SIN-2025-0007 aparece antes que la v1 (A15), por lo que se elige por `version` y no por posicion.

## Decisiones de normalizacion

- 12 reglas de valor (`N01` a `N12`) y 6 por registro (`R01` a `R06`) en `docs/datos/reglas_normalizacion.md`, con ejemplos reales de entrada y salida.
- Principios: funciones puras, formatos explicitos, falla ante lo desconocido, faltante es null (salvo `proteccion`, que tiene `no_registrado`), canonicos en ASCII y en espanol, original intacto y defensas comunes (booleanos, negativos e infinitos rechazados).
- Conteos de victimas derivados de las personas; el resumen declarado solo marca `summary_mismatch` (SIN-2025-0012).

## Politica de datos personales

- Documento: `docs/datos/politica_datos_personales.md` (reglas `P1` a `P7`).
- Nombre y cedula se descartan al leer; la placa solo enlaza persona y vehiculo y se descarta; ids sinteticos `<id_parte>-P<n>` y `-V<n>`.
- Textos libres verificados sin PII: 45 textos contra 61 nombres, 80 cedulas y 49 placas, 0 coincidencias (1 falso positivo explicado); control positivo en INF-RES-01.
- Riesgos residuales declarados: combinacion de atributos (edad, sexo, fecha, lugar) y 2 menores con edad exacta.

## Cifras relevantes

| Indicador | Valor |
| --- | --- |
| Registros / ids distintos / informes | 31 / 30 / 5 |
| Rutas perfiladas / anomalias detectadas | 60 / 42 |
| Decisiones del catalogo | 30 (23 previstas y 7 nuevas) |
| Escrituras categoricas -> valores canonicos | 115 escrituras distintas en campos cerrados; por ejemplo causa 17 -> 10, tipo de vehiculo 16 -> 10, proteccion 12 -> 5, via 25 -> 20 |
| Rangos tras normalizar | danos 1 200 a 41 000; km 3 a 205 (5 null); edad 7 a 71; alcoholemia 0 a 1.6 (34 null) |
| Valores de control de la Etapa 2 reproducidos con un prototipo | 30 siniestros, 29 vigentes, 18 fallecidos, 44 heridos, 15 con fallecidos, 7 con moto, Pichincha y Guayas 5/5, 4 en la E35 con fallecidos, 4 informes |
| Pruebas | 455: normalizadores 169, catalogos 155, modelos de dominio 55, perfilado 29, guardia ASCII 19, modelos crudos 12, reporte 12, configuracion 4 |

## Problemas encontrados y solucion

| Problema | Solucion |
| --- | --- |
| Escapes `\u` que quedaban como caracteres con tilde (tareas 1.1, 1.6 y 1.7) | `scripts/ascii_guard.py`, que los escapa solo, y hook `ascii-guard` en pre-commit |
| El comando de comprobacion ASCII contradecia la excepcion de datos | Regla por tipo de archivo en `CLAUDE.md`; Markdown valida solo fuera de comillas invertidas |
| Cifras redactadas de memoria incorrectas (marcas, `N/A`, sinonimos, digito verificador, escrituras de marca) | Toda cifra se comprueba con un script antes de escribirla en documentos o pruebas |
| Patron de placa que tomaba `SIN-2026` de `SIN-2026-0009` como placa | `(?!-\d)` al final y casos de prueba positivos y negativos |
| Regex de la tarea 5.4 atada a las cedulas ficticias (`99\d{8}`) | Valores exactos de la nomina mas patrones genericos |
| Comprobacion de la DoD que marcaba 4 rutas como no documentadas | Estaban cubiertas por la fila de su campo padre (`resumen`, `secciones[]`); se corrigio el script y se regenero la evidencia |

## Archivos y modulos clave

- Codigo: `src/accident_agent/ingestion/quality_report.py`, `normalizers.py`, `raw_models.py`, `quality_markdown.py`; `src/accident_agent/domain/catalogs.py` y `models.py`; `scripts/ascii_guard.py`.
- Pruebas: `tests/unit/test_quality_report.py`, `test_normalizers.py`, `test_catalogs.py`, `test_raw_models.py`, `test_domain_models.py`, `test_quality_markdown.py`, `test_ascii_guard.py`.
- Documentos: `docs/datos/analisis_datos.md`, `catalogo_anomalias.md`, `reglas_normalizacion.md`, `politica_datos_personales.md`, `reporte_calidad_datos.md` (generado).
- Configuracion: `.pre-commit-config.yaml` (hook `ascii-guard`), `CLAUDE.md` (convencion ASCII), `docs/PLAN_DESARROLLO.md`.

## Evidencias guardadas

| Archivo | Contenido | Seccion de la guia tecnica |
| --- | --- | --- |
| `docs/evidencias/1.1_perfilado.json` | Salida del perfilado (60 rutas, 42 anomalias); comprobada al dia en el cierre | 5.4 |
| `docs/datos/reporte_calidad_datos.md` | Reporte de calidad generado por codigo; una prueba verifica que esta al dia | 5.4 |
| `docs/evidencias/1.5_verificacion_datos_personales.txt` | Busqueda de PII en textos libres (solo conteos e ids) | 5.13 |
| `docs/evidencias/1.7_pruebas_normalizadores.txt` | Pruebas de normalizadores y catalogos (324); comprobada al dia en el cierre | 5.5 |
| `docs/evidencias/1.10_verificacion_cierre.txt` | SHA-256 del original y verificacion de la DoD | 5.5 |

La etapa no produce evidencia `func_`.

## Secciones de los documentos finales que alimenta

- **Documento tecnico:** 5.4 Analisis de los datos (material completo); 5.5 Normalizacion y carga (reglas y normalizadores; falta la carga de la Etapa 2); 5.13 Seguridad y privacidad (politica y prompt injection); 5.15 Pruebas (unitarias); 5.16 Limitaciones (riesgos residuales de privacidad).
- **Documento funcional:** 4.3 Conceptos basicos (tipos de siniestro y gravedad de INF-2026-02); 4.11 Privacidad y tratamiento de datos; 4.13 Limitaciones para el usuario.

## Detalle por tarea

Registro hecho durante la etapa, tarea por tarea.

### 1.1 Perfilado reproducible

#### Decisiones

- **Perfilado por ruta:** un `FieldProfile` por cada ruta del JSON (`registros[].personas[].edad`). Las claves ausentes se cuentan contra su objeto contenedor, de modo que se distingue "clave ausente" de "valor null".
- **Anomalias por codigo:** 13 codigos (`AnomalyCode`), 6 por campo y 7 por registro, en lugar de una revision manual. La seccion 4 del plan queda comprobada por pruebas.
- **Privacidad en la salida:** nombre, cedula y placa (por nombre de clave) y los textos libres (`narrativa`, `texto`) nunca muestran valores; solo conteos e ids de registro. Las instrucciones sospechosas se describen con una etiqueta ("ignorar instrucciones"), sin citar el texto.
- **Formas de valores:** cada racha de digitos pasa a `9` y cada racha de letras a `a` (`03/02/2025 22:15` -> `9/9/9 9:9`). Distingue formatos sin depender de la longitud de los numeros.
- **Salida JSON con `ensure_ascii`:** el archivo de evidencia queda en ASCII; los valores con tildes se ven como `\uXXXX`. El informe legible en Markdown es la tarea 1.9.
- **`normalize_key`** (sin tildes, minusculas, espacios colapsados) se creo en `normalizers.py` para reutilizarla en la tarea 1.7.

#### Alternativas descartadas

- **Marcar como variante de formato todo texto con digitos:** generaba ruido en vias, modelos de vehiculo y titulos (10 avisos, 5 falsos). Se limito a campos donde todo valor no de relleno tiene digitos.
- **Tratar el "-" siempre como separador:** separaba latitudes positivas y negativas en formatos distintos. Ahora un "-" al inicio o tras coma, espacio o parentesis es signo.
- **Usar ydata-profiling o pandas:** dependencias pesadas para 31 registros anidados, sin control sobre la exclusion de PII.

#### Cifras

- 31 registros, 5 informes, 60 rutas perfiladas y 42 anomalias.
- Por codigo: 9 `case_variants`, 7 `mixed_types`, 7 `partial_presence`, 6 `missing_values`, 5 `format_variants`, 2 `replacement_link`, y 1 de `whitespace`, `duplicate_id`, `summary_mismatch`, `restricted_classification`, `pii_in_text` y `suspicious_instruction`.
- Verificacion de privacidad sobre la evidencia: 0 coincidencias de 61 nombres, 80 cedulas y 49 placas distintas.
- Pruebas: 40 de 40 pasan (unitarias, sin Neo4j ni LLM).

#### Problemas encontrados

- Los literales con tildes en las pruebas quedaron escritos como caracteres no ASCII aunque se redactaron como escapes `\u`. Se detecto con `LC_ALL=C grep` y se reescribieron con un script que genera los escapes.

- **Prevencion:** se agrego a pre-commit el hook local `ascii-only-code` (`pygrep` con `[^\x00-\x7F]`) sobre Python, TOML y YAML. Alcance acordado con el candidato: solo codigo y comentarios. Probado con un archivo de prueba con tilde, que el hook bloqueo.

#### Archivos

- `src/accident_agent/ingestion/quality_report.py`, `src/accident_agent/ingestion/normalizers.py`.
- `tests/unit/test_quality_report.py`, `tests/unit/test_normalizers.py`.
- `.pre-commit-config.yaml` (hook `ascii-only-code`).
- Evidencia: `docs/evidencias/1.1_perfilado.json`.

### 1.2 Documentacion de la estructura

- Documento: `docs/datos/analisis_datos.md`, con cifras del perfilado y significados de INF-2026-02 (marcados como *inferidos* cuando el diccionario no los define).
- Los valores originales con tildes se citan entre comillas invertidas (excepcion de datos en `CLAUDE.md`); se verifico que no hay texto no ASCII fuera de ellas ni datos personales.

#### Hallazgos nuevos (para el catalogo de la tarea 1.3)

- **Orden de versiones:** SIN-2025-0007 v2 esta en la posicion 6 y v1 en la 30 (ultima). Quedarse con "la ultima aparicion" cargaria la v1 (danos 3900); hay que elegir por `version`.
- **Nombres no unicos:** 17 nombres se repiten con cedulas distintas; el nombre no sirve como identificador.
- **Nombres de campo distintos al diccionario:** `estado` (`ACTIVO`/`ANULADO`) frente a `estado_registro` (`vigente`/`anulado`), y `proteccion` frente a `uso_proteccion`.
- **Id fuera de patron:** INF-RES-01 no sigue `INF-AAAA-NN`.

#### Verificaciones de integridad (sin hallazgos)

- Las 76 placas no nulas de personas apuntan a un vehiculo del mismo registro, y los 50 vehiculos tienen al menos un ocupante.
- Los 5 peatones son exactamente las 5 personas sin vehiculo.
- Cada vehiculo trae `marca_modelo` o el par `marca` y `modelo`, nunca ambos ni ninguno.
- El anio del id coincide con el de `fecha_hora` en los 31 registros.

### 1.3 Catalogo de anomalias

- Documento: `docs/datos/catalogo_anomalias.md`, con 30 anomalias (`A01` a `A30`): las 23 de la seccion 4 del plan y 7 nuevas. Cada una tiene evidencia, decision, motivo y la tarea o modulo donde se aplica.
- **Trazabilidad:** una tabla asigna una decision a cada una de las 42 anomalias del perfilado; un script comprobo que la tabla y el perfilado coinciden exactamente (42 y 42).
- **Verificaciones (V1 a V6), ejecutadas sobre el JSON real sin imprimir PII:**
  - V1: `M` es masculino (0 de 21 nombres de pila terminan en "a", frente a 13 de 14 del grupo femenino; las narrativas usan "Un peaton" y "Un motociclista"). Cierra la verificacion pendiente de la seccion 4.
  - V2: con `dd/mm` las 31 fechas son validas y 29 coinciden con `fecha_actualizacion`; con `mm/dd` hay 3 invalidas.
  - V3: las 29 coordenadas caen en el Ecuador continental.
  - V4: el fallecido diferido ya tiene `condicion` fallecido.
  - V5: `N/A` y `NO APLICA` corresponden a peatones y pasajeros de bus.
  - V6: rangos plausibles tras parsear (edad 7 a 71, danos 1 200 a 41 000, km 3 a 205, alcoholemia 0 a 1.6).

#### Decisiones destacadas

- **Valor desconocido = error de carga:** un valor categorico que no esta en el catalogo detiene la carga en lugar de entrar como valor nuevo silencioso.
- **Codigos de via solo desde el texto** (`E35`, `E45`, `E15`); no se infieren de conocimiento externo.
- **Causas sinonimas:** el codigo canonico es la escritura mas frecuente (`exceso_de_velocidad`, `conducir_bajo_efectos_del_alcohol`).
- **Marca y modelo** en mayusculas, separados en el primer espacio (las 13 marcas son de una palabra).
- **INF-RES-01** se excluye por `clasificacion`, no por su id.

#### Hallazgos nuevos de esta tarea

- La raya larga (U+2013) en 11 nombres de via sobrevive a `normalize_key`; se convierte en `-` (A13).
- 2 personas menores de 18 anios: entrada para la politica de datos personales (tarea 1.5).

#### Problemas encontrados

- Dos cifras redactadas de memoria resultaron incorrectas al verificarlas con script (21 marcas en lugar de 13; `N/A` en 2 pasajeros de bus en lugar de 1, el otro era `NO APLICA`). Se corrigieron antes de cerrar la tarea; las cifras del catalogo salen de ejecuciones.

### 1.4 Reglas de normalizacion

- Documento: `docs/datos/reglas_normalizacion.md`, con 12 reglas de valor (`N01` a `N12`), los catalogos categoricos con todas las escrituras observadas, 6 reglas por registro (`R01` a `R06`) y la correspondencia campo a propiedad del grafo.
- **Origen de los ejemplos:** un prototipo desechable de las reglas (fuera del repositorio) se ejecuto sobre los 31 registros sin errores; las salidas del documento se copiaron de esa ejecucion. Las cifras restantes (Pichincha y Guayas 5/5, E35 6, 18 fallecidos y 44 heridos en vigentes) se confirmaron con un script y coinciden con los valores de control de la Etapa 2.

#### Decisiones

- **Formatos explicitos, sin deteccion automatica:** se descarto `dateutil.parser`, que puede leer `03/02/2025` como 2 de marzo; solo se aceptan los 4 formatos de fecha listados.
- **Montos:** el separador que aparece ultimo es el decimal; el caso de un solo separador queda especificado como regla defensiva (no hay ejemplos en los datos).
- **Provincia con catalogo cerrado de las 24 provincias** (no solo las 17 observadas): una consulta por Galapagos (escenario 10) debe dar cero resultados y no un error de validacion.
- **Canton, parroquia y via como dimensiones abiertas:** el nombre canonico se deriva de la clave (`display_name`: mayuscula inicial, salvo `de`, `la`, `los`...). Se descarto un catalogo cerrado porque exigiria 221 cantones y mas de mil parroquias de una fuente externa sin aportar control. Se ajusto la regla comun del catalogo de anomalias (seccion 2).
- **Alias de via unico:** `E35` -> `Panamericana E35 (Troncal de la Sierra)`; el codigo de via se extrae del texto con `\bE\d{2,3}\b`. Resultado: 25 escrituras -> 21 claves -> 20 vias.
- **`camion` no se fusiona** con `camion_liviano` ni `camion_pesado`: el dato no indica cual es.
- **`fuente`** no se carga: es constante en los 31 registros.
- **Errores sin PII:** `NormalizationError` incluye registro, ruta y motivo; el valor solo si el campo no es personal.

#### Cifras

- Categoricos: tipo 9 -> 5, causa 17 -> 10, tipo de vehiculo 16 -> 10, servicio 6 -> 3, rol 5 -> 3, condicion 8 -> 4, sexo 6 -> 2, proteccion 12 -> 5, provincia 21 -> 17, canton 26 -> 22, parroquia 29 -> 29.
- Valores: km 26 con dato (3 a 205) y 5 null; alcoholemia 47 con dato (maximo 1.6 g/L) y 34 null; danos de 1 200 a 41 000.

### 1.5 Politica de datos personales

- Documento: `docs/datos/politica_datos_personales.md`, con la clasificacion de los campos, 7 reglas (`P1` a `P7`), la verificacion de textos libres, la prompt injection, los datos enviados a terceros y los riesgos residuales.
- Evidencia: `docs/evidencias/1.5_verificacion_datos_personales.txt`, salida real del script de verificacion (solo conteos e ids).

#### Decisiones

- **Edad exacta**, confirmada por el candidato. Se descartaron los rangos: sin nombre, cedula ni placa la edad no identifica, y los rangos quitan detalle util para el analisis.
- **Prompt injection de SIN-2026-0009:** la narrativa se carga sin editar. La defensa es estructural: no hay PII en el grafo, los datos van delimitados como no confiables y hay una prueba dedicada. Se descarto neutralizar la frase en la carga porque modifica el dato y solo cubre esa frase.
- **Exclusion de informes por `clasificacion`**, no por id (P3).
- **Redaccion en logs y trazas con patrones genericos** (P6): cedula de 10 digitos, con guion y RUC de 13; placa de auto y de moto. No dependen del prefijo `99` ni del formato unico de placa de los datos ficticios. Se aplican solo a texto para no alterar campos numericos como `unix_timestamp`.

#### Cifras

- Nomina: 61 nombres distintos, 80 cedulas (formato `9999999999`, todas empiezan con `99`) y 49 placas (formato `AAA-9999`).
- 45 textos libres revisados (31 narrativas, 1 motivo de anulacion, 4 titulos y 9 secciones publicas): 0 nombres, cedulas, placas, correos o telefonos.
- Control positivo: el mismo script encuentra 6 nombres y 6 cedulas en INF-RES-01.
- 2 menores de edad (7 y 10 anios), registrados como riesgo residual.

#### Problemas encontrados

- La busqueda por palabras sueltas de los nombres dio 1 coincidencia en SIN-2026-0010. Se clasifico sin imprimir el valor: es un ordinal comun que tambien es nombre de pila y no corresponde a ninguna persona del registro (falso positivo).
- **Patrones atados a los datos ficticios** (observado por el candidato): la tarea 5.4 preveia buscar cedulas con `99\d{8}`, que solo reconoce las cedulas ficticias; con datos reales una fuga pasaria la prueba sin detectarse. La carga no se veia afectada, porque descarta la cedula por el nombre del campo sin leer su valor, y el perfilado ya usaba `\b\d{10}\b`. Se cambio la 5.4 a valores exactos de la nomina mas patrones genericos, y P6 se amplio con cedula con guion, RUC y placa de moto.
- **Falso positivo en el patron de placa:** al probar los patrones, `\b[A-Z]{3}-?\d{3,4}\b` sin distinguir mayusculas reconocia `SIN-2026` dentro de `SIN-2026-0009` (e `INF-2026` en `INF-2026-02`), lo que habria ocultado los ids de siniestros en los logs. Se agrego `(?!-\d)` al final y se dejaron casos de prueba positivos y negativos en P6 para la tarea 4.6.

### 1.6 Catalogos canonicos

- Modulo: `src/accident_agent/domain/catalogs.py`, con 15 `StrEnum` (tipo, causa, clima, superficie, iluminacion, tipo y servicio de vehiculo, rol, condicion, sexo, proteccion, estado del registro, estado y clasificacion del informe, provincia), una tabla de busqueda por catalogo y `ROAD_ALIASES`.
- Pruebas: `tests/unit/test_catalogs.py`, escritas antes del modulo a partir de las tablas de `reglas_normalizacion.md`. Suite completa: 195 de 195 pasan; ruff, mypy (estricto) y los hooks de pre-commit sin errores.

#### Decisiones

- **Tablas de clave a valor, no funciones:** el modulo de dominio solo usa la biblioteca estandar. Aplicar `normalize_key` y fallar ante un valor desconocido queda para los normalizadores (1.7).
- **Formas propias automaticas:** cada valor entra con su forma (`perdida_de_pista`) y con espacios (`perdida de pista`); a mano solo van 15 sinonimos reales (2 de causa, 4 de sexo, 8 de proteccion y `activo`). Con ellos resuelven las 115 escrituras distintas no nulas de los campos cerrados.
- **Conflictos detectados al importar:** `build_lookup` falla si un sinonimo apunta a otro valor, en lugar de pisarlo en silencio.
- **Miembros con el valor canonico** (`CHOQUE = "choque"`), no traducidos al ingles: los nombres de clase siguen la convencion en ingles, pero traducir los valores de datos crearia un segundo vocabulario.
- **Definiciones de los tipos de siniestro:** no se copian al codigo; la carga las toma de INF-2026-02 (2.2). Evita duplicar datos y texto no ASCII en el codigo.
- **Sin catalogo para canton, parroquia y via**, segun la regla de la tarea 1.4; solo el alias `e35`.

#### Pruebas clave

- 104 casos parametrizados con escrituras de las tablas de la tarea 1.4, incluido `Galapagos`.
- Las 115 escrituras reales del JSON resuelven, leidas del archivo, y dan el numero esperado de canonicos (por ejemplo, causa 10 y provincia 17).
- Todo valor de cada catalogo cerrado aparece en los datos, salvo las 7 provincias sin siniestros.
- Las claves de las tablas son puntos fijos de `normalize_key`; los valores son ASCII y los codigos, `snake_case`.

#### Problemas encontrados

- Se repitio el problema de la tarea 1.1: los escapes `\u` de las pruebas quedaron escritos como caracteres con tilde. El hook `ascii-only-code` no lo vio porque `pre-commit run --all-files` solo revisa archivos versionados, y el archivo era nuevo. Se detecto con `LC_ALL=C grep` y se corrigio con un script. El hook lo habria bloqueado al hacer commit.

### 1.7 Normalizadores

- Modulo: `src/accident_agent/ingestion/normalizers.py`, una funcion pura por regla de la tarea 1.4: `normalize_key` (N01, ampliada con la raya), `display_name` (N02), `normalize_road` (N03), `parse_occurred_at` (N04), `parse_update_date` y `parse_report_date` (N05), `parse_amount` (N06), `parse_km` (N07), `parse_coordinates` (N08), `parse_alcohol` (N09), `parse_int` (N10), `split_brand_model` (N11), `clean_text` (N12), `to_canonical` y `normalize_protection` (catalogos).
- Pruebas: `tests/unit/test_normalizers.py`, escritas antes del codigo: los ejemplos de entrada y salida de la 1.4, casos invalidos por regla y un recorrido completo del JSON real que comprueba las cifras de la 1.4.
- Resultados: suite completa 357 de 357; normalizadores y catalogos 324 de 324. Ruff, formato y mypy estricto sin errores. Evidencia: `docs/evidencias/1.7_pruebas_normalizadores.txt`.

#### Decisiones

- **`NormalizationError` con motivo y valor**, sin id de registro ni ruta: una funcion pura no los conoce; el pipeline los agrega (2.2). El valor puede ir en el mensaje porque los normalizadores nunca reciben nombres, cedulas ni placas.
- **`strptime` con formatos explicitos** y no `dateutil` ni `fromisoformat`: solo entran los 4 formatos documentados.
- **Montos validados con expresiones completas:** `1,000.000,00` o `1.2345` son error en lugar de producir un numero equivocado.
- **Defensas agregadas a las reglas** (principio 7 de `reglas_normalizacion.md`): booleanos rechazados como numeros, negativos e infinitos rechazados, objetos de fecha y coordenadas con exactamente sus dos claves, y `marca_modelo` de una sola palabra como error.
- **Zona de los datos fija** (`DATA_TIMEZONE`, de la metadata) e independiente de `DEFAULT_TIMEZONE` de la configuracion, que es la zona de la herramienta de hora.
- **Rayas como codigos numericos** (`0x2013`) en lugar de caracteres literales, para que el codigo sea ASCII sin depender del editor.

#### Verificacion de las pruebas (mutaciones)

Como las pruebas pasaron a la primera, se introdujeron fallos a proposito, uno por vez, sobre una copia del modulo:

| Fallo introducido | Resultado |
| --- | --- |
| Fecha `mm/dd` en lugar de `dd/mm` | 4 pruebas fallan |
| La raya U+2013 deja de convertirse en guion | 4 pruebas fallan |
| Abscisa dividida por 100 en lugar de 1000 | 1 prueba falla |

Se restauro el original y la suite volvio a 357 de 357.

#### Cifras del JSON real (comprobadas por las pruebas)

- 31 fechas con desfase `-05:00`, anio igual al del id y ninguna posterior a su `fecha_actualizacion`.
- Danos de 1 200 a 41 000; km 26 con dato (3 a 205) y 5 null; 29 coordenadas.
- Alcoholemia: 47 con dato, 34 null, maximo 1.6; edad de 7 a 71; anio de vehiculo de 2012 a 2023; 13 marcas.
- 22 cantones, 29 parroquias, 20 vias (6 siniestros en la E35; codigos E35, E45 y E15), 17 provincias; 10 narrativas con espacios corregidos.

#### Problemas encontrados

- Las rayas de `_DASHES` quedaron como caracteres literales (ruff las marco con RUF001). Se reescribieron como codigos numericos.
- Un `\u` en las pruebas se volvio a convertir en caracter; se corrigio con el mismo script de escapes antes de ejecutar.

### Mejora de la convencion ASCII (entre las tareas 1.7 y 1.8)

Revision pedida por el candidato: si la regla de excepciones al ASCII causaba problemas.

#### Diagnostico

- **No afectaba a las pruebas ni al codigo en ejecucion:** `"Pérdida"` y el literal con tilde son el mismo valor en Python; las pruebas pasaban.
- **Si causaba friccion y una contradiccion:**
  - escapar a mano los valores reales fallo en las tareas 1.1, 1.6 y 1.7 (los escapes quedaban como caracteres), con retrabajo cada vez;
  - el comando de comprobacion de `CLAUDE.md` (`LC_ALL=C grep`, "no debe devolver lineas") contradecia la excepcion de datos: 4 documentos de `docs/datos/` lo "fallaban" aunque cumplian la regla, y uno (`catalogo_anomalias.md`, linea 144) la incumplia de verdad con citas de narrativas fuera de comillas invertidas;
  - el hook `ascii-only-code` solo corria al hacer commit, no revisaba Markdown y no distinguia un literal con datos de un comentario.

#### Cambios

- **`scripts/ascii_guard.py`** (solo biblioteca estandar):
  - Python: reescribe como `\uXXXX` los caracteres no ASCII de los literales de texto (el valor no cambia) y reporta como error los de comentarios, docstrings, identificadores, f-strings y cadenas raw;
  - Markdown: solo permite caracteres no ASCII entre comillas invertidas o en bloques de codigo; los emojis son error en cualquier lugar;
  - TOML, YAML y Jinja: todo el archivo en ASCII.
- **Pre-commit:** el hook `ascii-guard` reemplaza a `ascii-only-code` y suma Markdown y Jinja; excluye `data/` y `docs/enunciado/`.
- **`CLAUDE.md`:** la regla y sus excepciones pasan a una tabla por tipo de archivo, y la comprobacion es el script. La seccion 3 del plan remite a esa tabla en lugar de repetirla.
- **`catalogo_anomalias.md`:** las 3 citas de narrativas de V1 pasan a comillas invertidas.

#### Verificacion

- 19 pruebas nuevas en `tests/unit/test_ascii_guard.py` (las muestras con tilde se arman con `chr()` para no depender de la propia guardia); suite completa 376 de 376; ruff y mypy (`src tests scripts`) sin errores.
- Reproduccion del fallo real: copias de `test_catalogs.py` y `test_normalizers.py` con los escapes convertidos en tildes (14 y 19 lineas); la guardia las dejo identicas a los archivos corregidos a mano.
- Hook probado con un archivo temporal: escapo el literal, bloqueo el comentario con tilde (salida 1) y el archivo se elimino.
- Repositorio completo (versionado y nuevo, sin `data/` ni `docs/enunciado/`): sin problemas tras corregir la linea 144.

### 1.8 Modelos crudos y de dominio

- Modulos: `src/accident_agent/ingestion/raw_models.py` (permisivo) y `src/accident_agent/domain/models.py` (estricto).
- Pruebas: `tests/unit/test_raw_models.py` (12) y `tests/unit/test_domain_models.py` (55), escritas antes de los modelos. Suite completa: 443 de 443; ruff, formato, mypy estricto y `ascii_guard` sin errores.

#### Decisiones

- **Modelos crudos con los tipos observados y modo estricto:** `edad: int | str`, `danos_materiales: int | float | str`, etc. Pydantic conserva el tipo original (`"39"` sigue siendo texto) y deja la conversion a los normalizadores. `extra="forbid"` y claves obligatorias detectan cambios de estructura; una clave presente con null se distingue de una ausente.
- **Datos personales fuera desde la lectura:** `RawPerson` descarta `nombre` y `cedula` antes de validar; las placas usan `repr=False` y `exclude=True`; `hide_input_in_errors` evita que un error muestre valores.
- **INF-RES-01 se excluye al leer** (`RawDataset`) y no en el pipeline, como decia R05: asi su texto con datos personales nunca llega a un modelo. Solo se conserva su id en `excluded_report_ids`. Se actualizaron R05 y P1/P3.
- **Dominio estricto e inmutable:** solo acepta enums de `catalogs`, numeros y fechas ya convertidos (un `"40"` o un `"conductor"` en texto es error).
- **Conteos y derivados calculados** (`deaths`, `injured`, `unharmed`, `is_active`, `date`, `year`, `month`, `hour`) con `computed_field`: salen en `model_dump` para la carga y no pueden contradecir a las personas.
- **`Report` no admite informes reservados:** id `INF-AAAA-NN` y clasificacion `Literal[publico]`.
- **Invariantes en el modelo:** ids de vehiculos y personas con el prefijo del siniestro y sin duplicados, personas enlazadas a vehiculos existentes, peaton sin vehiculo, `days_until_death` solo en fallecidos y como maximo 30 (INF-2026-02), anulacion y reemplazo solo en anulados y sin autorreferencia, fecha del siniestro no posterior a la actualizacion, textos limpios (N12) y marca y modelo en mayusculas.
- **`CleanDataset`:** ids unicos, `REPLACED_BY` hacia un siniestro vigente y `SUPERSEDES` hacia un informe reemplazado.

#### Alternativas descartadas

- **`extra="ignore"` en los modelos crudos** para no declarar `nombre` y `cedula`: ocultaria tambien claves nuevas inesperadas.
- **Conteos como campos que llena el pipeline:** obligaria a validar que coincidan con las personas; calcularlos elimina la posibilidad de inconsistencia.
- **Exigir que el anio del id coincida con el de la fecha:** se cumple en los datos, pero un siniestro del 31 de diciembre registrado en enero seria valido; no se convirtio en invariante.

#### Verificacion

- Cada caso invalido de las pruebas se rechaza por el motivo previsto (se imprimio el primer error de los 34 casos).
- Prototipo desechable raw -> normalizadores -> dominio sobre el JSON real (no queda en el repositorio): `CleanDataset` valido con 30 siniestros (29 vigentes; SIN-2026-0010 `REPLACED_BY` SIN-2026-0011), SIN-2025-0007 v2 con 4 100, 18 fallecidos y 44 heridos en vigentes, 15 con fallecidos, 7 con motocicleta, Pichincha y Guayas 5/5, los 4 de la E35 con fallecidos, `summary_mismatch` solo en SIN-2025-0012 y 4 informes. Coinciden con todos los valores de control de la Etapa 2 que no requieren Neo4j.

#### Pendiente para la tarea 2.2 (visto en el prototipo)

- Los normalizadores reciben diccionarios: al pasar `RawDateParts` y `RawCoordinates` hay que usar `model_dump()` (o aceptar esos modelos en los normalizadores).
- `summary_mismatch` debe calcularse antes de construir el `Accident` (el prototipo uso `model_copy`, que no revalida).

### 1.9 Reporte de calidad de datos

- Modulo: `src/accident_agent/ingestion/quality_markdown.py`. Genera `docs/datos/reporte_calidad_datos.md` (200 lineas) con `uv run python -m accident_agent.ingestion.quality_markdown --output docs/datos/reporte_calidad_datos.md`.
- Pruebas: `tests/unit/test_quality_markdown.py` (12), escritas antes del modulo. Suite completa: 455 de 455; ruff, mypy, `ascii_guard` y los hooks de pre-commit sin errores ni cambios en el archivo generado.

#### Contenido del reporte

1. Encabezado: archivo, SHA-256, fecha del extracto, comando para regenerarlo y nota de privacidad.
2. Resumen: 31 registros, 5 informes, 60 rutas, 42 anomalias (tabla por codigo), INF-RES-01 excluido al leer y 10 narrativas corregidas.
3. Las 42 anomalias del perfilado con ruta, detalle, casos e ids.
4. Perfil por campo del JSON original (presentes, ausentes, nulos, vacios, tipos, distintos y valores mas frecuentes).
5. Resultado de la normalizacion: escrituras originales frente a valores canonicos por campo categorico (por ejemplo causa 17 -> 10, via 25 -> 20, marca 21 -> 13), rangos numericos y rangos de fechas.

#### Decisiones

- **Reutilizar y no duplicar:** el reporte combina `profile_data` (1.1) con los normalizadores (1.7) aplicados sobre `RawDataset`; no tiene logica de limpieza propia.
- **Determinista:** sin fecha de ejecucion; la misma entrada produce el mismo archivo. Una prueba compara el archivo versionado con uno recien generado y, si difiere, muestra el comando para regenerarlo. Se comprobo agregando una linea al archivo: la prueba fallo con ese mensaje.
- **Privacidad heredada:** el perfilado no muestra nombre, cedula, placa ni textos libres, y `RawDataset` ya descarta nombre, cedula e INF-RES-01. Una prueba busca la nomina completa y el inicio de cada narrativa y seccion en el reporte: 0 coincidencias.
- **Convencion ASCII:** los valores originales van entre comillas invertidas (`markdown_cell`, que tambien escapa `|`); una prueba pasa el reporte por `ascii_guard.check_markdown`.
- **Aclaracion de alcance:** la seccion 4 cuenta los 31 registros, antes de R01 y R02; el reporte lo dice para no confundirlo con los valores de control (por ejemplo, Pichincha 6 registros frente a 5 siniestros vigentes).

#### Problemas encontrados

- Una cifra de la prueba escrita sin verificar (23 escrituras de marca) era incorrecta; se comprobo con un script antes de implementar (21) y se corrigio.
