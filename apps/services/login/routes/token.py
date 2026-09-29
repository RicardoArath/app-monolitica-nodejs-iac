"""
routes/token.py
Endpoints para verificacion y renovacion de tokens JWT.
POST /token/verify  -- Valida un JWT y retorna su payload.
POST /token/refresh -- Emite un nuevo JWT con expiracion renovada.
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
    """Renueva un JWT valido (no expirado) emitiendo uno nuevo con expiracion extendida."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()

    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()

    if not token:
        print("[JWT] [ERROR] /token/refresh -- No se proporciono token")
        return make_response_format({
            'status': 'error',
            'message': 'Token no proporcionado.'
        }, 400, request)

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

        new_payload = {
            'sub': str(payload['sub']),
            'username': payload.get('username'),
            'email': payload.get('email'),
            'role': payload.get('role'),
            'nombre': payload.get('nombre'),
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
        }
        new_token = jwt.encode(new_payload, JWT_SECRET, algorithm='HS256')

        print(f"\n{'='*60}")
        print(f"[JWT] [RENEW] TOKEN RENOVADO para usuario: {payload.get('username')}")
        print(f"[JWT]         nueva expiracion: {JWT_EXPIRY_MINUTES} minutos")
        print(f"[JWT]         nuevo token: {new_token[:50]}...")
        print(f"{'='*60}\n")

        return make_response_format({
            'status': 'success',
            'message': 'Token JWT renovado exitosamente.',
            'token': new_token,
            'token_type': 'Bearer',
            'expires_in': JWT_EXPIRY_MINUTES * 60
        }, 200, request)

    except jwt.ExpiredSignatureError:
        print("[JWT] [EXPIRED] /token/refresh -- Token EXPIRADO, no se puede renovar")
        return make_response_format({
            'status': 'error',
            'message': 'El token ha expirado. Inicie sesion nuevamente.'
        }, 401, request)

    except jwt.InvalidTokenError as e:
        print(f"[JWT] [ERROR] /token/refresh -- Token INVALIDO: {str(e)}")
        return make_response_format({
            'status': 'error',
            'message': f'Token JWT invalido: {str(e)}'
        }, 401, request)
