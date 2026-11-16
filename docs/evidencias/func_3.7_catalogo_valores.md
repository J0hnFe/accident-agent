# Catalogo de valores de busqueda

Generado desde el codigo con `uv run python scripts/export_catalog.py`.
Fuente: `src/accident_agent/domain/catalogs.py` y `tools/accident_search.py`.
Las mayusculas y las tildes no importan: `Pichincha`, `PICHINCHA` y `pichincha`
son el mismo valor. Un valor desconocido se rechaza con sugerencias.

## Provincia (`province`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `Azuay` | Azuay | - |
| `Bolivar` | Bolivar | - |
| `Canar` | Canar | - |
| `Carchi` | Carchi | - |
| `Chimborazo` | Chimborazo | - |
| `Cotopaxi` | Cotopaxi | - |
| `El Oro` | El Oro | - |
| `Esmeraldas` | Esmeraldas | - |
| `Galapagos` | Galapagos | - |
| `Guayas` | Guayas | - |
| `Imbabura` | Imbabura | - |
| `Loja` | Loja | - |
| `Los Rios` | Los Rios | - |
| `Manabi` | Manabi | - |
| `Morona Santiago` | Morona Santiago | - |
| `Napo` | Napo | - |
| `Orellana` | Orellana | - |
| `Pastaza` | Pastaza | - |
| `Pichincha` | Pichincha | - |
| `Santa Elena` | Santa Elena | - |
| `Santo Domingo de los Tsachilas` | Santo Domingo de los Tsachilas | - |
| `Sucumbios` | Sucumbios | - |
| `Tungurahua` | Tungurahua | - |
| `Zamora Chinchipe` | Zamora Chinchipe | - |

## Tipo de siniestro (`accident_type`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `choque` | Choque | - |
| `estrellamiento` | Estrellamiento | - |
| `atropello` | Atropello | - |
| `volcamiento` | Volcamiento | - |
| `perdida_de_pista` | Perdida de pista | - |

## Causa probable (`cause`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `exceso_de_velocidad` | Exceso de velocidad | `velocidad excesiva` |
| `conducir_bajo_efectos_del_alcohol` | Conducir bajo efectos del alcohol | `conducir en estado de ebriedad` |
| `invadir_carril` | Invadir carril | - |
| `distraccion_del_conductor` | Distraccion del conductor | - |
| `peaton_en_la_via` | Peaton en la via | - |
| `mal_estado_de_la_via` | Mal estado de la via | - |
| `no_respetar_semaforo` | No respetar semaforo | - |
| `somnolencia` | Somnolencia | - |
| `adelantamiento_indebido` | Adelantamiento indebido | - |
| `fallo_mecanico` | Fallo mecanico | - |

## Tipo de vehiculo (`vehicle_type`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `automovil` | Automovil | - |
| `camioneta` | Camioneta | - |
| `motocicleta` | Motocicleta | - |
| `bus` | Bus | - |
| `camion` | Camion | - |
| `camion_liviano` | Camion liviano | - |
| `camion_pesado` | Camion pesado | - |
| `suv` | Suv | - |
| `taxi` | Taxi | - |
| `trailer` | Trailer | - |

## Clima (`weather`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `despejado` | Despejado | - |
| `lluvia` | Lluvia | - |
| `neblina` | Neblina | - |

## Superficie (`surface`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `seca` | Seca | - |
| `mojada` | Mojada | - |
| `humeda` | Humeda | - |

## Iluminacion (`lighting`)

| Valor | Texto legible | Otras escrituras aceptadas |
| --- | --- | --- |
| `diurna` | Diurna | - |
| `nocturna_con_iluminacion` | Nocturna con iluminacion | - |
| `nocturna_sin_iluminacion` | Nocturna sin iluminacion | - |
| `amanecer_atardecer` | Amanecer atardecer | - |

## Modos (`mode`) y agrupaciones (`group_by`)

- `mode`: `search`, `stats`, `reports`.
- `group_by` (obligatorio con `mode=stats`): `province`, `cause`, `accident_type`, `month`, `year`, `weather`, `vehicle_type`.
- `road`: codigo de via (`E35`, `E45`, `E15`) o parte del nombre (`Via a la Costa`).
- `canton`: nombre del canton (`Quito`, `Ruminahui`); sin catalogo cerrado.
