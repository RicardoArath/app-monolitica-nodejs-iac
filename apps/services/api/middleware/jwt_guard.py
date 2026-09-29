"""
middleware/jwt_guard.py
Decorador @jwt_required que protege las rutas de escritura del microservicio de libros.
Valida el header Authorization: Bearer <token> usando el secreto compartido JWT_SECRET.
Si el token es valido, inyecta los datos del usuario en flask.g.jwt_user.
Si el token falta o es invalido, retorna 401 Unauthorized.
"""
from functools import wraps

import jwt
from flask import request, g

from config import JWT_SECRET
from helpers.response import make_response_format


def jwt_required(f):
    """
    Decorador que exige un JWT valido en el header Authorization.
    Uso: @jwt_required sobre cualquier ruta que requiera autenticacion.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header:
            print(f"[JWT-GUARD] [ERROR] {request.method} {request.path} -- Sin header Authorization")
            return make_response_format({
                'status': 'error',
                'message': 'Acceso denegado. Se requiere token JWT en el header Authorization: Bearer <token>.'
            }, 401, request)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            print(f"[JWT-GUARD] [ERROR] {request.method} {request.path} -- Formato incorrecto: {auth_header[:30]}...")
            return make_response_format({
                'status': 'error',
                'message': 'Formato de autorizacion invalido. Use: Authorization: Bearer <token>'
            }, 401, request)

        token = parts[1]

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.jwt_user = payload

            print(f"[JWT-GUARD] [OK] {request.method} {request.path} -- Token VALIDO")
            print(f"[JWT-GUARD]      usuario: {payload.get('username')} | email: {payload.get('email')} | role: {payload.get('role')}")

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            print(f"[JWT-GUARD] [EXPIRED] {request.method} {request.path} -- Token EXPIRADO")
            return make_response_format({
                'status': 'error',
                'message': 'Token JWT expirado. Inicie sesion nuevamente para obtener un nuevo token.'
            }, 401, request)

        except jwt.InvalidTokenError as e:
            print(f"[JWT-GUARD] [ERROR] {request.method} {request.path} -- Token INVALIDO: {str(e)}")
            return make_response_format({
                'status': 'error',
                'message': f'Token JWT invalido: {str(e)}'
            }, 401, request)

    return decorated
