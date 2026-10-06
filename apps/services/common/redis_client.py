"""
common/redis_client.py
Capa compartida de Redis con patrón de resiliencia Dual Fail-Safe:
  1. Fail-Open para lecturas de caché del catálogo (si Redis falla, cae a PostgreSQL sin romper la API).
  2. Fail-Closed para seguridad (sesiones, revocación jwt:revoked:<jti>, refresh tokens e idempotencia):
     si Redis no está disponible, lanza RedisSecurityException (resultando en 503 Service Unavailable).
"""
from datetime import date, datetime
from decimal import Decimal
import json
import threading
from typing import Any, Optional, Tuple
from uuid import UUID

import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from common import config
from common.logging_utils import get_logger
from common import metrics

logger = get_logger('common.redis')


def _serialize_to_json(val: Any) -> str:
    """Serializa estructuras a JSON manejando Decimal, datetime y UUID."""
    def _default(o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        return str(o)
    return json.dumps(val, default=_default)


class RedisSecurityException(Exception):
    """Lanzada cuando una operación crítica de seguridad no puede completarse en Redis."""
    pass


class RedisClient:
    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._lock = threading.Lock()

    def get_client(self) -> redis.Redis:
        """Obtiene la instancia del cliente Redis usando un ConnectionPool reutilizable."""
        if self._client is not None:
            return self._client

        with self._lock:
            if self._client is not None:
                return self._client

            logger.info(f"Iniciando pool Redis hacia {config.REDIS_URL} (protocol={config.REDIS_PROTOCOL})")
            self._pool = redis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_MAX_CONNECTIONS,
                socket_timeout=config.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=config.REDIS_CONNECT_TIMEOUT,
                decode_responses=True,
                protocol=config.REDIS_PROTOCOL
            )
            self._client = redis.Redis(connection_pool=self._pool)
            return self._client

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    def check_health(self) -> Tuple[bool, Optional[str]]:
        """Verifica conectividad con Redis mediante PING."""
        try:
            client = self.get_client()
            if client.ping():
                return True, None
            return False, "PING returned false"
        except Exception as e:
            return False, str(e)

    # =========================================================================
    # CACHE PATTERN (FAIL-OPEN)
    # =========================================================================
    def get_cache(self, key: str, prefix: str = "") -> Optional[Any]:
        """
        Recupera un valor de caché en JSON o texto.
        Si Redis falla o timeout, registra bypass y retorna None sin lanzar excepción.
        """
        try:
            client = self.get_client()
            val = client.get(key)
            if val is not None:
                metrics.inc('redis_cache_hits_total', prefix=prefix or key.split(':')[0])
                try:
                    return json.loads(val)
                except (ValueError, TypeError):
                    return val
            else:
                metrics.inc('redis_cache_misses_total', prefix=prefix or key.split(':')[0])
                return None
        except (RedisError, Exception) as e:
            metrics.inc('redis_cache_bypass_total', prefix=prefix or key.split(':')[0])
            metrics.inc('redis_errors_total', operation='get_cache')
            logger.warning(f"Fail-Open: Fallo de lectura de caché para '{key}', consultando PostgreSQL. Error: {e}")
            return None

    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None, prefix: str = "") -> bool:
        """
        Guarda un valor en caché en formato JSON.
        Si Redis falla, registra el error y retorna False sin romper la petición.
        """
        try:
            client = self.get_client()
            payload = _serialize_to_json(value) if not isinstance(value, str) else value
            ex = ttl if ttl is not None else config.CACHE_TTL_BOOKS_LIST
            client.set(key, payload, ex=ex)
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='set_cache')
            logger.warning(f"Fail-Open: No se pudo guardar caché para '{key}'. Error: {e}")
            return False

    def delete_cache(self, key: str) -> bool:
        """Elimina una clave específica de caché."""
        try:
            client = self.get_client()
            client.delete(key)
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='delete_cache')
            logger.warning(f"No se pudo eliminar clave '{key}': {e}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalida todas las claves que coincidan con el patrón (ej. 'books:*') usando SCAN.
        Retorna la cantidad de claves eliminadas.
        """
        deleted_count = 0
        try:
            client = self.get_client()
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    pipeline = client.pipeline()
                    for k in keys:
                        pipeline.delete(k)
                    pipeline.execute()
                    deleted_count += len(keys)
                if cursor == 0:
                    break

            metrics.inc('redis_cache_invalidations_total', pattern=pattern)
            logger.info(f"Invalidación de caché para patrón '{pattern}': {deleted_count} claves eliminadas")
            return deleted_count
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='invalidate_pattern')
            logger.error(f"Error al invalidar patrón '{pattern}' en Redis: {e}")
            return 0

    # =========================================================================
    # SECURITY & SESSION (FAIL-CLOSED)
    # =========================================================================
    def is_token_revoked(self, jti: str) -> bool:
        """
        Comprueba si el JTI del JWT está en la lista de revocación (jwt:revoked:<jti>).
        FAIL-CLOSED: Si Redis no está disponible, lanza RedisSecurityException.
        """
        try:
            client = self.get_client()
            key = f"jwt:revoked:{jti}"
            val = client.get(key)
            return val is not None
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='is_token_revoked')
            logger.error(f"Fail-Closed: Redis inaccesible al verificar revocación de JTI '{jti}'. Error: {e}")
            raise RedisSecurityException("No se puede verificar la validez del token debido a indisponibilidad de Redis.")

    def revoke_token(self, jti: str, ttl_seconds: int) -> bool:
        """
        Registra un JTI en la lista de revocación con TTL igual a la vida restante del token.
        FAIL-CLOSED: Si Redis falla, lanza RedisSecurityException.
        """
        try:
            client = self.get_client()
            key = f"jwt:revoked:{jti}"
            ttl = max(1, int(ttl_seconds))
            client.set(key, "1", ex=ttl)
            metrics.inc('jwt_revoked_total')
            logger.info(f"JTI '{jti}' revocado exitosamente por {ttl} segundos")
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='revoke_token')
            logger.error(f"Fail-Closed: Error al registrar revocación de JTI '{jti}'. Error: {e}")
            raise RedisSecurityException("No se pudo registrar la revocación del token en Redis.")

    def save_session(self, user_id: int, session_data: dict, ttl_seconds: Optional[int] = None) -> bool:
        """
        Almacena la sesión de usuario en Redis (session:<user_id>).
        FAIL-CLOSED: Si Redis falla, lanza RedisSecurityException.
        """
        try:
            client = self.get_client()
            key = f"session:{user_id}"
            ttl = ttl_seconds if ttl_seconds is not None else config.SESSION_TTL_SECONDS
            client.set(key, _serialize_to_json(session_data), ex=ttl)
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='save_session')
            logger.error(f"Fail-Closed: Error al guardar sesión de usuario {user_id}: {e}")
            raise RedisSecurityException("No se pudo guardar la sesión de usuario en Redis.")

    def get_session(self, user_id: int) -> Optional[dict]:
        """
        Obtiene los datos de sesión de Redis.
        FAIL-CLOSED: Si Redis falla, lanza RedisSecurityException.
        """
        try:
            client = self.get_client()
            key = f"session:{user_id}"
            val = client.get(key)
            if val is not None:
                return json.loads(val)
            return None
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='get_session')
            logger.error(f"Fail-Closed: Error al obtener sesión de usuario {user_id}: {e}")
            raise RedisSecurityException("No se pudo consultar la sesión en Redis.")

    def delete_session(self, user_id: int) -> bool:
        """Elimina la sesión del usuario en Redis."""
        try:
            client = self.get_client()
            key = f"session:{user_id}"
            client.delete(key)
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='delete_session')
            logger.warning(f"Error al eliminar sesión de usuario {user_id}: {e}")
            return False

    def save_refresh_token(self, token: str, user_id: int, ttl_seconds: Optional[int] = None) -> bool:
        """Guarda un refresh token en Redis con mapeo hacia el user_id."""
        try:
            client = self.get_client()
            key = f"refresh:{token}"
            ttl = ttl_seconds if ttl_seconds is not None else config.REFRESH_TTL_SECONDS
            client.set(key, str(user_id), ex=ttl)
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='save_refresh_token')
            logger.error(f"Fail-Closed: Error al almacenar refresh token: {e}")
            raise RedisSecurityException("No se pudo guardar el refresh token en Redis.")

    def get_refresh_token(self, token: str) -> Optional[int]:
        """Obtiene el user_id asociado a un refresh token."""
        try:
            client = self.get_client()
            key = f"refresh:{token}"
            val = client.get(key)
            return int(val) if val is not None else None
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='get_refresh_token')
            logger.error(f"Fail-Closed: Error al validar refresh token: {e}")
            raise RedisSecurityException("No se pudo verificar el refresh token en Redis.")

    def delete_refresh_token(self, token: str) -> bool:
        """Revoca/elimina un refresh token de Redis."""
        try:
            client = self.get_client()
            key = f"refresh:{token}"
            client.delete(key)
            return True
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='delete_refresh_token')
            logger.warning(f"Error al eliminar refresh token: {e}")
            return False

    # =========================================================================
    # IDEMPOTENCIA Y TAREAS TEMPORALES
    # =========================================================================
    def acquire_idempotency_key(self, key: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Adquiere una clave de idempotencia atómica (SET NX EX).
        Retorna True si es la primera vez que se procesa la clave, False si ya existía.
        """
        try:
            client = self.get_client()
            ttl = ttl_seconds if ttl_seconds is not None else config.IDEMPOTENCY_TTL_SECONDS
            # set con nx=True retorna True si la clave fue establecida, None si ya existía
            acquired = client.set(f"idempotency:{key}", "processing", ex=ttl, nx=True)
            return bool(acquired)
        except (RedisError, Exception) as e:
            metrics.inc('redis_errors_total', operation='acquire_idempotency_key')
            logger.error(f"Fail-Closed: Error al verificar clave de idempotencia '{key}': {e}")
            raise RedisSecurityException("No se pudo verificar idempotencia en Redis.")

    def set_idempotency_result(self, key: str, result_data: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Guarda el resultado de la operación idempotente."""
        try:
            client = self.get_client()
            ttl = ttl_seconds if ttl_seconds is not None else config.IDEMPOTENCY_TTL_SECONDS
            client.set(f"idempotency:{key}", _serialize_to_json(result_data), ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Error al guardar resultado de idempotencia '{key}': {e}")
            return False

    def get_idempotency_result(self, key: str) -> Optional[Any]:
        """Recupera el resultado de una operación previamente procesada."""
        try:
            client = self.get_client()
            val = client.get(f"idempotency:{key}")
            if val and val != "processing":
                return json.loads(val)
            return None
        except Exception as e:
            logger.warning(f"Error al consultar resultado de idempotencia '{key}': {e}")
            return None


# Instancia singleton del cliente Redis compartido
redis_client = RedisClient()
