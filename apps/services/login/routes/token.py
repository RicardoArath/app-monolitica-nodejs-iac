"""
routes/token.py
Endpoints para verificación y renovación de tokens JWT.
POST /token/verify  — Valida un JWT y retorna su payload.
POST /token/refresh — Emite un nuevo JWT con expiración renovada.
"""
from datetime import datetime, timezone, timedelta

import jwt
from flask import Blueprint, request

from config import JWT_SECRET, JWT_EXPIRY_MINUTES
from helpers.response import make_response_format

token_bp = Blueprint('token', __name__)


# -----------------------------------------------------------------
# POST /token/verify
# -----------------------------------------------------------------
@token_bp.route('/token/verify', methods=['POST'])
def verify_token():
    """Valida un JWT y retorna los datos del payload si es válido."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()

    if not token:
        # Intentar extraer del header Authorization
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()

    if not token:
        print(f"[JWT] ❌ /token/verify — No se proporcionó token")
        return make_response_format({
            'status': 'error',
            'message': 'Token no proporcionado. Envíe {"token": "..."} o header Authorization: Bearer <token>.'
        }, 400, request)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        print(f"[JWT] ✅ /token/verify — Token VÁLIDO para usuario: {payload.get('username')} (sub={payload.get('sub')})")
        return make_response_format({
            'status': 'success',
            'message': 'Token JWT válido.',
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
        print(f"[JWT] ⏰ /token/verify — Token EXPIRADO")
        return make_response_format({
            'status': 'error',
            'message': 'El token JWT ha expirado. Inicie sesión nuevamente para obtener uno nuevo.'
        }, 401, request)

    except jwt.InvalidTokenError as e:
        print(f"[JWT] ❌ /token/verify — Token INVÁLIDO: {str(e)}")
        return make_response_format({
            'status': 'error',
            'message': f'Token JWT inválido: {str(e)}'
        }, 401, request)


# -----------------------------------------------------------------
# POST /token/refresh
# -----------------------------------------------------------------
@token_bp.route('/token/refresh', methods=['POST'])
def refresh_token():
    """Renueva un JWT válido (no expirado) emitiendo uno nuevo con expiración extendida."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()

    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()

    if not token:
        print(f"[JWT] ❌ /token/refresh — No se proporcionó token")
        return make_response_format({
            'status': 'error',
            'message': 'Token no proporcionado.'
        }, 400, request)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

        # Generar nuevo token con expiración renovada
        new_payload = {
            'sub': payload['sub'],
            'username': payload.get('username'),
            'email': payload.get('email'),
            'role': payload.get('role'),
            'nombre': payload.get('nombre'),
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
        }
        new_token = jwt.encode(new_payload, JWT_SECRET, algorithm='HS256')

        print(f"\n{'='*60}")
        print(f"[JWT] 🔄 TOKEN RENOVADO para usuario: {payload.get('username')}")
        print(f"[JWT]    nueva expiración: {JWT_EXPIRY_MINUTES} minutos")
        print(f"[JWT]    nuevo token: {new_token[:50]}...")
        print(f"{'='*60}\n")

        return make_response_format({
            'status': 'success',
            'message': 'Token JWT renovado exitosamente.',
            'token': new_token,
            'token_type': 'Bearer',
            'expires_in': JWT_EXPIRY_MINUTES * 60
        }, 200, request)

    except jwt.ExpiredSignatureError:
        print(f"[JWT] ⏰ /token/refresh — Token EXPIRADO, no se puede renovar")
        return make_response_format({
            'status': 'error',
            'message': 'El token ha expirado. Inicie sesión nuevamente.'
        }, 401, request)

    except jwt.InvalidTokenError as e:
        print(f"[JWT] ❌ /token/refresh — Token INVÁLIDO: {str(e)}")
        return make_response_format({
            'status': 'error',
            'message': f'Token JWT inválido: {str(e)}'
        }, 401, request)
