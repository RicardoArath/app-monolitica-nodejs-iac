"""
common/db.py
Pool centralizado de conexiones PostgreSQL usando psycopg 3 y psycopg_pool.
PostgreSQL es la fuente única de la verdad (SSOT) para la librería en línea.
"""
import atexit
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool

from common import config
from common.logging_utils import get_logger

logger = get_logger('common.db')

_pool = None


def get_conninfo():
    """Genera la cadena de conexión para PostgreSQL."""
    return (
        f"host={config.PGHOST} "
        f"port={config.PGPORT} "
        f"dbname={config.PGDATABASE} "
        f"user={config.PGUSER} "
        f"password={config.PGPASSWORD} "
        f"connect_timeout=3"
    )


def open_pool():
    """Abre el pool de conexiones global si no está inicializado."""
    global _pool
    if _pool is not None and not _pool.closed:
        return _pool

    conninfo = get_conninfo()
    logger.info(
        f"Iniciando pool PostgreSQL en {config.PGHOST}:{config.PGPORT}/{config.PGDATABASE} "
        f"(min={config.PG_POOL_MIN}, max={config.PG_POOL_MAX})"
    )
    _pool = ConnectionPool(
        conninfo=conninfo,
        min_size=config.PG_POOL_MIN,
        max_size=config.PG_POOL_MAX,
        open=True
    )
    return _pool


def close_pool():
    """Cierra el pool de conexiones al terminar la aplicación."""
    global _pool
    if _pool is not None and not _pool.closed:
        logger.info("Cerrando pool de conexiones PostgreSQL")
        _pool.close()
        _pool = None


atexit.register(close_pool)


@contextmanager
def get_connection():
    """
    Context manager para obtener y devolver una conexión del pool.
    Uso:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    pool = open_pool()
    with pool.connection() as conn:
        yield conn


def check_db_health():
    """
    Verifica conectividad con PostgreSQL ejecutando un 'SELECT 1'.
    Retorna (True, None) si está saludable, o (False, mensaje_error).
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True, None
    except Exception as e:
        logger.error(f"Fallo en check_db_health: {e}")
        return False, str(e)
