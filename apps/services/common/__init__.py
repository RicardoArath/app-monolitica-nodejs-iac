"""
common
Paquete compartido por todos los microservicios Flask de Librería en Línea
(login, books, users, authors, pedidos, pagos).

Centraliza:
- config        -> variables de entorno comunes (PostgreSQL, Redis, JWT, CORS, TTLs)
- db            -> pool de conexiones PostgreSQL (fuente principal de datos)
- redis_client  -> conexión compartida a Redis, caché fail-open y operaciones fail-closed
- security      -> emisión/validación de JWT, lista de revocación (jti) y RBAC
- response      -> respuestas JSON/XML homogéneas
- metrics       -> contadores en memoria expuestos en /metrics (formato Prometheus)
- app_factory   -> creación de apps Flask con /health, /metrics, CORS y manejo de errores
"""
from . import config
from . import metrics
from .logging_utils import get_logger
from .db import get_connection, open_pool, close_pool, check_db_health
from .redis_client import redis_client, RedisClient, RedisSecurityException
from .response import make_response_format
from .security import (
    issue_access_token,
    issue_refresh_token,
    revoke_jwt,
    jwt_required,
    roles_required,
)
from .app_factory import create_microservice_app

__all__ = [
    'config',
    'get_logger',
    'metrics',
    'get_connection',
    'open_pool',
    'close_pool',
    'check_db_health',
    'redis_client',
    'RedisClient',
    'RedisSecurityException',
    'make_response_format',
    'issue_access_token',
    'issue_refresh_token',
    'revoke_jwt',
    'jwt_required',
    'roles_required',
    'create_microservice_app',
]
