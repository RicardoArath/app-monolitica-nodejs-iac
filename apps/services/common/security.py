"""
common/security.py
Autenticación y Autorización basada en JWT con lista de revocación en Redis (JTI) y RBAC.

Reglas:
  - Algoritmo: HS256
  - Expiración: 20 minutos (1200 segundos)
  - Clave compartida: JWT_SECRET_KEY compartida por variable de entorno
  - Claims obligatorios: sub, user_id, username, email, role, role_id, jti, iat, exp
  - Fail-Closed: Si Redis no está disponible para verificar revocación (jwt:revoked:<jti>),
    se rechaza la petición con HTTP 503 Service Unavailable.
"""
from datetime import datetime, timezone, timedelta
from functools import wraps
import secrets
import time
import uuid

import jwt
from flask import request, g

from common import config, metrics
from common.logging_utils import get_logger
from common.redis_client import redis_client, RedisSecurityException
from common.response import make_response_format

logger = get_logger('common.security')


def issue_access_token(user_dict: dict) -> tuple:
    """
    Genera un Access Token JWT (HS256) con vigencia de 20 minutos y claims completos.
    Retorna (token_jwt, payload_dict).
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=config.ACCESS_TOKEN_MINUTES)
    jti = str(uuid.uuid4())

    user_id = int(user_dict.get('id') or user_dict.get('user_id') or user_dict.get('sub'))
    role = user_dict.get('role', 'user').lower()
    role_id = user_dict.get('role_id') or (config.ROLE_ADMIN if role == 'admin' else config.ROLE_USER)

    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'username': user_dict.get('username', ''),
        'email': user_dict.get('email', ''),
        'role': role,
        'role_id': int(role_id),
        'nombre': user_dict.get('nombre', ''),
        'jti': jti,
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp())
    }

    token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    metrics.inc('jwt_issued_total')
    logger.info(f"JWT emitido para usuario '{payload['username']}' (role={role}, jti={jti})")
    return token, payload


def issue_refresh_token(user_id: int) -> str:
    """
    Genera un Refresh Token seguro de 64 caracteres y lo guarda en Redis con TTL de 7 días.
    """
    token = secrets.token_urlsafe(48)
    redis_client.save_refresh_token(token, user_id, ttl_seconds=config.REFRESH_TTL_SECONDS)
    return token


def revoke_jwt(token_str: str) -> bool:
    """
    Extrae el JTI y expiración del JWT y lo agrega a la lista de revocación en Redis.
    """
    try:
        # Decodificar sin verificar expiración por si ya expiró justo ahora
        unverified = jwt.decode(
            token_str,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        jti = unverified.get('jti')
        exp = unverified.get('exp', 0)
        now_ts = int(time.time())

        # Si aún le queda tiempo de vida al token, fijar ese TTL en Redis
        remaining_ttl = max(60, exp - now_ts)
        if jti:
            return redis_client.revoke_token(jti, remaining_ttl)
        return False
    except Exception as e:
        logger.error(f"Error al revocar JWT: {e}")
        return False


def jwt_required(optional: bool = False):
    """
    Middleware / Decorador que valida el JWT de acceso.
    Verifica firma, expiración y comprueba en Redis que el JTI NO esté revocado.
    Si optional=True, no rechaza si falta el token pero sí lo valida si viene presente.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '').strip()
            token = None

            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                else:
                    metrics.inc('jwt_rejected_total', reason='bad_format')
                    return make_response_format({
                        'status': 'error',
                        'message': 'Formato de autorización inválido. Debe ser: Authorization: Bearer <token>'
                    }, 401, request)

            if not token:
                if optional:
                    g.jwt_user = None
                    return f(*args, **kwargs)
                metrics.inc('jwt_rejected_total', reason='missing_token')
                return make_response_format({
                    'status': 'error',
                    'message': 'Acceso denegado. Se requiere encabezado Authorization: Bearer <token>'
                }, 401, request)

            # Validar firma y tiempo del token
            try:
                payload = jwt.decode(
                    token,
                    config.JWT_SECRET_KEY,
                    algorithms=[config.JWT_ALGORITHM]
                )
            except jwt.ExpiredSignatureError:
                metrics.inc('jwt_rejected_total', reason='expired')
                return make_response_format({
                    'status': 'error',
                    'message': 'El token JWT ha expirado. Por favor, renuévelo o inicie sesión nuevamente.'
                }, 401, request)
            except jwt.InvalidTokenError as e:
                metrics.inc('jwt_rejected_total', reason='invalid_signature')
                return make_response_format({
                    'status': 'error',
                    'message': f'Token JWT inválido: {str(e)}'
                }, 401, request)

            # Validar revocación en Redis (Fail-Closed)
            jti = payload.get('jti')
            if jti:
                try:
                    if redis_client.is_token_revoked(jti):
                        metrics.inc('jwt_rejected_total', reason='revoked')
                        logger.warning(f"Rechazado JWT con JTI revocado: {jti}")
                        return make_response_format({
                            'status': 'error',
                            'message': 'Token JWT revocado (sesión cerrada).'
                        }, 401, request)
                except RedisSecurityException as e:
                    # Fail-Closed: si no se puede verificar revocación, 503
                    logger.error(f"Fail-Closed activado en verificación de revocación: {e}")
                    return make_response_format({
                        'status': 'error',
                        'message': 'Servicio de autenticación temporalmente no disponible (Fail-Closed en verificación de seguridad).'
                    }, 503, request)

            g.jwt_user = payload
            g.raw_token = token
            return f(*args, **kwargs)

        return decorated_function
    return decorator


def roles_required(*allowed_roles):
    """
    Decorador RBAC para restringir endpoints a roles específicos (ej. @roles_required('admin')).
    Debe utilizarse en combinación con @jwt_required().
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, 'jwt_user', None)
            if not user:
                return make_response_format({
                    'status': 'error',
                    'message': 'No autenticado.'
                }, 401, request)

            user_role = (user.get('role') or '').lower()
            allowed = [r.lower() for r in allowed_roles]

            if user_role not in allowed:
                logger.warning(
                    f"Acceso denegado: Usuario '{user.get('username')}' con rol '{user_role}' "
                    f"intentó acceder a recurso reservado para {allowed}"
                )
                return make_response_format({
                    'status': 'error',
                    'message': 'Acceso prohibido: Privilegios insuficientes para esta operación.'
                }, 403, request)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
