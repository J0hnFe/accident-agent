"""Loader: verifica el original, ejecuta el pipeline, carga Neo4j y comprueba la carga.

Uso: uv run python -m accident_agent.ingestion (en compose, el servicio `loader`).
Sale con 0 si todo coincide; con 1 ante cualquier error o diferencia con los valores de control.
"""

import sys
from pathlib import Path

from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable

from accident_agent.config import Settings, get_settings
from accident_agent.graph.connection import create_driver, wait_for_neo4j
from accident_agent.ingestion.neo4j_writer import LoadMismatchError, Neo4jWriter
from accident_agent.ingestion.pipeline import IngestionError, run_pipeline, verify_integrity
from accident_agent.ingestion.verification import CONTROL_VALUES, VerificationReport, verify


def _say(message: str) -> None:
    print(f"loader: {message}", flush=True)


def _report(report: VerificationReport) -> None:
    for name, value in report.observed.items():
        expected = CONTROL_VALUES.get(name)
        status = "ok" if value == expected else ("DIFERENTE" if report.enforced else "informativo")
        _say(f"  {name} = {value} [{status}]")
    if not report.enforced:
        _say("el SHA-256 no es el del archivo conocido: valores de control no exigidos")
    _say(f"datos personales en el grafo: {report.personal_data_findings or 'ninguno'}")


def run_load(settings: Settings, *, wait_attempts: int = 20) -> int:
    data_file = Path(settings.data_file)
    sha_file = data_file.with_name(f"{data_file.name}.sha256")
    try:
        sha256 = verify_integrity(data_file, sha_file)
        _say(f"{data_file.name} SHA-256 {sha256} (verificado contra {sha_file.name})")
        dataset = run_pipeline(data_file)
        active = sum(a.is_active for a in dataset.accidents)
        _say(
            f"pipeline: {len(dataset.accidents)} siniestros ({active} vigentes), "
            f"{len(dataset.reports)} informes"
        )
        with create_driver(settings) as driver:
            wait_for_neo4j(driver, attempts=wait_attempts)
            created = Neo4jWriter(driver).write(dataset)
            nodes = sum(n for n, _ in created.values()) + 1  # +1: nodo Dataset
            rels = sum(r for _, r in created.values())
            _say(f"carga: {nodes} nodos y {rels} relaciones en una transaccion")
            report = verify(driver, sha256)
        _report(report)
        if verify_integrity(data_file, sha_file) != sha256:
            raise IngestionError("el original cambio durante la carga")
    except (IngestionError, LoadMismatchError) as exc:
        _say(f"ERROR {exc}")
        return 1
    except FileNotFoundError as exc:
        _say(f"ERROR no se encontro el archivo de datos: {exc.filename}")
        return 1
    except AuthError:
        _say("ERROR credenciales de Neo4j rechazadas: revise NEO4J_USER y NEO4J_PASSWORD")
        return 1
    except ServiceUnavailable:
        _say(f"ERROR Neo4j no responde en {settings.neo4j_uri}")
        return 1
    except Neo4jError as exc:
        _say(f"ERROR de Neo4j: {exc.code}")
        return 1

    if not report.ok:
        for mismatch in report.mismatches:
            _say(f"DIFERENCIA {mismatch}")
        _say("ERROR la verificacion posterior a la carga fallo")
        return 1
    _say("carga verificada")
    return 0


def main() -> int:
    return run_load(get_settings())


if __name__ == "__main__":
    sys.exit(main())
