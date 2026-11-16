# Reglas de normalizacion

- **Tarea:** 1.4 del plan. Convierte las decisiones de `docs/datos/catalogo_anomalias.md` (ids `A01`...) en reglas concretas.
- **Fecha:** 2026-11-15.
- **Origen de los ejemplos:** todas las entradas son valores reales de `data/siniestros_raw.json`. Las salidas se obtuvieron ejecutando un prototipo de estas reglas sobre los 31 registros (sin errores). Los casos sin ejemplo en los datos se marcan como *defensivos*.
- **Uso:**
  - especificacion de `normalizers.py` (tarea 1.7): cada fila de ejemplo se convierte en un caso de prueba parametrizado;
  - especificacion de los catalogos de `domain/catalogs.py` (tarea 1.6);
  - especificacion de las reglas por registro de `pipeline.py` (tarea 2.2).

Los valores entre comillas invertidas son textos originales del JSON y conservan su ortografia (excepcion de datos en `CLAUDE.md`). Nombres, cedulas, placas y narrativas no se citan.

## Indice

1. Principios
2. Reglas de valor (N01 a N12)
3. Catalogos de valores categoricos
4. Reglas por registro (R01 a R06)
5. Correspondencia de campos
6. Errores de normalizacion
7. Reutilizacion fuera de la carga

## 1. Principios

1. **Funciones puras:** cada regla recibe un valor original y devuelve un valor canonico o lanza `NormalizationError`. No leen archivos, no usan el reloj ni dependen del orden de los registros.
2. **Formatos explicitos:** solo se aceptan los formatos listados. No se usa deteccion automatica de formatos (por ejemplo `dateutil.parser`), que podria leer `03/02/2025` como 2 de marzo.
3. **Falla ante lo desconocido:** un valor que ninguna regla reconoce detiene la carga con un error que dice registro, campo y motivo. Nada entra como valor nuevo silencioso.
4. **Faltante es null:** `""`, `N/D`, `SIN DATO` y null significan "sin dato" y se guardan como null, salvo en `proteccion`, donde el diccionario tiene un valor propio (`no_registrado`).
5. **Valores canonicos en ASCII y en espanol:** codigos en minusculas con guion bajo (`herido_leve`); nombres propios con mayuscula inicial (`Canar`, `Ruminahui`). Los textos libres (narrativas, secciones de informes) conservan su ortografia original.
6. **El original no cambia:** las reglas trabajan sobre la copia en memoria; el SHA-256 de `data/siniestros_raw.json` se verifica antes y despues de la carga.
7. **Defensas comunes** (agregadas en la tarea 1.7, sin ejemplos en los datos): un booleano nunca se acepta como numero (en Python `True` es un entero); montos, kilometro, alcoholemia, edad y anio no pueden ser negativos ni infinitos; los objetos de fecha y de coordenadas deben tener exactamente sus dos claves.

## 2. Reglas de valor

### N01 - Clave de comparacion (`normalize_key`)

**Anomalias:** A10, A13. Creada en la tarea 1.1 y ampliada con la raya en la 1.7.

1. La raya `–` (U+2013) y la raya larga `—` (U+2014) se convierten en `-`.
2. Descomposicion Unicode NFKD y eliminacion de las marcas diacriticas (la `n` con tilde pasa a `n`).
3. `casefold` (minusculas).
4. Espacios en blanco colapsados a uno y recortados en los extremos.

| Entrada | Salida |
| --- | --- |
| `HERIDO LEVE` | `herido leve` |
| `Herido leve` | `herido leve` |
| `Rumiñahui` | `ruminahui` |
| `HÚMEDA` (defensivo; los datos traen `HUMEDA`) | `humeda` |
| `VIA CUENCA–AZOGUES` | `via cuenca-azogues` |
| `Vía Baños–Puyo` | `via banos-puyo` |

La clave solo sirve para comparar y buscar en catalogos; nunca se guarda como valor visible.

### N02 - Nombre visible derivado (`display_name`)

**Anomalias:** A10, A12, A13. Para canton, parroquia y via, que no tienen catalogo cerrado (seccion 3.3).

1. Se parte de la clave de N01.
2. Cada palabra empieza con mayuscula, tambien despues de `(` y de `-`.
3. Las palabras `de`, `del`, `la`, `las`, `los`, `el`, `a` e `y` quedan en minusculas, salvo al inicio.

| Entrada | Salida |
| --- | --- |
| `GUAYAQUIL` / `Guayaquil` | `Guayaquil` |
| `Baños de Agua Santa` | `Banos de Agua Santa` |
| `LA MARISCAL` | `La Mariscal` |
| `Puerto Bolívar` | `Puerto Bolivar` |
| `AV. SIMON BOLIVAR (QUITO)` / `Av. Simón Bolívar (Quito)` | `Av. Simon Bolivar (Quito)` |
| `Av. de las Américas (Cuenca)` | `Av. de las Americas (Cuenca)` |
| `VIA A LA COSTA (GUAYAQUIL)` | `Via a la Costa (Guayaquil)` |
| `Vía Quevedo–Santo Domingo` | `Via Quevedo-Santo Domingo` |

Resultado verificado: canton 26 escrituras -> 22 nombres, parroquia 29 -> 29, via 25 -> 21 claves (20 vias tras el alias de N03).

### N03 - Via: nombre canonico y codigo

**Anomalias:** A12, A13, A22.

1. Se calcula la clave (N01).
2. Si la clave esta en la tabla de alias, se reemplaza por la clave canonica. Unico alias: `e35` -> `panamericana e35 (troncal de la sierra)`.
3. El nombre visible se deriva con N02.
4. El codigo de red vial se extrae del texto con la expresion `\bE\d{2,3}\b` sobre la clave en mayusculas; si no aparece, es null. No se infiere de conocimiento externo.

| Entrada | Nombre | Codigo |
| --- | --- | --- |
| `Panamericana E35 (Troncal de la Sierra)` (3) | `Panamericana E35 (Troncal de la Sierra)` | `E35` |
| `PANAMERICANA E35 (TRONCAL DE LA SIERRA)` (2) | `Panamericana E35 (Troncal de la Sierra)` | `E35` |
| `E35` (1) | `Panamericana E35 (Troncal de la Sierra)` | `E35` |
| `Troncal Amazónica E45` / `TRONCAL AMAZONICA E45` | `Troncal Amazonica E45` | `E45` |
| `E15` | `E15` | `E15` |
| `VIA A LA COSTA (GUAYAQUIL)` | `Via a la Costa (Guayaquil)` | null |

Las tres escrituras de la E35 suman 6 siniestros, igual que el valor de control de la Etapa 2. La misma regla resuelve `via_analizada` de los informes (`PANAMERICANA E35 (TRONCAL DE LA SIERRA)` -> E35).

### N04 - Fecha y hora del siniestro (`fecha_hora`)

**Anomalia:** A01. Zona: America/Guayaquil (metadata `zona_horaria`).

Formatos aceptados, en este orden:

| # | Forma | Formato | Tratamiento de la zona |
| --- | --- | --- | --- |
| F1 | texto ISO con desfase | `%Y-%m-%dT%H:%M:%S%z` | Se convierte a America/Guayaquil |
| F2 | texto dia primero | `%d/%m/%Y %H:%M` | Se asume America/Guayaquil |
| F3 | texto ISO sin desfase | `%Y-%m-%d %H:%M:%S` | Se asume America/Guayaquil |
| F4 | objeto `{fecha, hora}` | `fecha` con `%d-%m-%Y` y `hora` con `%H:%M` | Se asume America/Guayaquil |

Salida: `occurred_at` (datetime con `-05:00`) y los derivados `date`, `year`, `month` y `hour`, todos en hora local.

| Entrada | `occurred_at` | `date` / `year` / `month` / `hour` | Registro |
| --- | --- | --- | --- |
| `2025-01-12T05:40:00-05:00` | `2025-01-12T05:40:00-05:00` | 2025-01-12 / 2025 / 1 / 5 | SIN-2025-0001 |
| `03/02/2025 22:15` | `2025-02-03T22:15:00-05:00` | 2025-02-03 / 2025 / 2 / 22 | SIN-2025-0002 |
| `2025-02-22 14:05:00` | `2025-02-22T14:05:00-05:00` | 2025-02-22 / 2025 / 2 / 14 | SIN-2025-0003 |
| `{"fecha": "09-03-2025", "hora": "03:50"}` | `2025-03-09T03:50:00-05:00` | 2025-03-09 / 2025 / 3 / 3 | SIN-2025-0004 |
| `14/06/2026 05:10` | `2026-06-14T05:10:00-05:00` | 2026-06-14 / 2026 / 6 / 5 | SIN-2026-0007 |
| `01/03/2026 00:40` | `2026-03-01T00:40:00-05:00` | 2026-03-01 / 2026 / 3 / 0 | SIN-2026-0003 |

`14/06/2026` solo es valida con dia primero (no existe el mes 14); es uno de los 3 casos de la verificacion V2 del catalogo. Un texto con otro formato es error.

### N05 - Fechas sin hora

**Anomalias:** A23, A29.

| Campo | Formato | Entrada | Salida |
| --- | --- | --- | --- |
| `registros[].fecha_actualizacion` | `%Y-%m-%d` | `2025-05-06` (SIN-2025-0007 v2) | fecha 2025-05-06 |
| `informes[].fecha` | `%d/%m/%Y` | `10/02/2025` (INF-2025-01) | fecha 2025-02-10 |
| `informes[].fecha` | `%d/%m/%Y` | `30/03/2026` | fecha 2026-03-30 |

### N06 - Montos en USD (`danos_materiales`)

**Anomalia:** A02. Salida: float en USD.

1. Un numero (entero o decimal) se convierte a float.
2. En un texto se quitan `$`, `USD` y los espacios. Lo que queda debe tener solo digitos, `.` y `,`; si no, es error.
3. Si hay `.` y `,`, el que aparece ultimo es el separador decimal y el otro es separador de miles (se elimina).
4. Si hay un solo tipo de separador: una sola aparicion seguida de 1 o 2 digitos es decimal; si todos los grupos tras el separador tienen 3 digitos, es de miles. Otro caso es error. (*Defensivo*: no hay ejemplos en los datos.)
5. Solo digitos: se convierte a float.

| Entrada | Salida | Registro |
| --- | --- | --- |
| `18500` (numero) | 18500.0 | SIN-2025-0001 |
| `"3200"` | 3200.0 | SIN-2025-0002 |
| `"$6,400.00"` | 6400.0 | SIN-2025-0003 |
| `"21.000,00 USD"` | 21000.0 | SIN-2025-0004 |
| `"$4,100.00"` | 4100.0 | SIN-2025-0007 v2 |
| `"$3,900.00"` | 3900.0 | SIN-2025-0007 v1 (descartada por R01) |
| `"$33,800.00"` | 33800.0 | SIN-2026-0004 |
| `"6.200,00 USD"` | 6200.0 | SIN-2025-0016 |

Resultado sobre los 31 registros: minimo 1 200, maximo 41 000.

### N07 - Kilometro (`ubicacion.km`)

**Anomalia:** A03. Salida: float o null.

1. null o texto vacio (tras recortar) -> null.
2. Numero -> float.
3. Texto de solo digitos -> float.
4. Prefijo `Km` (sin importar mayusculas) seguido de un numero -> ese numero.
5. Abscisa `K+MMM` (`^\d+\+\d{3}$`) -> K + MMM / 1000.
6. Otro texto es error.

| Entrada | Salida |
| --- | --- |
| `128` (numero) | 128.0 |
| `"4"` | 4.0 |
| `"12+000"` | 12.0 |
| `"9+000"` | 9.0 |
| `"Km 11"` | 11.0 |
| `"Km 118"` | 118.0 |
| `""` | null |
| null | null |

Resultado: 26 valores entre 3 y 205; 5 null (4 vacios y 1 null).

### N08 - Coordenadas (`ubicacion.coordenadas`)

**Anomalia:** A04. Salida: `latitude` y `longitude` float, o ambas null.

1. null -> ambas null.
2. Objeto `{latitud, longitud}` -> sus dos numeros.
3. Texto `"lat,lon"`: se separa en la coma; deben quedar exactamente dos numeros, en orden latitud y longitud.
4. Latitud fuera de [-90, 90] o longitud fuera de [-180, 180] es error.

| Entrada | `latitude` | `longitude` |
| --- | --- | --- |
| `"-1.2497,-78.6237"` | -1.2497 | -78.6237 |
| `"0.0847,-76.895"` | 0.0847 | -76.895 |
| `{"latitud": -2.174, "longitud": -79.9224}` | -2.174 | -79.9224 |
| `{"latitud": 0.9632, "longitud": -79.6499}` | 0.9632 | -79.6499 |
| null | null | null |

Son referenciales (INF-2026-02): se guardan pero no se usan para calcular distancias.

### N09 - Alcoholemia (`personas[].alcohol_gl`)

**Anomalia:** A06. Salida: float en g/L o null.

1. null, `""` y `N/D` -> null (prueba no realizada o sin dato).
2. Numero -> float.
3. Texto: la coma decimal pasa a punto y se convierte a float.
4. Un valor negativo o un texto no numerico es error.

| Entrada | Salida |
| --- | --- |
| `"0,0"` | 0.0 |
| `"0.0"` | 0.0 |
| `0.4` (numero) | 0.4 |
| `"1,6"` | 1.6 |
| `"1.3"` | 1.3 |
| `""` | null |
| `"N/D"` | null |
| null | null |

Resultado: 47 personas con dato y 34 null; maximo 1.6 g/L.

### N10 - Enteros escritos como texto (`personas[].edad`, `vehiculos[].anio`)

**Anomalia:** A05.

1. Entero -> entero.
2. Texto de solo digitos (tras recortar) -> entero.
3. Otro valor es error.

| Entrada | Salida |
| --- | --- |
| `29` (numero) | 29 |
| `"39"` | 39 |
| `"10"` | 10 |
| `2019` (numero) | 2019 |
| `"2018"` | 2018 |

Resultado: edad de 7 a 71; anio de 2012 a 2023.

### N11 - Marca y modelo

**Anomalia:** A14.

1. Si existe `marca_modelo`, se colapsan los espacios y se divide en el primer espacio: lo anterior es la marca y lo posterior el modelo.
2. Si existen `marca` y `modelo`, se usan tal cual.
3. Ambos resultados van en mayusculas y con espacios colapsados.
4. Que falten ambas formas, o que aparezcan las dos, es error (en los datos siempre hay exactamente una). Tambien es error un `marca_modelo` de una sola palabra o una marca o modelo vacios.

| Entrada | `brand` | `model` |
| --- | --- | --- |
| `marca_modelo: "HINO AK"` | `HINO` | `AK` |
| `marca_modelo: "HONDA CG 150"` | `HONDA` | `CG 150` |
| `marca_modelo: "CHEVROLET D-MAX"` | `CHEVROLET` | `D-MAX` |
| `marca: "Chevrolet", modelo: "Aveo"` | `CHEVROLET` | `AVEO` |
| `marca: "Mercedes-Benz", modelo: "OF"` | `MERCEDES-BENZ` | `OF` |
| `marca: "Mazda", modelo: "BT-50"` | `MAZDA` | `BT-50` |

`CHEVROLET AVEO` y `Chevrolet` + `Aveo` quedan iguales.

### N12 - Texto libre

**Anomalia:** A07. Campos: `narrativa`, `motivo_anulacion`, `informes[].titulo`, `secciones[].titulo` y `secciones[].texto`.

1. Recortar los extremos y colapsar cualquier secuencia de espacios en blanco (incluidos saltos de linea) a un espacio.
2. El resto del texto no cambia: se conservan tildes, mayusculas y puntuacion.

Ejemplos (se describe la forma, no el contenido):

| Registro | Entrada | Salida |
| --- | --- | --- |
| SIN-2025-0001 | 2 espacios al inicio y al final, y un salto de linea seguido de espacio | Sin espacios en los extremos; el salto pasa a un espacio |
| SIN-2025-0006 | 2 espacios al inicio y al final, y un doble espacio interno | Sin espacios en los extremos ni dobles |
| SIN-2025-0008 | Un salto de linea interno | Un espacio |

Afecta a 10 narrativas; las secciones de informes ya vienen limpias. La narrativa de SIN-2026-0009 se normaliza igual que las demas: la instruccion embebida se conserva como dato (A28).

## 3. Catalogos de valores categoricos

Regla comun: valor original -> clave (N01) -> busqueda en el catalogo -> valor canonico. Las tablas listan todas las escrituras observadas, con su frecuencia. Los catalogos se codifican en `domain/catalogs.py` (tarea 1.6).

### 3.1 Catalogos cerrados

Una clave que no esta en el catalogo es error de carga.

**`tipo_siniestro`** (A10; definiciones de INF-2026-02 -> `AccidentType.definition`)

| Canonico | Escrituras observadas |
| --- | --- |
| `choque` | `CHOQUE` (9), `Choque` (9) |
| `atropello` | `Atropello` (3), `ATROPELLO` (2) |
| `estrellamiento` | `Estrellamiento` (2) |
| `perdida_de_pista` | `PERDIDA DE PISTA` (2), `Pérdida de pista` (1) |
| `volcamiento` | `VOLCAMIENTO` (2), `Volcamiento` (1) |

**`causa_probable`** (A10, A11): 17 escrituras -> 12 claves -> 10 causas

| Canonico | Escrituras observadas |
| --- | --- |
| `exceso_de_velocidad` | `EXCESO DE VELOCIDAD` (5), `Exceso de velocidad` (1), `VELOCIDAD EXCESIVA` (3) |
| `conducir_bajo_efectos_del_alcohol` | `CONDUCIR BAJO EFECTOS DEL ALCOHOL` (1), `Conducir bajo efectos del alcohol` (1), `CONDUCIR EN ESTADO DE EBRIEDAD` (1) |
| `invadir_carril` | `Invadir carril` (3) |
| `distraccion_del_conductor` | `Distracción del conductor` (2), `DISTRACCION DEL CONDUCTOR` (1) |
| `peaton_en_la_via` | `PEATON EN LA VIA` (2), `Peatón en la vía` (2) |
| `mal_estado_de_la_via` | `MAL ESTADO DE LA VIA` (2) |
| `no_respetar_semaforo` | `No respetar semáforo` (2) |
| `somnolencia` | `SOMNOLENCIA` (2) |
| `adelantamiento_indebido` | `ADELANTAMIENTO INDEBIDO` (1), `Adelantamiento indebido` (1) |
| `fallo_mecanico` | `FALLO MECANICO` (1) |

**`condiciones`** (sin variantes; solo pasan a minusculas)

| Campo | Canonico | Escrituras observadas |
| --- | --- | --- |
| `clima` | `despejado`, `lluvia`, `neblina` | `DESPEJADO` (20), `LLUVIA` (7), `NEBLINA` (4) |
| `superficie` | `seca`, `mojada`, `humeda` | `SECA` (20), `MOJADA` (7), `HUMEDA` (4) |
| `iluminacion` | `diurna`, `nocturna_con_iluminacion`, `nocturna_sin_iluminacion`, `amanecer_atardecer` | `DIURNA` (12), `NOCTURNA_CON_ILUMINACION` (7), `NOCTURNA_SIN_ILUMINACION` (6), `AMANECER_ATARDECER` (6) |

**`vehiculos[].tipo_vehiculo`** (A10): 16 escrituras -> 10 tipos

| Canonico | Escrituras observadas |
| --- | --- |
| `automovil` | `AUTOMOVIL` (11), `Automóvil` (6) |
| `camioneta` | `Camioneta` (5), `CAMIONETA` (3) |
| `motocicleta` | `MOTOCICLETA` (4), `Motocicleta` (3) |
| `bus` | `BUS` (3), `Bus` (2) |
| `camion` | `Camión` (2), `CAMION` (1) |
| `camion_liviano` | `Camión liviano` (2) |
| `camion_pesado` | `CAMION PESADO` (2), `Camión pesado` (1) |
| `suv` | `SUV` (2) |
| `taxi` | `Taxi` (2) |
| `trailer` | `Tráiler` (1) |

`camion` no se fusiona con `camion_liviano` ni con `camion_pesado`: el dato no dice cual de los dos es.

**`vehiculos[].servicio`** (A10)

| Canonico | Escrituras observadas |
| --- | --- |
| `particular` | `PARTICULAR` (18), `particular` (16) |
| `carga` | `carga` (6), `CARGA` (3) |
| `publico` | `público` (4), `PUBLICO` (3) |

**`personas[].rol`** (A10)

| Canonico | Escrituras observadas |
| --- | --- |
| `conductor` | `CONDUCTOR` (27), `conductor` (23) |
| `pasajero` | `PASAJERO` (13), `pasajero` (13) |
| `peaton` | `peatón` (5) |

**`personas[].condicion`** (A10; gravedad de INF-2026-02)

| Canonico | Escrituras observadas |
| --- | --- |
| `fallecido` | `FALLECIDO` (13), `Fallecido` (6) |
| `herido_grave` | `HERIDO GRAVE` (10), `Herido grave` (4) |
| `herido_leve` | `Herido leve` (19), `HERIDO LEVE` (13) |
| `ileso` | `Ileso` (11), `ILESO` (5) |

**`personas[].sexo`** (A09; `M` verificado como masculino en V1)

| Canonico | Escrituras observadas |
| --- | --- |
| `M` | `M` (21), `Hombre` (21), `MASCULINO` (19) |
| `F` | `FEMENINO` (8), `F` (6), `Mujer` (6) |

**`personas[].proteccion`** (A08; valores de `uso_proteccion` en INF-2026-02)

| Canonico | Escrituras observadas |
| --- | --- |
| `cinturon` | `CINTURON` (23), `SI - CINTURON` (18), `Cinturón de seguridad` (16) |
| `casco` | `SI - CASCO` (4), `CASCO` (3) |
| `ninguna` | `NINGUNO` (1), `NO` (1) |
| `no_aplica` | `N/A` (6), `NO APLICA` (1) |
| `no_registrado` | `SIN DATO` (4), null (3), `""` (1) |

**`registros[].estado`** (A16, A29)

| Canonico (`status`) | `is_active` | Escrituras observadas |
| --- | --- | --- |
| `vigente` | true | `ACTIVO` (30) |
| `anulado` | false | `ANULADO` (1) |

**`informes[].estado` e `informes[].clasificacion`** (A21, A27)

| Campo | Canonico | Escrituras observadas |
| --- | --- | --- |
| `estado` | `vigente`, `reemplazado` | `VIGENTE` (4), `REEMPLAZADO` (1) |
| `clasificacion` | `publico`, `reservado` | `PUBLICO` (4), `RESERVADO` (1) |

### 3.2 Provincia: catalogo cerrado de las 24 provincias

El catalogo contiene las 24 provincias del Ecuador con su nombre canonico ASCII, no solo las 17 observadas. Asi, una consulta por una provincia valida sin siniestros (escenario 10, "Galapagos") devuelve cero resultados en lugar de un error de validacion. Una clave que no es provincia es error de carga.

| Canonico | Escrituras observadas |
| --- | --- |
| `Pichincha` | `Pichincha` (3), `PICHINCHA` (3) |
| `Guayas` | `Guayas` (3), `GUAYAS` (2) |
| `Tungurahua` | `TUNGURAHUA` (2), `Tungurahua` (1) |
| `Manabi` | `MANABI` (1), `Manabi` (1) |
| `Azuay`, `El Oro` | `Azuay` (2), `El Oro` (2) |
| `Canar` | `CANAR` (1) |
| `Los Rios` | `Los Ríos` (1) |
| `Sucumbios` | `SUCUMBIOS` (1) |
| `Santo Domingo de los Tsachilas` | `Santo Domingo de los Tsachilas` (1) |
| `Chimborazo`, `Cotopaxi`, `Esmeraldas`, `Imbabura`, `Loja`, `Napo`, `Santa Elena` | una escritura cada una |
| `Bolivar`, `Carchi`, `Galapagos`, `Morona Santiago`, `Orellana`, `Pastaza`, `Zamora Chinchipe` | sin siniestros en los datos |

Resultado: 21 escrituras -> 17 provincias; Pichincha 6 registros y Guayas 5 (Pichincha queda en 5 siniestros vigentes tras R01 y R02).

### 3.3 Canton, parroquia y via: dimensiones abiertas

No tienen catalogo cerrado: el nombre canonico se deriva con N02 (y N03 para vias) y la clave de N01 sirve de identidad. Motivo: un catalogo cerrado exigiria los 221 cantones y mas de mil parroquias desde una fuente externa, y no aporta control adicional porque la derivacion es determinista. Canton y parroquia se identifican junto con su nivel superior (provincia y canton), porque el nombre solo no es unico (`Santa Elena` es canton y provincia; `Loja` y `Esmeraldas` tambien).

## 4. Reglas por registro

Se aplican en `pipeline.py` (tarea 2.2) sobre los valores ya normalizados.

### R01 - Una version por siniestro

**Anomalias:** A15, A30.

1. Se agrupan los registros por `id_parte`.
2. Se conserva el de mayor `version`, sin importar su posicion en la lista. Dos registros con el mismo id y la misma version son error.
3. `versions_count` = numero de registros del grupo.

| Registro | Posicion | `version` | Danos | Resultado |
| --- | --- | --- | --- | --- |
| SIN-2025-0007 | 6 | 2 | `$4,100.00` | Se carga; `versions_count = 2` |
| SIN-2025-0007 | 30 (ultima) | 1 | `$3,900.00` | Se descarta |

Resultado: 31 registros -> 30 siniestros.

### R02 - Anulacion y reemplazo

**Anomalia:** A16.

1. `status` y `is_active` salen del catalogo de `estado` (3.1).
2. `annulment_reason` = `motivo_anulacion` normalizado con N12; null si no existe.
3. Si un registro trae `reemplaza_a`, se crea `(anulado)-[:REPLACED_BY]->(reemplazo)`. El id referido debe existir y estar anulado; si no, es error.

| Registro | Entrada | Resultado |
| --- | --- | --- |
| SIN-2026-0010 | `estado: "ANULADO"`, `motivo_anulacion: "Ubicación errónea (cantón incorrecto) y parte incompleto"` | `status = anulado`, `is_active = false`, `annulment_reason` con el texto |
| SIN-2026-0011 | `estado: "ACTIVO"`, `reemplaza_a: "SIN-2026-0010"` | `status = vigente`; relacion SIN-2026-0010 `REPLACED_BY` SIN-2026-0011 |

Resultado: 29 vigentes y 1 anulado.

### R03 - Conteos derivados de las personas

**Anomalias:** A17, A18.

1. `deaths` = personas con `condicion` `fallecido`.
2. `injured` = personas con `herido_grave` o `herido_leve`.
3. `unharmed` = personas con `ileso`.
4. `summary_mismatch` = true si alguno de los tres difiere del `resumen` declarado. El resumen declarado se conserva solo para el texto de la advertencia.
5. `days_until_death` se copia de `dias_hasta_deceso`; null si no existe.

| Registro | `resumen` declarado (F/H/I) | Derivado de personas (F/H/I) | `summary_mismatch` |
| --- | --- | --- | --- |
| SIN-2025-0012 | 0 / 3 / 0 | 0 / 2 / 0 (`Herido leve`, `HERIDO LEVE`) | true |
| SIN-2026-0011 | 2 / 1 / 0 | 2 / 1 / 0 (incluye el pasajero con `dias_hasta_deceso = 6`) | false |

Resultado en vigentes: 18 fallecidos y 44 heridos (valores de control).

### R04 - Identificadores sinteticos y datos personales

**Anomalias:** A19, A25, A26.

1. Vehiculos: `vehicle_id = <id_parte>-V<n>`, con n desde 1 en el orden de la lista del registro.
2. Personas: `person_id = <id_parte>-P<n>`, con el mismo criterio.
3. La persona se enlaza al vehiculo del mismo registro cuya `placa` es igual a su `placa_vehiculo`. Si `placa_vehiculo` es null (peatones), no hay enlace. Una placa que no coincide con ningun vehiculo del registro es error.
4. Despues del enlace, `placa` y `placa_vehiculo` se descartan. `nombre` y `cedula` nunca pasan al modelo de dominio.

| Registro | Resultado |
| --- | --- |
| SIN-2025-0001 | Vehiculos `SIN-2025-0001-V1`...; personas `SIN-2025-0001-P1`..., cada una con su vehiculo |
| Peatones (5 personas) | Sin relacion `RODE_IN` |

### R05 - Informes

**Anomalias:** A21, A22, A24, A27.

1. Un informe con `clasificacion` distinta de `publico` se excluye completo, texto incluido: INF-RES-01. Se aplica al leer el archivo (`RawDataset`, tarea 1.8), antes de este paso.
2. `estado` sale del catalogo de 3.1.
3. Si un informe trae `reemplaza_a`, se crea `(nuevo)-[:SUPERSEDES]->(anterior)`: INF-2026-01 `SUPERSEDES` INF-2025-01.
4. `via_analizada` se resuelve con N03 y crea `ANALYZES_ROAD`; si es null, no hay relacion.
5. Las secciones conservan su orden: `order` desde 1 segun la posicion en la lista.

Resultado: 5 informes -> 4 cargados; 2 enlazados a la E35.

### R06 - Determinismo

**Anomalia:** A30. La salida del pipeline se ordena por id (siniestros por `accident_id`, informes por `report_id`), de modo que la misma entrada produce siempre la misma carga.

## 5. Correspondencia de campos

| Campo original | Destino | Regla |
| --- | --- | --- |
| `id_parte` | `Accident.accident_id` | Patron `SIN-\d{4}-\d{4}` |
| `version` | `Accident.version`, `versions_count` | R01 |
| `fecha_actualizacion` | `Accident.updated_at` | N05 |
| `estado` | `Accident.status`, `is_active` | 3.1, R02 |
| `fecha_hora` | `occurred_at`, `date`, `year`, `month`, `hour` | N04 |
| `ubicacion.provincia` | `Province.name` | 3.2 |
| `ubicacion.canton` | `Canton.name` | N02 |
| `ubicacion.parroquia` | `Parish.name` | N02 |
| `ubicacion.via` | `Road.name`, `Road.code` | N03 |
| `ubicacion.km` | `Accident.km` y `ON_ROAD.km` | N07 |
| `ubicacion.coordenadas` | `Accident.latitude`, `longitude` | N08 |
| `tipo_siniestro` | `AccidentType.code` | 3.1 |
| `causa_probable` | `Cause.code` | 3.1 |
| `condiciones.clima`, `superficie`, `iluminacion` | `Accident.weather`, `surface`, `lighting` | 3.1 |
| `danos_materiales` | `Accident.damages_usd` | N06 |
| `resumen` | Solo para `summary_mismatch` | R03 |
| `narrativa` | `Accident.narrative` | N12 |
| `motivo_anulacion` | `Accident.annulment_reason` | N12, R02 |
| `reemplaza_a` | Relacion `REPLACED_BY` | R02 |
| `fuente` | No se carga: es constante (`Parte policial (ficticio)`) en los 31 registros | - |
| `vehiculos[].tipo_vehiculo` | `VehicleType.name` | 3.1 |
| `vehiculos[].marca_modelo`, `marca`, `modelo` | `Vehicle.brand`, `model` | N11 |
| `vehiculos[].anio` | `Vehicle.year` | N10 |
| `vehiculos[].servicio` | `Vehicle.service` | 3.1 |
| `vehiculos[].placa` | Solo para el enlace; no se carga | R04 |
| `personas[].nombre`, `cedula` | Se descartan al leer el archivo (`RawPerson`) | R04, P1 |
| `personas[].rol`, `condicion` | `Person.role`, `condition` y en `PARTICIPATED_IN` | 3.1 |
| `personas[].edad` | `Person.age` | N10 |
| `personas[].sexo` | `Person.sex` | 3.1 |
| `personas[].alcohol_gl` | `Person.alcohol_gl` | N09 |
| `personas[].proteccion` | `Person.protection` | 3.1 |
| `personas[].placa_vehiculo` | Solo para el enlace; no se carga | R04 |
| `personas[].dias_hasta_deceso` | `Person.days_until_death` | R03 |
| `informes[].id`, `titulo`, `fecha` | `Report.report_id`, `title`, `date` | N12, N05 |
| `informes[].estado`, `clasificacion` | `Report.status`, `classification` | 3.1, R05 |
| `informes[].via_analizada` | Relacion `ANALYZES_ROAD` | N03, R05 |
| `informes[].reemplaza_a` | Relacion `SUPERSEDES` | R05 |
| `informes[].secciones[]` | `ReportSection.title`, `text`, `order` | N12, R05 |

## 6. Errores de normalizacion

- Toda regla que no reconoce un valor lanza `NormalizationError` con el id del registro, la ruta del campo (`registros[].ubicacion.km`) y el motivo.
- El valor original se incluye en el mensaje solo si no es un campo personal; nombre, cedula y placa nunca aparecen en errores ni en logs.
- La carga se detiene ante el primer error, antes de escribir en Neo4j, y el loader termina con codigo distinto de cero.

## 7. Reutilizacion fuera de la carga

`search_accidents` (seccion 7.3 del plan) normaliza los filtros del usuario con las mismas funciones: `province` con 3.2, `canton` con N01 y N02, `road` con N03 (por eso `E35` y `Panamericana E35` encuentran los mismos 6 siniestros) y los filtros categoricos con los catalogos de 3.1. Una sola implementacion evita que la carga y la consulta discrepen.
