"""
middleware/jwt_guard.py
Decorador @jwt_required para el microservicio API.
Valida el header Authorization: Bearer <token>.
"""
from functools import wraps
import jwt
from flask import request, g

from config import JWT_SECRET
from helpers.response import make_response_format


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header:
            print(f"[JWT-GUARD] ❌ {request.method} {request.path} — Sin header Authorization")
            return make_response_format({
                'status': 'error',
                'message': 'Acceso denegado. Se requiere token JWT en el header Authorization: Bearer <token>.'
            }, 401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            print(f"[JWT-GUARD] ❌ {request.method} {request.path} — Formato incorrecto")
            return make_response_format({
                'status': 'error',
                'message': 'Formato de autorización inválido. Use: Authorization: Bearer <token>'
            }, 401)

        token = parts[1]

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.jwt_user = payload
            print(f"[JWT-GUARD] ✅ {request.method} {request.path} — Token VÁLIDO (usuario: {payload.get('username')})")
            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            print(f"[JWT-GUARD] ⏰ {request.method} {request.path} — Token EXPIRADO")
            return make_response_format({
                'status': 'error',
                'message': 'Token JWT expirado. Inicie sesión nuevamente.'
            }, 401)

        except jwt.InvalidTokenError as e:
            print(f"[JWT-GUARD] ❌ {request.method} {request.path} — Token INVÁLIDO: {str(e)}")
            return make_response_format({
                'status': 'error',
                'message': f'Token JWT inválido: {str(e)}'
            }, 401)

    return decorated
