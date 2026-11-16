# Etapa 6 - Avance de documentacion y entrega

- Fecha: 2026-11-15.
- Implementacion documentada: `eb9537e` (aplicacion 0.1.0).
- Estado: tareas 6.1, 6.2 y 6.3 completas; etapa abierta.
- Repositorio remoto: no configurado al iniciar esta etapa.
- URL publica, commit/tag entregado, acceso anonimo y confirmacion de envio: pendientes.

## Trabajo realizado

- README con configuracion, arranque, CLI, REST, pruebas, persistencia y diagnostico.
- Documentos tecnico y funcional en Markdown editable y PDF, con ortografia completa.
- Diagramas y capturas; conversaciones, errores, logs y contratos tomados de evidencias reales.
- Actualizacion de las tablas de avance y decision del formato PDF.
- Excepcion de `ascii-guard` para `docs/entrega/`, prevista por CLAUDE.md.

## Decisiones

- PDF para lectura portable y Markdown como fuente editable; no se agregan dependencias de
  documentos a la aplicacion. La exportacion usa ReportLab en un entorno temporal.
- Se conserva la autoria del historial (J0hnFe); no se inventa un nombre completo.
- Se cita la version implementada `eb9537e`; el commit de entrega se registrara tras publicar.
- Las mediciones de etapa 5 se identifican como historicas. Las pruebas nuevas se guardan
  por separado: no se ejecuta el LLM real ni se consume cuota.
- Se corrigen ejemplos orientativos de las guias segun el codigo: `cli chat` explicito,
  HTTP 200 con `stop_reason=llm_error` en fallos del proveedor, sin prometer HTTP 503.
- Se documenta la persistencia real: los informes del contenedor CLI eliminado con `--rm`
  no quedan disponibles en la API; informes y logs no tienen volumen por defecto.

## Verificaciones de esta etapa

| Verificacion | Resultado |
| --- | --- |
| Suite por defecto | 719 pasan; 30 deseleccionadas |
| Suite sin LLM real, con Neo4j | 748 pasan; 1 deseleccionada; cobertura total 96% |
| Ruff | Sin errores |
| Mypy | Sin errores, 81 archivos |
| Docker existente | Neo4j healthy, loader Exited(0), API activa |
| Clon limpio | 287 nodos, 438 relaciones, todos los controles correctos; health ok |
| PDF | 23 paginas tecnicas y 20 funcionales; render revisado, sin texto fuera de margenes |
| Revision documental independiente | Corregidos ejemplos ausentes, indice, versiones y alcance de grounding |

La primera ejecucion de integracion dentro del sandbox omitio 29 pruebas por conexion
bloqueada; la repeticion con acceso autorizado a Neo4j aprobo las 748. La cobertura actual
96% no reemplaza el 97% historico de etapa 5: esta corrida excluye la prueba real.

## Auditoria de entrega (6.5, parcial)

- Requisitos de implementacion: vinculados a codigo, pruebas y evidencias en el documento tecnico.
- Instalacion, uso, pruebas y limitaciones: README revisado frente a Compose y las interfaces.
- Documentos: fuentes y PDF disponibles; referencias a URL publica pendientes de publicacion.
- Arranque desde clon limpio verificado con el README: proyecto, imagen, puertos y volumen aislados;
  loader correcto y API saludable. Sin clave IA, por lo que no se repitio conversacion real.
- Falta revisar secretos en el historial final, publicar, verificar acceso anonimo y enviar.
- No se marca 6.5, 6.7 ni el DoD de la etapa hasta cerrar esos puntos.
- Las capturas adicionales de Langfuse de 5.2 siguen pendientes; no se fabrican capturas.

## Evidencias y archivos

- `docs/evidencias/6.5_pytest_sin_llm.txt`: ejecucion actual sin consumo del proveedor.
- `docs/entrega/DOCUMENTO_TECNICO.md` y `.pdf`.
- `docs/entrega/DOCUMENTO_FUNCIONAL.md` y `.pdf`.
- `docs/diagramas/`: diagramas editables y representaciones PNG.
- README, plan, guias y configuracion del hook ASCII.

Alimenta las portadas, resumenes, anexos y tablas de avance de ambos documentos.

## Reproducibilidad con README final

Clon local de `eb9537e` en `/tmp/bit-stage6-clean`, con README actualizado y `.env`
nuevo a partir de `.env.example` (clave Neo4j aleatoria; sin claves de terceros).
Se ejecuto el mismo `up -d --build` con un override de aislamiento:
proyecto e imagen `bit-stage6-check`, puertos 17474/17687/18000. El volumen era nuevo;
no se borro ni modifico la base del proyecto original. Loader verifico SHA-256,
30 siniestros, 29 vigentes, 4 informes, 18 fallecidos, 44 heridos, 287 nodos,
438 relaciones y ausencia de datos personales. API: `{"status":"ok","neo4j":"ok","llm_configured":false}`.
La consulta real al modelo no se repitio; ya existe evidencia de etapa 5.
