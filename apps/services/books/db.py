"""
db.py
Pool de conexiones PostgreSQL con Psycopg 3 para el microservicio de libros.
"""
from psycopg_pool import ConnectionPool
from config import PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

_conninfo = (
    f"host={PGHOST} port={PGPORT} dbname={PGDATABASE} "
    f"user={PGUSER} password={PGPASSWORD}"
)

pool = ConnectionPool(conninfo=_conninfo, min_size=2, max_size=10, open=False)


def open_pool():
    """Abre el pool de conexiones."""
    pool.open()


def close_pool():
    """Cierra el pool de conexiones."""
    pool.close()


def get_connection():
    """Obtiene una conexión del pool (usar con with)."""
    return pool.connection()


def health_check():
    """Verifica conectividad a PostgreSQL ejecutando SELECT 1."""
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except Exception:
        return False
