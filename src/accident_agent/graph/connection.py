"""Creacion del driver de Neo4j y espera a que el servidor acepte conexiones."""

import time

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from accident_agent.config import Settings


def create_driver(settings: Settings) -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        connection_timeout=10,
        # Reintentos breves: con Neo4j caido, una herramienta debe fallar antes de su timeout
        # (10 s). El driver inicia un reintento mientras no se supere este tiempo y espera 1, 2
        # y 4 s con jitter: con 2 s hay a lo sumo dos reintentos (fallo en 3.6 s como maximo);
        # con 3 s a veces entraba un tercero y el fallo llegaba a unos 7 s. El arranque lo espera
        # wait_for_neo4j, no estos reintentos.
        max_transaction_retry_time=2,
    )


def wait_for_neo4j(driver: Driver, *, attempts: int = 20, delay_seconds: float = 3) -> None:
    """Reintenta mientras el servidor arranca; un error de credenciales no se reintenta."""
    for attempt in range(1, attempts + 1):
        try:
            driver.verify_connectivity()
            return
        except AuthError:
            raise
        except ServiceUnavailable:
            if attempt == attempts:
                raise
            time.sleep(delay_seconds)
