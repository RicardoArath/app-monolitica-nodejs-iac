"""
routes/session.py
Endpoints de gestión de sesión: /session, /session/renew con soporte dual (Cookies y JWT con Redis).
"""
import sys, os
_SERVICES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

from datetime import datetime, timezone
import time
import jwt
from flask import Blueprint, request, session

from config import SESSION_LIFETIME_MINUTES, SESSION_WARNING_MINUTES
from common import (
    config as common_config,
    redis_client,
    RedisSecurityException,
    make_response_format,
    issue_access_token
)


session_bp = Blueprint('session', __name__)

SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_MINUTES * 60
SESSION_WARNING_SECONDS = SESSION_WARNING_MINUTES * 60


@session_bp.route('/session', methods=['GET', 'POST'])
def get_session():
    """
    Consulta si existe una sesión activa y su estado.
    Soporta tanto sesión basada en Cookies como token JWT en header Authorization: Bearer <token>.
    """
    token = None
    auth_header = request.headers.get('Authorization', '').strip()
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()

    # Caso 1: Se proporcionó token JWT
    if token:
        try:
            payload = jwt.decode(token, common_config.JWT_SECRET_KEY, algorithms=[common_config.JWT_ALGORITHM])
            jti = payload.get('jti')

            # Verificar si está revocado en Redis
            if jti:
                try:
                    if redis_client.is_token_revoked(jti):
                        return make_response_format({
                            'status': 'session_expired',
                            'message': 'El token JWT ha sido revocado.'
                        }, 401, request)
                except RedisSecurityException:
                    return make_response_format({
                        'status': 'error',
                        'message': 'Redis no disponible para validar sesión (Fail-Closed).'
                    }, 503, request)

            user_id = int(payload.get('user_id') or payload.get('sub'))
            now_ts = int(time.time())
            exp_ts = payload.get('exp', now_ts)
            remaining = max(0, exp_ts - now_ts)

            if remaining <= 0:
                return make_response_format({
                    'status': 'session_expired',
                    'message': 'El token JWT ha expirado.'
                }, 401, request)

            # Umbral de advertencia para renovación
            status = 'expiring' if remaining <= common_config.TOKEN_RENEW_THRESHOLD_SECONDS else 'active'

            return make_response_format({
                'status': status,
                'message': 'Sesión activa (JWT).' if status == 'active' else 'El token expirará pronto. Renuévelo.',
                'remaining_seconds': remaining,
                'session_lifetime_minutes': common_config.ACCESS_TOKEN_MINUTES,
                'auth_type': 'jwt_bearer',
                'user': {
                    'id': user_id,
                    'username': payload.get('username'),
                    'email': payload.get('email'),
                    'nombre': payload.get('nombre'),
                    'role': payload.get('role'),
                    'role_id': payload.get('role_id')
                }
            }, 200, request)

        except jwt.ExpiredSignatureError:
            return make_response_format({
                'status': 'session_expired',
                'message': 'El token JWT ha expirado.'
            }, 401, request)
        except jwt.InvalidTokenError as e:
            return make_response_format({
                'status': 'error',
                'message': f'Token JWT inválido: {str(e)}'
            }, 401, request)

    # Caso 2: Sesión por Cookies Flask
    if 'user_id' not in session:
        return make_response_format({
            'status': 'no_session',
            'message': 'No hay sesión activa.'
        }, 401, request)

    last_activity = session.get('last_activity')
    if isinstance(last_activity, str):
        last_activity = datetime.fromisoformat(last_activity)
    if last_activity and last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    elapsed = (now - last_activity).total_seconds() if last_activity else 999999
    remaining = max(0, SESSION_LIFETIME_SECONDS - elapsed)

    if remaining <= 0:
        session.clear()
        return make_response_format({
            'status': 'session_expired',
            'message': 'Su sesión ha expirado por inactividad.'
        }, 440, request)

    status = 'expiring' if remaining <= SESSION_WARNING_SECONDS else 'active'

    return make_response_format({
        'status': status,
        'message': 'Sesión activa (Cookie).' if status == 'active' else 'Su sesión expirará pronto.',
        'remaining_seconds': int(remaining),
        'session_lifetime_minutes': SESSION_LIFETIME_MINUTES,
        'auth_type': 'cookie_session',
        'user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'email': session.get('email'),
            'nombre': session.get('nombre'),
            'role': session.get('role')
        }
    }, 200, request)


@session_bp.route('/session/renew', methods=['POST'])
@session_bp.route('/session/extend', methods=['POST'])
def renew_session():
    """Renovar la sesión (Cookie o JWT con Redis)."""
    token = None
    auth_header = request.headers.get('Authorization', '').strip()
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
    elif request.is_json:
        token = (request.get_json(silent=True) or {}).get('token')

    # Caso 1: Renovación con JWT
    if token:
        try:
            payload = jwt.decode(token, common_config.JWT_SECRET_KEY, algorithms=[common_config.JWT_ALGORITHM])
            jti = payload.get('jti')
            if jti:
                try:
                    if redis_client.is_token_revoked(jti):
                        return make_response_format({
                            'status': 'session_expired',
                            'message': 'El token JWT ha sido revocado.'
                        }, 401, request)
                except RedisSecurityException:
                    return make_response_format({
                        'status': 'error',
                        'message': 'Redis no disponible (Fail-Closed).'
                    }, 503, request)

            user_id = int(payload.get('user_id') or payload.get('sub'))
            user_dict = {
                'id': user_id,
                'user_id': user_id,
                'username': payload.get('username'),
                'email': payload.get('email'),
                'nombre': payload.get('nombre'),
                'apellido_paterno': payload.get('apellido_paterno', ''),
                'apellido_materno': payload.get('apellido_materno', ''),
                'role': payload.get('role'),
                'role_id': payload.get('role_id', 1 if payload.get('role') == 'admin' else 2)
            }
            new_token, new_payload = issue_access_token(user_dict)

            # Actualizar sesión en Redis con TTL de 20 min
            session_data = {
                'user_id': user_id,
                'username': user_dict['username'],
                'email': user_dict['email'],
                'role': user_dict['role'],
                'role_id': user_dict['role_id'],
                'nombre': user_dict['nombre'],
                'jti': new_payload['jti'],
                'login_at': datetime.now(timezone.utc).isoformat()
            }
            try:
                redis_client.save_session(user_id, session_data, ttl_seconds=1200)
            except Exception:
                pass

            return make_response_format({
                'status': 'success',
                'message': 'Token JWT renovado exitosamente.',
                'token': new_token,
                'expires_in': 1200,
                'remaining_seconds': 1200,
                'session_lifetime_minutes': common_config.ACCESS_TOKEN_MINUTES,
                'user': user_dict
            }, 200, request)
        except jwt.ExpiredSignatureError:
            return make_response_format({
                'status': 'session_expired',
                'message': 'El token JWT ha expirado. Inicie sesión nuevamente.'
            }, 401, request)
        except jwt.InvalidTokenError as e:
            return make_response_format({
                'status': 'error',
                'message': f'Token JWT inválido: {e}'
            }, 401, request)

    # Caso 2: Renovación de sesión por Cookie Flask
    if 'user_id' not in session:
        return make_response_format({
            'status': 'no_session',
            'message': 'No hay sesión activa para renovar.'
        }, 401, request)

    session['last_activity'] = datetime.now(timezone.utc).isoformat()
    return make_response_format({
        'status': 'success',
        'message': 'Sesión renovada exitosamente.',
        'remaining_seconds': SESSION_LIFETIME_SECONDS,
        'session_lifetime_minutes': SESSION_LIFETIME_MINUTES
    }, 200, request)
