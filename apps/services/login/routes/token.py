"""
routes/token.py
Endpoints para verificacion y renovacion de tokens JWT con soporte para Redis y rotación de Refresh Token.
POST /token/verify  -- Valida un JWT y retorna su payload.
POST /token/refresh -- Emite un nuevo JWT con expiracion renovada (rotando refresh token si se proporciona).
"""
import os
import sys
from datetime import datetime, timezone, timedelta

_SERVICES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

import jwt
from flask import Blueprint, request

from config import JWT_SECRET, JWT_EXPIRY_MINUTES
from helpers.response import make_response_format
from db import get_connection
from common import (
    redis_client,
    RedisSecurityException,
    issue_access_token,
    issue_refresh_token
)

token_bp = Blueprint('token', __name__)


# -----------------------------------------------------------------
# POST /token/verify
# -----------------------------------------------------------------
@token_bp.route('/token/verify', methods=['POST'])
def verify_token():
    """Valida un JWT y retorna los datos del payload si es valido."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()

    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()

    if not token:
        print("[JWT] [ERROR] /token/verify -- No se proporciono token")
        return make_response_format({
            'status': 'error',
            'message': 'Token no proporcionado. Envie {"token": "..."} o header Authorization: Bearer <token>.'
        }, 400, request)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        print(f"[JWT] [OK] /token/verify -- Token VALIDO para usuario: {payload.get('username')} (sub={payload.get('sub')})")
        return make_response_format({
            'status': 'success',
            'message': 'Token JWT valido.',
            'payload': {
                'sub': payload.get('sub'),
                'username': payload.get('username'),
                'email': payload.get('email'),
                'role': payload.get('role'),
                'nombre': payload.get('nombre'),
                'iat': payload.get('iat'),
                'exp': payload.get('exp')
            }
        }, 200, request)

    except jwt.ExpiredSignatureError:
        print("[JWT] [EXPIRED] /token/verify -- Token EXPIRADO")
        return make_response_format({
            'status': 'error',
            'message': 'El token JWT ha expirado. Inicie sesion nuevamente para obtener uno nuevo.'
        }, 401, request)

    except jwt.InvalidTokenError as e:
        print(f"[JWT] [ERROR] /token/verify -- Token INVALIDO: {str(e)}")
        return make_response_format({
            'status': 'error',
            'message': f'Token JWT invalido: {str(e)}'
        }, 401, request)


# -----------------------------------------------------------------
# POST /token/refresh
# -----------------------------------------------------------------
@token_bp.route('/token/refresh', methods=['POST'])
def refresh_token():
    """
    Renueva un Access Token JWT.
    Soporta:
      1. {"refresh_token": "..."}: valida contra Redis, rota el refresh token y emite nuevo Access Token.
      2. {"token": "..."} o Authorization: Bearer <token>: renueva un access token activo existente.
    """
    data = request.get_json(silent=True) or {}

    # Caso 1: Se proporcionó refresh_token para rotación con Redis
    refresh_token_in = data.get('refresh_token', '').strip()
    if refresh_token_in:
        try:
            user_id = redis_client.get_refresh_token(refresh_token_in)
        except RedisSecurityException:
            return make_response_format({
                'status': 'error',
                'message': 'No se pudo verificar el refresh token debido a indisponibilidad de Redis.'
            }, 503, request)

        if not user_id:
            return make_response_format({
                'status': 'error',
                'message': 'Refresh token inválido o expirado.'
            }, 401, request)

        # Rotar el refresh token (eliminar el usado y emitir nuevo)
        try:
            redis_client.delete_refresh_token(refresh_token_in)
            new_refresh_token = issue_refresh_token(user_id)
        except RedisSecurityException:
            return make_response_format({
                'status': 'error',
                'message': 'No se pudo rotar el refresh token en Redis.'
            }, 503, request)

        # Consultar datos del usuario
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, username, email, role,
                              nombre, apellido_paterno, apellido_materno
                       FROM users WHERE id = %s""",
                    (user_id,)
                )
                row = cur.fetchone()

        if not row:
            return make_response_format({
                'status': 'error',
                'message': 'Usuario no encontrado.'
            }, 404, request)

        u_id, u_name, u_email, u_role, u_nom, u_ap, u_am = row
        user_dict = {
            'id': u_id,
            'user_id': u_id,
            'username': u_name,
            'email': u_email,
            'role': u_role,
            'role_id': 1 if u_role == 'admin' else 2,
            'nombre': u_nom or '',
            'apellido_paterno': u_ap or '',
            'apellido_materno': u_am or ''
        }

        new_access_token, _ = issue_access_token(user_dict)

        print(f"\n{'='*60}")
        print(f"[AUTH+REDIS] [REFRESH] Token rotado para user_id {user_id} ({u_name})")
        print(f"[AUTH+REDIS]         Nuevo Refresh Token generado con éxito")
        print(f"{'='*60}\n")

        return make_response_format({
            'status': 'success',
            'message': 'Token JWT renovado exitosamente con rotación de refresh token.',
            'token': new_access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'Bearer',
            'expires_in': 1200
        }, 200, request)

    # Caso 2: Renovación mediante token de acceso vigente
    token = data.get('token', '').strip()
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()

    if not token:
        print("[JWT] [ERROR] /token/refresh -- No se proporciono token ni refresh_token")
        return make_response_format({
            'status': 'error',
            'message': 'Token no proporcionado. Envíe {"refresh_token": "..."} o {"token": "..."}.'
        }, 400, request)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

        user_id = int(payload.get('user_id') or payload.get('sub'))
        role = payload.get('role', 'user')
        user_dict = {
            'id': user_id,
            'user_id': user_id,
            'username': payload.get('username', ''),
            'email': payload.get('email', ''),
            'role': role,
            'role_id': payload.get('role_id', 1 if role == 'admin' else 2),
            'nombre': payload.get('nombre', '')
        }
        new_token, _ = issue_access_token(user_dict)

        print(f"\n{'='*60}")
        print(f"[JWT] [RENEW] TOKEN RENOVADO para usuario: {payload.get('username')}")
        print(f"[JWT]         nuevo token: {new_token[:50]}...")
        print(f"{'='*60}\n")

        return make_response_format({
            'status': 'success',
            'message': 'Token JWT renovado exitosamente.',
            'token': new_token,
            'token_type': 'Bearer',
            'expires_in': 1200
        }, 200, request)

    except jwt.ExpiredSignatureError:
        print("[JWT] [EXPIRED] /token/refresh -- Token EXPIRADO, no se puede renovar")
        return make_response_format({
            'status': 'error',
            'message': 'El token ha expirado. Inicie sesion nuevamente o use refresh_token.'
        }, 401, request)

    except jwt.InvalidTokenError as e:
        print(f"[JWT] [ERROR] /token/refresh -- Token INVALIDO: {str(e)}")
        return make_response_format({
            'status': 'error',
            'message': f'Token JWT invalido: {str(e)}'
        }, 401, request)
