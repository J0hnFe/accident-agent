# Analisis de los datos de entrada

- **Archivo:** `data/siniestros_raw.json` (77 189 bytes), sin modificar.
- **SHA-256:** `77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280` (`data/siniestros_raw.json.sha256`).
- **Fecha del analisis:** 2026-11-15.
- **Fuente de las cifras:** perfilado reproducible de la tarea 1.1, `uv run python -m accident_agent.ingestion.quality_report`; salida completa en `docs/evidencias/1.1_perfilado.json`.
- **Significado de los campos:** tomado del informe INF-2026-02 "Diccionario de datos y definiciones de siniestros", incluido en el propio JSON. Cuando el diccionario no define un campo, el significado se marca como *inferido* a partir de los valores.

Los valores entre comillas invertidas son textos originales del JSON y se citan tal cual, con sus tildes (excepcion de `CLAUDE.md`). Los valores de nombre, cedula y placa no se citan nunca.

## Indice

1. Vista general
2. `metadata`
3. `registros`: campos de primer nivel
4. `registros[].ubicacion`
5. `registros[].condiciones`
6. `registros[].resumen`
7. `registros[].vehiculos[]`
8. `registros[].personas[]`
9. `informes`
10. Relaciones e integridad entre campos
11. Datos personales
12. Diferencias con el diccionario INF-2026-02
13. Resumen de problemas detectados

## 1. Vista general

El JSON es un objeto con tres claves:

| Clave | Tipo | Contenido |
| --- | --- | --- |
| `metadata` | objeto | Descripcion del extracto: fuente, fecha, zona horaria y formato de fechas |
| `registros` | lista de 31 objetos | Partes de siniestros de transito, con objetos y listas anidados |
| `informes` | lista de 5 objetos | Documentos de analisis con secciones de texto libre |

```
registros[]                      31 (30 ids distintos)
  ubicacion {}                   provincia, canton, parroquia, via, km, coordenadas
  condiciones {}                 clima, superficie, iluminacion
  resumen {}                     fallecidos, heridos, ilesos
  vehiculos[]                    50 en total (1 a 3 por registro)
  personas[]                     81 en total (1 a 7 por registro)
informes[]                       5
  secciones[]                    10 en total
```

- **Registros por anio del id:** 20 de 2025 y 11 de 2026. El anio del id coincide siempre con el anio de `fecha_hora`.
- **Vehiculos por registro:** 13 registros con 1, 17 con 2 y 1 con 3.
- **Personas por registro:** 3 registros con 1, 13 con 2, 11 con 3, 3 con 4 y 1 con 7.
- **Orden:** los registros no estan ordenados por id; la version 2 de SIN-2025-0007 aparece en la posicion 6 y la version 1 en la ultima (posicion 30).

## 2. `metadata`

| Campo | Valor | Uso en la solucion |
| --- | --- | --- |
| `fuente` | `Extracto ficticio de partes de siniestros de tránsito (ANT / ECU 911) - SOLO PARA PRUEBA TÉCNICA` | Se cita como fuente en los informes generados |
| `generado` | `2026-11-09` | Fecha del extracto |
| `version_esquema` | `1.0` | Informativo |
| `zona_horaria` | `America/Guayaquil (UTC-05:00)` | Zona por defecto de la solucion y de las fechas sin desfase |
| `formato_fechas_texto` | `dd/mm/aaaa (día primero)` | Regla para interpretar las fechas de texto ambiguas |
| `total_registros` | `31` | Coincide con la longitud de `registros` (31) |
| `aviso` | `Todos los datos, nombres, cédulas y placas son inventados.` | Los datos personales son ficticios, pero se tratan como reales (seccion 11) |

## 3. `registros`: campos de primer nivel

| Campo | Tipos observados | Presencia | Significado | Observaciones |
| --- | --- | --- | --- | --- |
| `id_parte` | texto (31) | 31 de 31 | Identificador del parte, patron `SIN-AAAA-NNNN` | 30 valores distintos: SIN-2025-0007 aparece dos veces (versiones 1 y 2) |
| `version` | entero (31) | 31 de 31 | Version del parte (*inferido*) | 30 registros con `1` y uno con `2` |
| `fecha_actualizacion` | texto (31) | 31 de 31 | Fecha de la ultima actualizacion del parte (*inferido*) | Formato unico `AAAA-MM-DD` |
| `estado` | texto (31) | 31 de 31 | Estado del parte; el diccionario lo llama `estado_registro` | `ACTIVO` (30) y `ANULADO` (1, SIN-2026-0010) |
| `fecha_hora` | texto (24), objeto (7) | 31 de 31 | Fecha y hora del siniestro | 4 formatos (seccion 3.1) |
| `ubicacion` | objeto (31) | 31 de 31 | Lugar del siniestro | Seccion 4 |
| `tipo_siniestro` | texto (31) | 31 de 31 | Tipo segun el diccionario: choque, estrellamiento, atropello, volcamiento, perdida de pista | 9 escrituras para 5 tipos (`CHOQUE` / `Choque`, `Pérdida de pista` / `PERDIDA DE PISTA`) |
| `causa_probable` | texto (31) | 31 de 31 | Causa probable registrada en el parte (*inferido*) | 17 escrituras; mezcla mayusculas y sinonimos (`EXCESO DE VELOCIDAD` / `VELOCIDAD EXCESIVA`) |
| `condiciones` | objeto (31) | 31 de 31 | Condiciones del entorno | Seccion 5 |
| `danos_materiales` | entero (8), texto (23) | 31 de 31 | Monto de los danos materiales en USD (*inferido* del sufijo `USD` y del simbolo `$`) | 4 representaciones (seccion 3.2) |
| `resumen` | objeto (31) | 31 de 31 | Conteo de victimas declarado en el parte | Seccion 6 |
| `vehiculos` | lista (31) | 31 de 31 | Vehiculos involucrados | Seccion 7 |
| `personas` | lista (31) | 31 de 31 | Personas involucradas | Seccion 8 |
| `narrativa` | texto (31) | 31 de 31 | Relato libre del siniestro | 139 a 321 caracteres; 10 con espacios o saltos de linea sobrantes; SIN-2026-0009 contiene una prompt injection |
| `fuente` | texto (31) | 31 de 31 | Origen del parte | Valor unico `Parte policial (ficticio)` |
| `motivo_anulacion` | texto (1) | 1 de 31 | Motivo de la anulacion | Solo en SIN-2026-0010: `Ubicación errónea (cantón incorrecto) y parte incompleto` |
| `reemplaza_a` | texto (1) | 1 de 31 | Id del parte al que reemplaza | Solo en SIN-2026-0011, que reemplaza a SIN-2026-0010 |

### 3.1 Formatos de `fecha_hora`

| Forma | Ejemplo | Registros | Desfase horario |
| --- | --- | --- | --- |
| ISO 8601 con desfase | `2025-01-12T05:40:00-05:00` | 8 | Explicito (`-05:00`) |
| Texto dia primero | `03/02/2025 22:15` | 8 | Ninguno; segun la metadata es `dd/mm/aaaa` |
| Texto ISO sin desfase | `2025-02-22 14:05:00` | 8 | Ninguno |
| Objeto `{fecha, hora}` | `{"fecha": "09-03-2025", "hora": "03:50"}` | 7 | Ninguno; la fecha usa guiones y dia primero |

Los formatos sin desfase se interpretan en la zona de la metadata (America/Guayaquil, UTC-05:00).

### 3.2 Representaciones de `danos_materiales`

| Forma | Ejemplo | Registros | Separador decimal |
| --- | --- | --- | --- |
| Entero JSON | `18500` | 8 | No aplica |
| Texto con digitos | `"3200"` | 8 | No aplica |
| Formato de EE. UU. con `$` | `"$6,400.00"` | 8 | Punto; coma de miles |
| Formato europeo con `USD` | `"21.000,00 USD"` | 7 | Coma; punto de miles |

## 4. `registros[].ubicacion`

| Campo | Tipos observados | Significado | Observaciones |
| --- | --- | --- | --- |
| `provincia` | texto (31) | Provincia del Ecuador | 21 escrituras; mezcla mayusculas y minusculas (`PICHINCHA` / `Pichincha`) y omite la enie (`CANAR`) |
| `canton` | texto (31) | Canton dentro de la provincia | 26 escrituras; mezcla mayusculas y tildes (`RUMINAHUI` / `Rumiñahui`, `Durán`) |
| `parroquia` | texto (31) | Parroquia dentro del canton | 29 escrituras; mezcla mayusculas (`SAN RAFAEL`, `El Vecino`) |
| `via` | texto (31) | Via donde ocurrio el siniestro | 25 escrituras; alias de una misma via (`E35`, `Panamericana E35 (Troncal de la Sierra)`, `PANAMERICANA E35 (TRONCAL DE LA SIERRA)`) y vias urbanas con ciudad entre parentesis |
| `km` | entero (8), texto (22), null (1) | Abscisa o kilometro de la via (*inferido*) | 4 formas de texto: digitos (`"4"`, 7), abscisa (`"12+000"`, 7), prefijo (`"Km 11"`, 4) y vacio (`""`, 4); ademas 1 null |
| `coordenadas` | texto (15), objeto (14), null (2) | Ubicacion geografica; el diccionario las define como *referenciales* | Texto `"-1.2497,-78.6237"` (latitud, longitud) u objeto `{latitud, longitud}` con numeros; null en SIN-2025-0006 y SIN-2025-0019 |

## 5. `registros[].condiciones`

Los tres campos son texto, estan en los 31 registros y ya vienen normalizados en mayusculas y sin tildes.

| Campo | Significado | Valores (registros) |
| --- | --- | --- |
| `clima` | Clima al momento del siniestro | `DESPEJADO` (20), `LLUVIA` (7), `NEBLINA` (4) |
| `superficie` | Estado de la calzada | `SECA` (20), `MOJADA` (7), `HUMEDA` (4) |
| `iluminacion` | Condicion de luz | `DIURNA` (12), `NOCTURNA_CON_ILUMINACION` (7), `AMANECER_ATARDECER` (6), `NOCTURNA_SIN_ILUMINACION` (6) |

## 6. `registros[].resumen`

| Campo | Tipo | Significado | Valores (registros) |
| --- | --- | --- | --- |
| `fallecidos` | entero | Fallecidos declarados en el parte; el diccionario cuenta a quien muere en el lugar o hasta 30 dias despues | 0 (15), 1 (13), 2 (3) |
| `heridos` | entero | Heridos declarados (graves y leves) | 0 (5), 1 (12), 2 (8), 3 (5), 4 (1) |
| `ilesos` | entero | Ilesos declarados | 0 (15), 1 (16) |

Los tres campos son enteros en los 31 registros. El resumen es redundante con la lista `personas`: en SIN-2025-0012 declara 3 heridos y la lista solo tiene 2.

## 7. `registros[].vehiculos[]`

50 vehiculos en total.

| Campo | Tipos observados | Presencia | Significado | Observaciones |
| --- | --- | --- | --- | --- |
| `placa` | texto (50) | 50 de 50 | Placa del vehiculo | **Dato personal**; 49 distintas (la repetida es de SIN-2025-0007 v1 y v2) |
| `tipo_vehiculo` | texto (50) | 50 de 50 | Tipo de vehiculo | 16 escrituras; mayusculas y tildes mezcladas (`AUTOMOVIL` / `Automóvil`, `CAMION PESADO`, `Camión liviano`) |
| `marca_modelo` | texto (26) | 26 de 50 | Marca y modelo en un solo texto | Excluyente con `marca` y `modelo` |
| `marca` | texto (24) | 24 de 50 | Marca | Escrita en tipo titulo (`Chevrolet`, `Mercedes-Benz`) |
| `modelo` | texto (24) | 24 de 50 | Modelo | Incluye modelos con digitos (`BT-50`, `CB 125`, `500`) |
| `anio` | entero (32), texto (18) | 50 de 50 | Anio del modelo del vehiculo (*inferido*) | El texto siempre contiene solo digitos (`"2018"`) |
| `servicio` | texto (50) | 50 de 50 | Tipo de servicio del vehiculo | 6 escrituras para 3 valores: `PARTICULAR` / `particular`, `CARGA` / `carga`, `PUBLICO` / `público` |

Cada vehiculo trae `marca_modelo` (26) o el par `marca` y `modelo` (24), nunca ambos.

## 8. `registros[].personas[]`

81 personas en total.

| Campo | Tipos observados | Presencia | Significado | Observaciones |
| --- | --- | --- | --- | --- |
| `rol` | texto (81) | 81 de 81 | Rol en el siniestro | 5 escrituras para 3 roles: `CONDUCTOR` / `conductor`, `PASAJERO` / `pasajero`, `peatón` |
| `edad` | entero (61), texto (20) | 81 de 81 | Edad en anios | El texto siempre contiene solo digitos (`"39"`) |
| `sexo` | texto (81) | 81 de 81 | Sexo | 6 escrituras para 2 valores: `M`, `MASCULINO`, `Hombre`, `F`, `FEMENINO`, `Mujer` |
| `condicion` | texto (81) | 81 de 81 | Gravedad segun el diccionario: fallecido, herido grave, herido leve, ileso | 8 escrituras para 4 valores (`HERIDO LEVE` / `Herido leve`) |
| `alcohol_gl` | texto (58), numero (14), null (9) | 81 de 81 | Alcoholemia en g/L; el diccionario indica que queda vacia si no se hizo la prueba | Decimales con coma (18 textos, p. ej. `"0,0"` y `"1,6"`) o con punto (15 textos, p. ej. `"0.0"` y `"1.3"`), ademas de 14 numeros JSON; sin dato como `""` (13), `"N/D"` (12) o null (9) |
| `proteccion` | texto (78), null (3) | 81 de 81 | Elemento de proteccion usado; el diccionario lo llama `uso_proteccion` | 12 escrituras para los 5 valores del diccionario (`CINTURON`, `SI - CINTURON`, `Cinturón de seguridad`, `SI - CASCO`, `N/A`, `NO APLICA`, `SIN DATO`, `NINGUNO`, `NO`, `""`, null...) |
| `nombre` | texto (81) | 81 de 81 | Nombre completo | **Dato personal**; 61 distintos: 17 nombres se repiten con cedulas distintas, asi que el nombre no identifica a una persona |
| `cedula` | texto (81) | 81 de 81 | Cedula de identidad | **Dato personal**; 80 distintas (la repetida es de SIN-2025-0007 v1 y v2) |
| `placa_vehiculo` | texto (76), null (5) | 81 de 81 | Placa del vehiculo en el que iba la persona | **Dato personal**; null en los 5 peatones |
| `dias_hasta_deceso` | entero (1) | 1 de 81 | Dias entre el siniestro y el fallecimiento | Solo en SIN-2026-0011 (valor 6): fallecimiento diferido, dentro de los 30 dias del diccionario |

## 9. `informes`

Cada informe tiene `id`, `titulo`, `fecha` (`dd/mm/aaaa`, formato unico), `estado`, `clasificacion`, `via_analizada` (texto o null) y una lista `secciones` de objetos `{titulo, texto}`. Un informe agrega `reemplaza_a`.

| Id | Fecha | Estado | Clasificacion | Via analizada | Secciones | Contenido |
| --- | --- | --- | --- | --- | --- | --- |
| INF-2025-01 | 10/02/2025 | `REEMPLAZADO` | `PUBLICO` | E35 | Resumen, Recomendaciones | Siniestralidad 2024 del corredor E35 Ambato-Riobamba; causa principal: exceso de velocidad |
| INF-2026-01 | 12/02/2026 | `VIGENTE` | `PUBLICO` | E35 | Resumen, Recomendaciones | Datos 2025 del corredor E35; la neblina y la invasion de carril desplazan al exceso de velocidad. `reemplaza_a`: INF-2025-01 |
| INF-2026-02 | 15/01/2026 | `VIGENTE` | `PUBLICO` | null | Tipos de siniestro, Gravedad de las lesiones, Campos y calidad de datos | Diccionario de datos: definiciones de tipos, gravedad y catalogos |
| INF-2026-03 | 20/07/2026 | `VIGENTE` | `PUBLICO` | null | Hallazgos, Recomendaciones | Siniestros con motocicletas: 7 de 29 vigentes |
| INF-RES-01 | 30/03/2026 | `VIGENTE` | `RESERVADO` | null | 1 seccion | Nomina de victimas fatales. Contiene nombres y cedulas; su texto no se cita ni se ingesta |

- Los textos de las secciones miden de 116 a 450 caracteres.
- `via_analizada` usa la escritura en mayusculas `PANAMERICANA E35 (TRONCAL DE LA SIERRA)`, una de las variantes de `registros[].ubicacion.via`.
- El id de INF-RES-01 no sigue el patron `INF-AAAA-NN` de los demas.

## 10. Relaciones e integridad entre campos

| Relacion | Resultado |
| --- | --- |
| `personas[].placa_vehiculo` -> `vehiculos[].placa` del mismo registro | Las 76 placas no nulas apuntan a un vehiculo del mismo registro |
| Vehiculos con al menos un ocupante listado | Los 50 vehiculos tienen al menos una persona con su placa |
| `rol` peaton y `placa_vehiculo` null | Coinciden: 5 peatones, todos sin vehiculo |
| `registros[].reemplaza_a` | SIN-2026-0011 -> SIN-2026-0010; el destino existe y esta `ANULADO`. Ambos tienen `fecha_actualizacion` 2026-09-02 |
| `informes[].reemplaza_a` | INF-2026-01 -> INF-2025-01; el destino existe y esta `REEMPLAZADO` |
| Versiones de SIN-2025-0007 | v1 (`fecha_actualizacion` 2025-05-02, danos `$3,900.00`) y v2 (2025-05-06, `$4,100.00`); misma narrativa, una persona y un vehiculo en ambas. La version vigente se elige por `version`, no por posicion, porque v1 esta despues en la lista |
| `resumen` frente a `personas` | Coinciden en 30 de 31 registros; SIN-2025-0012 declara 3 heridos y lista 2 |
| Anio del id frente a `fecha_hora` | Coinciden en los 31 registros |
| `metadata.total_registros` | 31, igual a la longitud de `registros` |

## 11. Datos personales

- **Campos con datos personales:** `personas[].nombre`, `personas[].cedula`, `personas[].placa_vehiculo` y `vehiculos[].placa`. La metadata declara que son inventados, pero se tratan como reales.
- **Textos libres:** el perfilado no encontro nombres, cedulas ni placas del dataset dentro de las 31 narrativas. Si los encontro en el texto de INF-RES-01 (nombre y cedula).
- **Edad y sexo** no identifican por si solos a una persona, pero junto con el lugar y la fecha podrian hacerlo. La decision sobre su exposicion es de la tarea 1.5.
- La politica completa (que se carga, que se muestra y como se trata INF-RES-01 y la prompt injection) es la tarea 1.5.

## 12. Diferencias con el diccionario INF-2026-02

| Diccionario | JSON | Consecuencia |
| --- | --- | --- |
| `estado_registro`: `vigente` o `anulado` | `estado`: `ACTIVO` o `ANULADO` | `ACTIVO` equivale a vigente; los anulados no cuentan en estadisticas |
| `uso_proteccion`: `cinturón`, `casco`, `ninguna`, `no_aplica`, `no_registrado` | `proteccion` con 12 escrituras | Las 12 escrituras se mapean a esos 5 valores (tarea 1.6) |
| Alcoholemia "vacia si no se realizo la prueba" | `""`, `"N/D"` y null | Los tres equivalen a sin dato |
| Fallecido: muere en el lugar o hasta 30 dias despues | `condicion` y `dias_hasta_deceso` | SIN-2026-0011 (6 dias) cuenta como fallecido |
| Coordenadas "referenciales" | Texto u objeto | Se cargan como referencia, sin calculos de precision |

## 13. Resumen de problemas detectados

El perfilado reporta 42 anomalias. El catalogo completo con la decision de cada una es la tarea 1.3 (seccion 4 del plan); aqui solo se agrupan:

| Tipo | Campos afectados |
| --- | --- |
| Tipos mezclados | `fecha_hora`, `km`, `coordenadas`, `danos_materiales`, `anio`, `edad`, `alcohol_gl` |
| Varios formatos | `fecha_hora` (4), `danos_materiales` (4), `km` (4 de texto), `alcohol_gl` (separador decimal), `coordenadas` (texto u objeto) |
| Mayusculas, tildes y sinonimos | `provincia`, `canton`, `parroquia`, `via`, `tipo_siniestro`, `causa_probable`, `tipo_vehiculo`, `servicio`, `rol`, `sexo`, `condicion`, `proteccion` |
| Valores faltantes o de relleno | `km` (5), `coordenadas` (2), `alcohol_gl` (34), `proteccion` (14), `placa_vehiculo` (5, peatones) |
| Estructura variable | `marca_modelo` frente a `marca` y `modelo`; claves presentes solo en un registro (`motivo_anulacion`, `reemplaza_a`, `dias_hasta_deceso`) |
| Espacios sobrantes | 10 narrativas |
| Duplicados y versiones | SIN-2025-0007 v1 y v2, con la v1 despues de la v2 en la lista |
| Inconsistencias | Resumen de SIN-2025-0012; nombres de campo distintos a los del diccionario |
| Trazabilidad | SIN-2026-0010 anulado y reemplazado; INF-2025-01 reemplazado |
| Seguridad y privacidad | INF-RES-01 reservado con PII; prompt injection en la narrativa de SIN-2026-0009 |
