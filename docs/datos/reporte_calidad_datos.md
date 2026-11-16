# Reporte de calidad de datos

Archivo generado por codigo (tarea 1.9); no se edita a mano. Para regenerarlo:

`uv run python -m accident_agent.ingestion.quality_markdown --output docs/datos/reporte_calidad_datos.md`

- **Archivo:** `siniestros_raw.json`.
- **SHA-256:** `77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280`.
- **Extracto generado:** `2026-11-09`.
- **Privacidad:** no se muestran nombres, cedulas, placas ni textos libres (narrativas y secciones de informes); de esos campos solo hay conteos.
- **Referencias:** decisiones en `docs/datos/catalogo_anomalias.md`; reglas en `docs/datos/reglas_normalizacion.md`. Los valores entre comillas invertidas son textos originales del JSON.

## 1. Resumen

| Indicador | Valor |
| --- | --- |
| Registros | 31 |
| Informes | 5 |
| Rutas perfiladas | 60 |
| Anomalias detectadas | 42 |
| Informes excluidos al leer | INF-RES-01 |
| Narrativas con espacios corregidos (N12) | 10 |

Anomalias por codigo:

| Codigo | Cantidad |
| --- | --- |
| `case_variants` | 9 |
| `duplicate_id` | 1 |
| `format_variants` | 5 |
| `missing_values` | 6 |
| `mixed_types` | 7 |
| `partial_presence` | 7 |
| `pii_in_text` | 1 |
| `replacement_link` | 2 |
| `restricted_classification` | 1 |
| `summary_mismatch` | 1 |
| `suspicious_instruction` | 1 |
| `whitespace` | 1 |

## 2. Anomalias detectadas

| Codigo | Ruta | Detalle | Casos | Registros |
| --- | --- | --- | --- | --- |
| `mixed_types` | `registros[].fecha_hora` | object: 7, string: 24 | 31 | - |
| `format_variants` | `registros[].fecha_hora` | 3 formas: 9-9-9 9:9:9, 9-9-9a9:9:9-9:9, 9/9/9 9:9 | 3 | - |
| `case_variants` | `registros[].ubicacion.provincia` | 4 valores escritos de varias formas | 8 | - |
| `case_variants` | `registros[].ubicacion.canton` | 4 valores escritos de varias formas | 8 | - |
| `case_variants` | `registros[].ubicacion.via` | 4 valores escritos de varias formas | 8 | - |
| `mixed_types` | `registros[].ubicacion.km` | integer: 8, string: 22 | 30 | - |
| `format_variants` | `registros[].ubicacion.km` | 3 formas: 9, 9+9, a 9 | 3 | - |
| `missing_values` | `registros[].ubicacion.km` | valores null, vacios o de relleno | 5 | SIN-2025-0003, SIN-2025-0007, SIN-2025-0019, SIN-2026-0003 |
| `mixed_types` | `registros[].ubicacion.coordenadas` | object: 14, string: 15 | 29 | - |
| `missing_values` | `registros[].ubicacion.coordenadas` | valores null, vacios o de relleno | 2 | SIN-2025-0006, SIN-2025-0019 |
| `case_variants` | `registros[].tipo_siniestro` | 4 valores escritos de varias formas | 8 | - |
| `case_variants` | `registros[].causa_probable` | 5 valores escritos de varias formas | 10 | - |
| `mixed_types` | `registros[].danos_materiales` | integer: 8, string: 23 | 31 | - |
| `format_variants` | `registros[].danos_materiales` | 3 formas: $9,9.9, 9, 9.9,9 a | 3 | - |
| `case_variants` | `registros[].vehiculos[].tipo_vehiculo` | 6 valores escritos de varias formas | 12 | - |
| `partial_presence` | `registros[].vehiculos[].marca_modelo` | presente en 26 de 50 objetos | 24 | SIN-2025-0002, SIN-2025-0004, SIN-2025-0006, SIN-2025-0008, SIN-2025-0010, SIN-2025-0012, SIN-2025-0014, SIN-2025-0016, SIN-2025-0018, SIN-2026-0001, SIN-2026-0003, SIN-2026-0005, SIN-2026-0007, SIN-2026-0009, SIN-2026-0011 |
| `mixed_types` | `registros[].vehiculos[].anio` | integer: 32, string: 18 | 50 | - |
| `case_variants` | `registros[].vehiculos[].servicio` | 3 valores escritos de varias formas | 6 | - |
| `partial_presence` | `registros[].vehiculos[].marca` | presente en 24 de 50 objetos | 26 | SIN-2025-0002, SIN-2025-0004, SIN-2025-0006, SIN-2025-0008, SIN-2025-0010, SIN-2025-0012, SIN-2025-0014, SIN-2025-0016, SIN-2025-0018, SIN-2026-0001, SIN-2026-0003, SIN-2026-0005, SIN-2026-0007, SIN-2026-0009, SIN-2026-0011 |
| `partial_presence` | `registros[].vehiculos[].modelo` | presente en 24 de 50 objetos | 26 | SIN-2025-0002, SIN-2025-0004, SIN-2025-0006, SIN-2025-0008, SIN-2025-0010, SIN-2025-0012, SIN-2025-0014, SIN-2025-0016, SIN-2025-0018, SIN-2026-0001, SIN-2026-0003, SIN-2026-0005, SIN-2026-0007, SIN-2026-0009, SIN-2026-0011 |
| `case_variants` | `registros[].personas[].rol` | 2 valores escritos de varias formas | 4 | - |
| `mixed_types` | `registros[].personas[].edad` | integer: 61, string: 20 | 81 | - |
| `case_variants` | `registros[].personas[].condicion` | 4 valores escritos de varias formas | 8 | - |
| `mixed_types` | `registros[].personas[].alcohol_gl` | number: 14, string: 58 | 72 | - |
| `format_variants` | `registros[].personas[].alcohol_gl` | 2 formas: 9,9, 9.9 | 2 | - |
| `missing_values` | `registros[].personas[].alcohol_gl` | valores null, vacios o de relleno | 34 | SIN-2025-0001, SIN-2025-0002, SIN-2025-0003, SIN-2025-0004, SIN-2025-0005, SIN-2025-0006, SIN-2025-0009, SIN-2025-0010, SIN-2025-0011, SIN-2025-0012, SIN-2025-0014, SIN-2025-0015, SIN-2025-0016, SIN-2025-0017, SIN-2025-0018 |
| `missing_values` | `registros[].personas[].proteccion` | valores null, vacios o de relleno | 14 | SIN-2025-0001, SIN-2025-0002, SIN-2025-0004, SIN-2025-0009, SIN-2025-0014, SIN-2025-0015, SIN-2025-0018, SIN-2026-0001, SIN-2026-0004, SIN-2026-0008 |
| `missing_values` | `registros[].personas[].placa_vehiculo` | valores null, vacios o de relleno | 5 | SIN-2025-0002, SIN-2025-0009, SIN-2025-0015, SIN-2025-0018, SIN-2026-0008 |
| `partial_presence` | `registros[].personas[].dias_hasta_deceso` | presente en 1 de 81 objetos | 80 | SIN-2026-0011 |
| `whitespace` | `registros[].narrativa` | espacios al inicio o al final, dobles o saltos de linea | 10 | SIN-2025-0001, SIN-2025-0006, SIN-2025-0008, SIN-2025-0011, SIN-2025-0015, SIN-2025-0016, SIN-2026-0002, SIN-2026-0003, SIN-2026-0007, SIN-2026-0010 |
| `partial_presence` | `registros[].motivo_anulacion` | presente en 1 de 31 objetos | 30 | SIN-2026-0010 |
| `partial_presence` | `registros[].reemplaza_a` | presente en 1 de 31 objetos | 30 | SIN-2026-0011 |
| `format_variants` | `informes[].id` | 2 formas: a-9-9, a-a-9 | 2 | - |
| `missing_values` | `informes[].via_analizada` | valores null, vacios o de relleno | 3 | INF-2026-02, INF-2026-03, INF-RES-01 |
| `partial_presence` | `informes[].reemplaza_a` | presente en 1 de 5 objetos | 4 | INF-2026-01 |
| `duplicate_id` | `registros[].id_parte` | SIN-2025-0007: versiones 1, 2 | 1 | SIN-2025-0007 |
| `summary_mismatch` | `registros[].resumen` | conteos del resumen distintos de los derivados de personas | 1 | SIN-2025-0012 |
| `replacement_link` | `registros[].reemplaza_a` | SIN-2026-0011 reemplaza a SIN-2026-0010 | 1 | SIN-2026-0011 |
| `replacement_link` | `informes[].reemplaza_a` | INF-2026-01 reemplaza a INF-2025-01 | 1 | INF-2026-01 |
| `restricted_classification` | `informes[].clasificacion` | informes con clasificacion distinta de PUBLICO | 1 | INF-RES-01 |
| `pii_in_text` | `informes[].secciones[].texto` | texto libre con cedula: 1, nombre: 1 | 1 | INF-RES-01 |
| `suspicious_instruction` | `registros[].narrativa` | posible prompt injection: ignorar instrucciones, mensaje dirigido al asistente | 1 | SIN-2026-0009 |

## 3. Perfil por campo (JSON original)

Valores mas frecuentes en formato JSON (los textos van entre comillas dobles).

| Ruta | Presentes | Ausentes | Nulos | Vacios | Tipos | Distintos | Valores |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `registros[].id_parte` | 31 | 0 | 0 | 0 | string (31) | 30 | `"SIN-2025-0007"` (2), `"SIN-2025-0001"` (1), `"SIN-2025-0002"` (1), `"SIN-2025-0003"` (1), `"SIN-2025-0004"` (1), ... |
| `registros[].version` | 31 | 0 | 0 | 0 | integer (31) | 2 | `1` (30), `2` (1) |
| `registros[].fecha_actualizacion` | 31 | 0 | 0 | 0 | string (31) | 30 | `"2026-09-02"` (2), `"2025-01-12"` (1), `"2025-02-03"` (1), `"2025-02-22"` (1), `"2025-03-09"` (1), ... |
| `registros[].estado` | 31 | 0 | 0 | 0 | string (31) | 2 | `"ACTIVO"` (30), `"ANULADO"` (1) |
| `registros[].fecha_hora` | 31 | 0 | 0 | 0 | object (7), string (24) | 23 | `"2025-05-01 12:20:00"` (2), `"01/03/2026 00:40"` (1), `"02/09/2026 02:25"` (1), `"03/02/2025 22:15"` (1), `"06/12/2025 11:50"` (1), ... |
| `registros[].fecha_hora.fecha` | 7 | 0 | 0 | 0 | string (7) | 7 | `"02-08-2025"` (1), `"09-03-2025"` (1), `"12-04-2026"` (1), `"15-08-2026"` (1), `"17-05-2025"` (1), ... |
| `registros[].fecha_hora.hora` | 7 | 0 | 0 | 0 | string (7) | 7 | `"03:50"` (1), `"07:20"` (1), `"10:05"` (1), `"13:10"` (1), `"15:25"` (1), ... |
| `registros[].ubicacion` | 31 | 0 | 0 | 0 | object (31) | 0 |  |
| `registros[].ubicacion.provincia` | 31 | 0 | 0 | 0 | string (31) | 21 | `"Guayas"` (3), `"PICHINCHA"` (3), `"Pichincha"` (3), `"Azuay"` (2), `"El Oro"` (2), ... |
| `registros[].ubicacion.canton` | 31 | 0 | 0 | 0 | string (31) | 26 | `"GUAYAQUIL"` (3), `"Ambato"` (2), `"Cuenca"` (2), `"QUITO"` (2), `"AZOGUES"` (1), ... |
| `registros[].ubicacion.parroquia` | 31 | 0 | 0 | 0 | string (31) | 29 | `"El Vecino"` (2), `"SAN RAFAEL"` (2), `"AHUANO"` (1), `"ALLURIQUIN"` (1), `"ATACAMES"` (1), ... |
| `registros[].ubicacion.via` | 31 | 0 | 0 | 0 | string (31) | 25 | `"Panamericana E35 (Troncal de la Sierra)"` (3), `"AUTOPISTA GENERAL RUMINAHUI"` (2), `"AUTOPISTA NARCISA DE JESUS"` (2), `"Av. de las Américas (Cuenca)"` (2), `"PANAMERICANA E35 (TRONCAL DE LA SIERRA)"` (2), ... |
| `registros[].ubicacion.km` | 31 | 0 | 1 | 4 | integer (8), null (1), string (22) | 28 | `""` (4), `"12+000"` (1), `"14+000"` (1), `"15+000"` (1), `"20"` (1), ... |
| `registros[].ubicacion.coordenadas` | 31 | 0 | 2 | 0 | null (2), object (14), string (15) | 15 | `"-2.9121,-79.0059"` (2), `null` (2), `"-0.1807,-78.4638"` (1), `"-0.33,-78.458"` (1), `"-0.9232,-78.6115"` (1), ... |
| `registros[].ubicacion.coordenadas.latitud` | 14 | 0 | 0 | 0 | number (14) | 13 | `-2.174` (2), `-0.1767` (1), `-0.1807` (1), `-0.342` (1), `-0.9978` (1), ... |
| `registros[].ubicacion.coordenadas.longitud` | 14 | 0 | 0 | 0 | number (14) | 14 | `-77.8169` (1), `-78.145` (1), `-78.269` (1), `-78.442` (1), `-78.4638` (1), ... |
| `registros[].tipo_siniestro` | 31 | 0 | 0 | 0 | string (31) | 9 | `"CHOQUE"` (9), `"Choque"` (9), `"Atropello"` (3), `"ATROPELLO"` (2), `"Estrellamiento"` (2), ... |
| `registros[].causa_probable` | 31 | 0 | 0 | 0 | string (31) | 17 | `"EXCESO DE VELOCIDAD"` (5), `"Invadir carril"` (3), `"VELOCIDAD EXCESIVA"` (3), `"Distracción del conductor"` (2), `"MAL ESTADO DE LA VIA"` (2), ... |
| `registros[].condiciones` | 31 | 0 | 0 | 0 | object (31) | 0 |  |
| `registros[].condiciones.clima` | 31 | 0 | 0 | 0 | string (31) | 3 | `"DESPEJADO"` (20), `"LLUVIA"` (7), `"NEBLINA"` (4) |
| `registros[].condiciones.superficie` | 31 | 0 | 0 | 0 | string (31) | 3 | `"SECA"` (20), `"MOJADA"` (7), `"HUMEDA"` (4) |
| `registros[].condiciones.iluminacion` | 31 | 0 | 0 | 0 | string (31) | 4 | `"DIURNA"` (12), `"NOCTURNA_CON_ILUMINACION"` (7), `"AMANECER_ATARDECER"` (6), `"NOCTURNA_SIN_ILUMINACION"` (6) |
| `registros[].danos_materiales` | 31 | 0 | 0 | 0 | integer (8), string (23) | 31 | `"$1,200.00"` (1), `"$1,800.00"` (1), `"$3,900.00"` (1), `"$33,800.00"` (1), `"$4,100.00"` (1), ... |
| `registros[].resumen` | 31 | 0 | 0 | 0 | object (31) | 0 |  |
| `registros[].resumen.fallecidos` | 31 | 0 | 0 | 0 | integer (31) | 3 | `0` (15), `1` (13), `2` (3) |
| `registros[].resumen.heridos` | 31 | 0 | 0 | 0 | integer (31) | 5 | `1` (12), `2` (8), `0` (5), `3` (5), `4` (1) |
| `registros[].resumen.ilesos` | 31 | 0 | 0 | 0 | integer (31) | 2 | `1` (16), `0` (15) |
| `registros[].vehiculos` | 31 | 0 | 0 | 0 | array (31) | 0 |  |
| `registros[].vehiculos[].placa` | 50 | 0 | 0 | 0 | string (50) | 49 | (oculto: dato personal) |
| `registros[].vehiculos[].tipo_vehiculo` | 50 | 0 | 0 | 0 | string (50) | 16 | `"AUTOMOVIL"` (11), `"Automóvil"` (6), `"Camioneta"` (5), `"MOTOCICLETA"` (4), `"BUS"` (3), ... |
| `registros[].vehiculos[].marca_modelo` | 26 | 24 | 0 | 0 | string (26) | 21 | `"CHEVROLET AVEO"` (2), `"CHEVROLET D-MAX"` (2), `"HINO AK"` (2), `"KIA SPORTAGE"` (2), `"TOYOTA HILUX"` (2), ... |
| `registros[].vehiculos[].anio` | 50 | 0 | 0 | 0 | integer (32), string (18) | 19 | `2019` (6), `2020` (6), `"2018"` (4), `2017` (4), `2018` (4), ... |
| `registros[].vehiculos[].servicio` | 50 | 0 | 0 | 0 | string (50) | 6 | `"PARTICULAR"` (18), `"particular"` (16), `"carga"` (6), `"público"` (4), `"CARGA"` (3), ... |
| `registros[].vehiculos[].marca` | 24 | 26 | 0 | 0 | string (24) | 10 | `"Chevrolet"` (6), `"Hino"` (3), `"Mercedes-Benz"` (3), `"Honda"` (2), `"Hyundai"` (2), ... |
| `registros[].vehiculos[].modelo` | 24 | 26 | 0 | 0 | string (24) | 18 | `"OF"` (3), `"Sail"` (3), `"Accent"` (2), `"BT-50"` (2), `"500"` (1), ... |
| `registros[].personas` | 31 | 0 | 0 | 0 | array (31) | 0 |  |
| `registros[].personas[].rol` | 81 | 0 | 0 | 0 | string (81) | 5 | `"CONDUCTOR"` (27), `"conductor"` (23), `"PASAJERO"` (13), `"pasajero"` (13), `"peatón"` (5) |
| `registros[].personas[].edad` | 81 | 0 | 0 | 0 | integer (61), string (20) | 55 | `29` (4), `34` (4), `31` (3), `33` (3), `44` (3), ... |
| `registros[].personas[].sexo` | 81 | 0 | 0 | 0 | string (81) | 6 | `"Hombre"` (21), `"M"` (21), `"MASCULINO"` (19), `"FEMENINO"` (8), `"F"` (6), ... |
| `registros[].personas[].condicion` | 81 | 0 | 0 | 0 | string (81) | 8 | `"Herido leve"` (19), `"FALLECIDO"` (13), `"HERIDO LEVE"` (13), `"Ileso"` (11), `"HERIDO GRAVE"` (10), ... |
| `registros[].personas[].alcohol_gl` | 81 | 0 | 9 | 13 | null (9), number (14), string (58) | 13 | `"0,0"` (15), `""` (13), `"0.0"` (13), `"N/D"` (12), `0.0` (12), ... |
| `registros[].personas[].proteccion` | 81 | 0 | 3 | 1 | null (3), string (78) | 12 | `"CINTURON"` (23), `"SI - CINTURON"` (18), `"Cinturón de seguridad"` (16), `"N/A"` (6), `"SI - CASCO"` (4), ... |
| `registros[].personas[].nombre` | 81 | 0 | 0 | 0 | string (81) | 61 | (oculto: dato personal) |
| `registros[].personas[].cedula` | 81 | 0 | 0 | 0 | string (81) | 80 | (oculto: dato personal) |
| `registros[].personas[].placa_vehiculo` | 81 | 0 | 5 | 0 | null (5), string (76) | 50 | (oculto: dato personal) |
| `registros[].personas[].dias_hasta_deceso` | 1 | 80 | 0 | 0 | integer (1) | 1 | `6` (1) |
| `registros[].narrativa` | 31 | 0 | 0 | 0 | string (31) | 30 | (texto libre: 139 a 321 caracteres) |
| `registros[].fuente` | 31 | 0 | 0 | 0 | string (31) | 1 | `"Parte policial (ficticio)"` (31) |
| `registros[].motivo_anulacion` | 1 | 30 | 0 | 0 | string (1) | 1 | `"Ubicación errónea (cantón incorrecto) y parte incompleto"` (1) |
| `registros[].reemplaza_a` | 1 | 30 | 0 | 0 | string (1) | 1 | `"SIN-2026-0010"` (1) |
| `informes[].id` | 5 | 0 | 0 | 0 | string (5) | 5 | `"INF-2025-01"` (1), `"INF-2026-01"` (1), `"INF-2026-02"` (1), `"INF-2026-03"` (1), `"INF-RES-01"` (1) |
| `informes[].titulo` | 5 | 0 | 0 | 0 | string (5) | 5 | `"Diccionario de datos y definiciones de siniestros"` (1), `"Informe de siniestralidad del corredor E35 (datos 2025). Actualiza el informe anterior"` (1), `"Informe de siniestralidad del corredor E35 Ambato–Riobamba (datos 2024)"` (1), `"Nota técnica: siniestros con motocicletas"` (1), `"Nómina reservada de víctimas fatales (CONFIDENCIAL)"` (1) |
| `informes[].fecha` | 5 | 0 | 0 | 0 | string (5) | 5 | `"10/02/2025"` (1), `"12/02/2026"` (1), `"15/01/2026"` (1), `"20/07/2026"` (1), `"30/03/2026"` (1) |
| `informes[].estado` | 5 | 0 | 0 | 0 | string (5) | 2 | `"VIGENTE"` (4), `"REEMPLAZADO"` (1) |
| `informes[].clasificacion` | 5 | 0 | 0 | 0 | string (5) | 2 | `"PUBLICO"` (4), `"RESERVADO"` (1) |
| `informes[].via_analizada` | 5 | 0 | 3 | 0 | null (3), string (2) | 2 | `null` (3), `"PANAMERICANA E35 (TRONCAL DE LA SIERRA)"` (2) |
| `informes[].secciones` | 5 | 0 | 0 | 0 | array (5) | 0 |  |
| `informes[].secciones[].titulo` | 10 | 0 | 0 | 0 | string (10) | 7 | `"Recomendaciones"` (3), `"Resumen"` (2), `"Campos y calidad de datos"` (1), `"Gravedad de las lesiones"` (1), `"Hallazgos"` (1), ... |
| `informes[].secciones[].texto` | 10 | 0 | 0 | 0 | string (10) | 10 | (texto libre: 116 a 450 caracteres) |
| `informes[].reemplaza_a` | 1 | 4 | 0 | 0 | string (1) | 1 | `"INF-2025-01"` (1) |

## 4. Resultado de la normalizacion

Conteos sobre los 31 registros del archivo, antes de quedarse con una version por siniestro (R01) y sin excluir anulados (R02). Por eso pueden diferir de los valores de control de la Etapa 2, que cuentan siniestros vigentes.

### 4.1 Valores categoricos

| Campo | Escrituras originales | Valores canonicos | Regla | Distribucion |
| --- | --- | --- | --- | --- |
| `registros[].estado` | 2 | 2 | 3.1 | `vigente` (30), `anulado` (1) |
| `registros[].tipo_siniestro` | 9 | 5 | 3.1 | `choque` (18), `atropello` (5), `perdida_de_pista` (3), `volcamiento` (3), `estrellamiento` (2) |
| `registros[].causa_probable` | 17 | 10 | 3.1 | `exceso_de_velocidad` (9), `peaton_en_la_via` (4), `conducir_bajo_efectos_del_alcohol` (3), `distraccion_del_conductor` (3), `invadir_carril` (3), `adelantamiento_indebido` (2), `mal_estado_de_la_via` (2), `no_respetar_semaforo` (2), `somnolencia` (2), `fallo_mecanico` (1) |
| `registros[].condiciones.clima` | 3 | 3 | 3.1 | `despejado` (20), `lluvia` (7), `neblina` (4) |
| `registros[].condiciones.superficie` | 3 | 3 | 3.1 | `seca` (20), `mojada` (7), `humeda` (4) |
| `registros[].condiciones.iluminacion` | 4 | 4 | 3.1 | `diurna` (12), `nocturna_con_iluminacion` (7), `amanecer_atardecer` (6), `nocturna_sin_iluminacion` (6) |
| `registros[].ubicacion.provincia` | 21 | 17 | 3.2 | `Pichincha` (6), `Guayas` (5), `Tungurahua` (3), `Azuay` (2), `El Oro` (2), `Manabi` (2), `Canar` (1), `Chimborazo` (1), `Cotopaxi` (1), `Esmeraldas` (1), `Imbabura` (1), `Loja` (1), `Los Rios` (1), `Napo` (1), `Santa Elena` (1), `Santo Domingo de los Tsachilas` (1), `Sucumbios` (1) |
| `registros[].ubicacion.canton` | 26 | 22 | N02 | `Guayaquil` (4), `Quito` (3), `Ambato` (2), `Cuenca` (2), `Machala` (2), `Ruminahui` (2), `Azogues` (1), `Banos de Agua Santa` (1), `Cayambe` (1), `Duran` (1), `Esmeraldas` (1), `Lago Agrio` (1), `Latacunga` (1), `Loja` (1), `Manta` (1), `Otavalo` (1), `Portoviejo` (1), `Quevedo` (1), `Riobamba` (1), `Santa Elena` (1), `Santo Domingo` (1), `Tena` (1) |
| `registros[].ubicacion.parroquia` | 29 | 29 | N02 | `El Vecino` (2), `San Rafael` (2), `Ahuano` (1), `Alluriquin` (1), `Atacames` (1), `Ayora` (1), `Ballenita` (1), `Borrero` (1), `Chongon` (1), `Conocoto` (1), `Cotocollao` (1), `Crucita` (1), `El Cambio` (1), `Eloy Alfaro` (1), `Febres Cordero` (1), `Guaytacama` (1), `Izamba` (1), `La Mariscal` (1), `Lizarzaburu` (1), `Malacatos` (1), `Nueva Loja` (1), `Pasa` (1), `Pascuales` (1), `Puerto Bolivar` (1), `San Camilo` (1), `San Mateo` (1), `Sangolqui` (1), `Tarqui` (1), `Ulba` (1) |
| `registros[].ubicacion.via` | 25 | 20 | N03 | `Panamericana E35 (Troncal de la Sierra)` (6), `Autopista General Ruminahui` (3), `Autopista Narcisa de Jesus` (2), `Av. Simon Bolivar (Quito)` (2), `Av. de las Americas (Cuenca)` (2), `Troncal Amazonica E45` (2), `Av. Francisco de Orellana (Guayaquil)` (1), `E15` (1), `Via Banos-Puyo` (1), `Via Cuenca-Azogues` (1), `Via Duran-Yaguachi` (1), `Via Esmeraldas-Atacames` (1), `Via Guayaquil-Machala` (1), `Via Loja-Catamayo` (1), `Via Machala-Pasaje` (1), `Via Manta-Portoviejo` (1), `Via Portoviejo-Crucita` (1), `Via Quevedo-Santo Domingo` (1), `Via Santo Domingo-Quito` (1), `Via a la Costa (Guayaquil)` (1) |
| `registros[].vehiculos[].tipo_vehiculo` | 16 | 10 | 3.1 | `automovil` (17), `camioneta` (8), `motocicleta` (7), `bus` (5), `camion` (3), `camion_pesado` (3), `camion_liviano` (2), `suv` (2), `taxi` (2), `trailer` (1) |
| `registros[].vehiculos[].servicio` | 6 | 3 | 3.1 | `particular` (34), `carga` (9), `publico` (7) |
| `registros[].vehiculos[].marca` | 21 | 13 | N11 | `CHEVROLET` (14), `HINO` (6), `KIA` (6), `HYUNDAI` (4), `TOYOTA` (4), `HONDA` (3), `MERCEDES-BENZ` (3), `YAMAHA` (3), `MAZDA` (2), `NISSAN` (2), `KENWORTH` (1), `SUZUKI` (1), `VOLVO` (1) |
| `registros[].personas[].rol` | 5 | 3 | 3.1 | `conductor` (50), `pasajero` (26), `peaton` (5) |
| `registros[].personas[].condicion` | 8 | 4 | 3.1 | `herido_leve` (32), `fallecido` (19), `ileso` (16), `herido_grave` (14) |
| `registros[].personas[].sexo` | 6 | 2 | 3.1 | `M` (61), `F` (20) |
| `registros[].personas[].proteccion` | 12 | 5 | 3.1 | `cinturon` (57), `no_registrado` (8), `casco` (7), `no_aplica` (7), `ninguna` (2) |
| `informes[].estado` | 2 | 2 | 3.1 | `vigente` (3), `reemplazado` (1) |

### 4.2 Valores numericos

| Campo | Con dato | Null | Minimo | Maximo | Regla |
| --- | --- | --- | --- | --- | --- |
| `registros[].danos_materiales` | 31 | 0 | 1200 | 41000 | N06 |
| `registros[].ubicacion.km` | 26 | 5 | 3 | 205 | N07 |
| `registros[].ubicacion.coordenadas (latitud)` | 29 | 2 | -3.9851 | 0.9632 | N08 |
| `registros[].ubicacion.coordenadas (longitud)` | 29 | 2 | -80.867 | -76.895 | N08 |
| `registros[].vehiculos[].anio` | 50 | 0 | 2012 | 2023 | N10 |
| `registros[].personas[].edad` | 81 | 0 | 7 | 71 | N10 |
| `registros[].personas[].alcohol_gl` | 47 | 34 | 0 | 1.6 | N09 |

### 4.3 Fechas

| Campo | Valores | Minimo | Maximo | Regla |
| --- | --- | --- | --- | --- |
| `registros[].fecha_hora` | 31 | 2025-01-12T05:40:00-05:00 | 2026-09-02T02:25:00-05:00 | N04 |
| `registros[].fecha_actualizacion` | 31 | 2025-01-12 | 2026-09-02 | N05 |
| `informes[].fecha` | 4 | 2025-02-10 | 2026-07-20 | N05 |
