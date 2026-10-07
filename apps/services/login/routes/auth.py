"""
routes/auth.py
Endpoints de autenticación: /register, /login, /logout, /verify-email
"""
import random
import re
import secrets
import unicodedata
import os
import sys
from datetime import datetime, timezone, timedelta

_SERVICES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

import bcrypt
from flask import Blueprint, request, session
import jwt

from db import get_connection
from helpers.response import make_response_format
from helpers.mailer import send_verification_email
from config import JWT_SECRET, JWT_EXPIRY_MINUTES
from common import (
    redis_client,
    RedisSecurityException,
    issue_access_token,
    issue_refresh_token,
    revoke_jwt
)

auth_bp = Blueprint('auth', __name__)

# Regex para validar formato de email
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
)

# Duración del token de verificación
TOKEN_EXPIRY_HOURS = 24


def _normalize_for_username(text):
    """Elimina acentos y caracteres especiales para generar un username limpio."""
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = nfkd.encode('ascii', 'ignore').decode('ascii')
    return ascii_text.lower().strip()


def _generate_username(nombre, apellido_paterno):
    """
    Genera un username único tipo 'juan.perez'.
    Si ya existe, agrega sufijo numérico: 'juan.perez2', 'juan.perez3', etc.
    """
    base_nombre = _normalize_for_username(nombre)
    base_apellido = _normalize_for_username(apellido_paterno)
    base_username = f"{base_nombre}.{base_apellido}"

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Verificar si el username base está disponible
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE username = %s",
                (base_username,)
            )
            count = cur.fetchone()[0]
            if count == 0:
                return base_username

            # Buscar el mayor sufijo existente
            cur.execute(
                "SELECT username FROM users WHERE username LIKE %s",
                (f"{base_username}%",)
            )
            existing = [row[0] for row in cur.fetchall()]

            suffix = 2
            while f"{base_username}{suffix}" in existing:
                suffix += 1
            return f"{base_username}{suffix}"


# -----------------------------------------------------------------
# GET /captcha
# -----------------------------------------------------------------
@auth_bp.route('/captcha', methods=['GET'])
def get_captcha():
    """Generar un desafío CAPTCHA para verificación humana."""
    num1 = random.randint(1, 15)
    num2 = random.randint(1, 15)
    question = f"¿Cuánto es {num1} + {num2}?"
    answer = str(num1 + num2)
    captcha_id = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO captcha_challenges (id, question, answer, expires_at)
                   VALUES (%s, %s, %s, %s)""",
                (captcha_id, question, answer, expires_at)
            )
            conn.commit()

    return make_response_format({
        'status': 'success',
        'captcha_id': captcha_id,
        'challenge': question,
        'expires_in_seconds': 300
    }, 200, request)


# -----------------------------------------------------------------
# POST /register
# -----------------------------------------------------------------
@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrar un nuevo usuario y enviar email de verificación."""
    # Aceptar datos como JSON o form-data
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    nombre = data.get('nombre', '').strip()
    apellido_paterno = data.get('apellido_paterno', '').strip()
    apellido_materno = data.get('apellido_materno', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    captcha_id = data.get('captcha_id', '').strip()
    captcha_answer = str(data.get('captcha_answer', '')).strip()

    # --- Validaciones ---
    errors = []
    if not nombre:
        errors.append('El campo nombre es obligatorio.')
    if not apellido_paterno:
        errors.append('El campo apellido_paterno es obligatorio.')
    if not email:
        errors.append('El campo email es obligatorio.')
    elif not EMAIL_REGEX.match(email):
        errors.append('El formato del email no es válido.')
    if not password:
        errors.append('El campo password es obligatorio.')
    elif len(password) < 8:
        errors.append('La contraseña debe tener al menos 8 caracteres.')
    # Verificación de humano (si se envía captcha)
    if captcha_id or captcha_answer:
        if not captcha_id or not captcha_answer:
            errors.append('Para verificación de humano se requieren ambos campos: captcha_id y captcha_answer.')

    if errors:
        return make_response_format({
            'status': 'error',
            'errors': errors
        }, 400, request)

    # --- Validar CAPTCHA contra la BD (si se proporcionó) ---
    if captcha_id and captcha_answer:
        now = datetime.now(timezone.utc)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT answer, expires_at, used
                       FROM captcha_challenges
                       WHERE id = %s""",
                    (captcha_id,)
                )
                row = cur.fetchone()

                if row is None:
                    return make_response_format({
                        'status': 'error',
                        'message': 'El captcha_id no existe. Solicite uno nuevo con GET /captcha.'
                    }, 400, request)

                db_answer, db_expires, db_used = row
                if db_expires.tzinfo is None:
                    db_expires = db_expires.replace(tzinfo=timezone.utc)

                if db_used:
                    return make_response_format({
                        'status': 'error',
                        'message': 'Este CAPTCHA ya fue utilizado. Solicite uno nuevo con GET /captcha.'
                    }, 400, request)

                if now > db_expires:
                    return make_response_format({
                        'status': 'error',
                        'message': 'El CAPTCHA ha expirado. Solicite uno nuevo con GET /captcha.'
                    }, 400, request)

                if captcha_answer != db_answer:
                    return make_response_format({
                        'status': 'error',
                        'message': 'Verificación de humano fallida: la respuesta al CAPTCHA es incorrecta.'
                    }, 400, request)

                # Marcar captcha como usado
                cur.execute(
                    "UPDATE captcha_challenges SET used = true WHERE id = %s",
                    (captcha_id,)
                )
                conn.commit()

    # --- Verificar unicidad de email ---
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return make_response_format({
                    'status': 'error',
                    'message': 'El email ya está registrado.'
                }, 409, request)

    # --- Generar username automático ---
    username = _generate_username(nombre, apellido_paterno)

    # --- Hash de contraseña (bcrypt, compatible con bcryptjs de Node.js) ---
    password_hash = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt(rounds=10)
    ).decode('utf-8')

    # --- Insertar usuario vía stored procedure ---
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sp_register_user(%s, %s, %s, %s, %s, %s)",
                (username, email, password_hash,
                 nombre, apellido_paterno, apellido_materno or None)
            )
            user_id = cur.fetchone()[0]

            # --- Generar token de verificación ---
            token = secrets.token_urlsafe(64)
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=TOKEN_EXPIRY_HOURS
            )
            cur.execute(
                """INSERT INTO email_verification_tokens
                   (user_id, token, expires_at)
                   VALUES (%s, %s, %s)""",
                (user_id, token, expires_at)
            )
            conn.commit()

    # --- Enviar email de verificación vía Postfix ---
    try:
        send_verification_email(email, token, nombre)
    except Exception as e:
        # El usuario se creó, pero el correo falló.
        # No revertimos el registro; el usuario puede solicitar reenvío.
        return make_response_format({
            'status': 'warning',
            'message': (
                'Usuario registrado, pero no se pudo enviar el correo '
                'de verificación. Contacte al administrador.'
            ),
            'user_id': user_id,
            'username': username,
            'mail_error': str(e)
        }, 201, request)

    return make_response_format({
        'status': 'success',
        'message': (
            'Registro exitoso. Revise su correo electrónico para '
            'verificar su cuenta.'
        ),
        'user_id': user_id,
        'username': username
    }, 201, request)


# -----------------------------------------------------------------
# GET /verify-email?token=xxx and GET /verify?token=xxx
# -----------------------------------------------------------------
@auth_bp.route('/verify-email', methods=['GET'])
@auth_bp.route('/verify', methods=['GET'])
def verify_email():
    """Verificar email del usuario mediante token."""
    token = request.args.get('token', '').strip()

    if not token:
        return make_response_format({
            'status': 'error',
            'message': 'Token de verificación no proporcionado.'
        }, 400, request)

    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Buscar token válido
            cur.execute(
                """SELECT id, user_id, expires_at, used
                   FROM email_verification_tokens
                   WHERE token = %s""",
                (token,)
            )
            row = cur.fetchone()

            if row is None:
                return make_response_format({
                    'status': 'error',
                    'message': 'Token de verificación inválido.'
                }, 400, request)

            token_id, user_id, expires_at, used = row

            if used:
                return make_response_format({
                    'status': 'error',
                    'message': 'Este token ya fue utilizado.'
                }, 400, request)

            # Asegurar timezone-awareness para comparar
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if now > expires_at:
                return make_response_format({
                    'status': 'error',
                    'message': (
                        'El token de verificación ha expirado. '
                        'Solicite uno nuevo.'
                    )
                }, 400, request)

            # Activar cuenta
            cur.execute(
                "UPDATE users SET email_verified = true WHERE id = %s",
                (user_id,)
            )
            cur.execute(
                "UPDATE email_verification_tokens SET used = true WHERE id = %s",
                (token_id,)
            )
            conn.commit()

    return make_response_format({
        'status': 'success',
        'message': 'Email verificado exitosamente. Ya puede iniciar sesión.'
    }, 200, request)


# -----------------------------------------------------------------
# POST /login
# -----------------------------------------------------------------
@auth_bp.route('/login', methods=['POST'])
def login():
    """Autenticar usuario e iniciar sesión."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return make_response_format({
            'status': 'error',
            'message': 'Email y password son obligatorios.'
        }, 400, request)

    # Buscar usuario por email
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, username, email, password_hash, role,
                          nombre, apellido_paterno, apellido_materno,
                          email_verified
                   FROM users WHERE email = %s""",
                (email,)
            )
            row = cur.fetchone()

    if row is None:
        return make_response_format({
            'status': 'error',
            'message': 'Credenciales inválidas.'
        }, 401, request)

    (user_id, username, user_email, password_hash, role,
     nombre, apellido_paterno, apellido_materno, email_verified) = row

    # Verificar contraseña
    if not bcrypt.checkpw(
        password.encode('utf-8'),
        password_hash.encode('utf-8')
    ):
        return make_response_format({
            'status': 'error',
            'message': 'Credenciales inválidas.'
        }, 401, request)

    # Verificar que el email esté confirmado
    if not email_verified:
        return make_response_format({
            'status': 'error',
            'message': (
                'Su email no ha sido verificado. '
                'Revise su correo electrónico.'
            )
        }, 403, request)

    # Crear sesión Flask para compatibilidad
    session.clear()
    session['user_id'] = user_id
    session['username'] = username
    session['email'] = user_email
    session['role'] = role
    session['nombre'] = nombre
    session['last_activity'] = datetime.now(timezone.utc).isoformat()

    # Construir diccionario de usuario para emisión de JWT
    role_id = 1 if role == 'admin' else 2
    user_dict = {
        'id': user_id,
        'user_id': user_id,
        'username': username,
        'email': user_email,
        'nombre': nombre or '',
        'apellido_paterno': apellido_paterno or '',
        'apellido_materno': apellido_materno or '',
        'role': role,
        'role_id': role_id
    }

    # Emitir Access Token (20 min) y Refresh Token (7 días)
    token, payload = issue_access_token(user_dict)
    try:
        refresh_token = issue_refresh_token(user_id)
    except RedisSecurityException as r_err:
        return make_response_format({
            'status': 'error',
            'message': 'No se pudo generar el refresh token en Redis.'
        }, 503, request)

    # Guardar sesión en Redis con TTL de 20 minutos (1200 segundos)
    session_data = {
        'user_id': user_id,
        'username': username,
        'email': user_email,
        'role': role,
        'role_id': role_id,
        'nombre': nombre or '',
        'jti': payload['jti'],
        'login_at': datetime.now(timezone.utc).isoformat()
    }
    try:
        redis_client.save_session(user_id, session_data, ttl_seconds=1200)
    except RedisSecurityException as r_err:
        return make_response_format({
            'status': 'error',
            'message': 'No se pudo guardar la sesión de usuario en Redis.'
        }, 503, request)

    # --- Log en consola ---
    print(f"\n{'='*60}")
    print(f"[AUTH+REDIS] [OK] Sesión y tokens emitidos para: {username} ({user_email})")
    print(f"[AUTH+REDIS]      user_id: {user_id} | role: {role} (id={role_id}) | JTI: {payload['jti']}")
    print(f"[AUTH+REDIS]      Access Token TTL: 20 min | Refresh Token TTL: 7 días")
    print(f"{'='*60}\n")

    return make_response_format({
        'status': 'success',
        'message': 'Inicio de sesión exitoso.',
        'token': token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 1200,
        'user': user_dict
    }, 200, request)


# -----------------------------------------------------------------
# POST /logout
# -----------------------------------------------------------------
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Cerrar la sesión del usuario, revocar JWT en Redis y limpiar sesión."""
    auth_header = request.headers.get('Authorization', '').strip()
    token_to_revoke = None
    if auth_header.startswith('Bearer '):
        token_to_revoke = auth_header[7:].strip()
    elif request.is_json:
        token_to_revoke = (request.get_json(silent=True) or {}).get('token')

    # Revocar JWT en Redis si existe
    if token_to_revoke:
        try:
            revoke_jwt(token_to_revoke)
            print(f"[AUTH+REDIS] [LOGOUT] JTI revocado para token: {token_to_revoke[:30]}...")
        except Exception as e:
            print(f"[AUTH+REDIS] [LOGOUT] Advertencia al revocar JWT: {e}")

    # Obtener user_id
    user_id = session.get('user_id')
    if not user_id and token_to_revoke:
        try:
            unverified = jwt.decode(token_to_revoke, options={"verify_signature": False})
            user_id = unverified.get('user_id') or unverified.get('sub')
        except Exception:
            pass

    # Eliminar sesión en Redis
    if user_id:
        try:
            redis_client.delete_session(int(user_id))
            print(f"[AUTH+REDIS] [LOGOUT] Sesión en Redis eliminada para user_id {user_id}")
        except Exception as e:
            print(f"[AUTH+REDIS] [LOGOUT] Advertencia al borrar sesión de Redis: {e}")

    if 'user_id' not in session and not token_to_revoke:
        return make_response_format({
            'status': 'error',
            'message': 'No hay sesión activa.'
        }, 401, request)

    session.clear()

    return make_response_format({
        'status': 'success',
        'message': 'Sesión cerrada exitosamente.'
    }, 200, request)


# -----------------------------------------------------------------
# GET and PATCH /profile
# -----------------------------------------------------------------
@auth_bp.route('/profile', methods=['GET', 'PATCH'])
def profile():
    """Consultar o actualizar el perfil del usuario autenticado (soporta JWT o sesión)."""
    user_id = None

    # 1. Intentar autenticar mediante JWT (Authorization: Bearer <token>)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('sub')
            print(f"[JWT] [OK] /profile -- Autenticado via JWT para usuario ID: {user_id}")
        except jwt.ExpiredSignatureError:
            print(f"[JWT] [EXPIRED] /profile -- Token JWT expirado")
            return make_response_format({
                'status': 'error',
                'message': 'Token JWT expirado. Inicie sesion nuevamente.'
            }, 401, request)
        except jwt.InvalidTokenError as e:
            print(f"[JWT] [ERROR] /profile -- Token JWT invalido: {e}")
            return make_response_format({
                'status': 'error',
                'message': f'Token JWT invalido: {e}'
            }, 401, request)

    # 2. Fallback a sesión Flask
    if not user_id and 'user_id' in session:
        user_id = session['user_id']

    if not user_id:
        return make_response_format({
            'status': 'error',
            'message': 'No hay sesión activa ni token JWT válido. Acceso no autorizado.'
        }, 401, request)

    if request.method == 'GET':
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, username, email, role,
                              nombre, apellido_paterno, apellido_materno, created_at
                       FROM users WHERE id = %s""",
                    (user_id,)
                )
                row = cur.fetchone()

        if not row:
            return make_response_format({
                'status': 'error',
                'message': 'Usuario no encontrado.'
            }, 404, request)

        return make_response_format({
            'status': 'success',
            'user': {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'role': row[3],
                'nombre': row[4],
                'apellido_paterno': row[5],
                'apellido_materno': row[6],
                'created_at': row[7].isoformat() if row[7] else None
            }
        }, 200, request)

    # --- PATCH: Actualización parcial del perfil ---
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    updates = []
    params = []

    # Nombre
    if 'nombre' in data:
        nombre_val = str(data['nombre']).strip()
        updates.append("nombre = %s")
        params.append(nombre_val)
        session['nombre'] = nombre_val

    # Apellidos
    if 'apellido_paterno' in data:
        ap_val = str(data['apellido_paterno']).strip()
        updates.append("apellido_paterno = %s")
        params.append(ap_val)
        session['apellido_paterno'] = ap_val

    if 'apellido_materno' in data:
        am_val = str(data['apellido_materno']).strip()
        updates.append("apellido_materno = %s")
        params.append(am_val)
        session['apellido_materno'] = am_val

    # Email
    if 'email' in data:
        new_email = str(data['email']).strip().lower()
        if not EMAIL_REGEX.match(new_email):
            return make_response_format({
                'status': 'error',
                'message': 'El formato del email no es válido.'
            }, 400, request)

        # Validar si ya lo usa otro usuario
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s AND id != %s", (new_email, user_id))
                if cur.fetchone():
                    return make_response_format({
                        'status': 'error',
                        'message': 'El correo electrónico ya está registrado por otro usuario.'
                    }, 409, request)

        updates.append("email = %s")
        params.append(new_email)
        session['email'] = new_email

    # Contraseña
    if 'password' in data and data['password']:
        new_pass = str(data['password'])
        if len(new_pass) < 8:
            return make_response_format({
                'status': 'error',
                'message': 'La contraseña debe tener al menos 8 caracteres.'
            }, 400, request)
        pwd_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt(rounds=10)).decode('utf-8')
        updates.append("password_hash = %s")
        params.append(pwd_hash)

    if not updates:
        return make_response_format({
            'status': 'warning',
            'message': 'No se enviaron campos para actualizar.'
        }, 200, request)

    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING id, username, email, role, nombre, apellido_paterno, apellido_materno"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            conn.commit()

    return make_response_format({
        'status': 'success',
        'message': 'Perfil actualizado correctamente.',
        'user': {
            'id': row[0],
            'username': row[1],
            'email': row[2],
            'role': row[3],
            'nombre': row[4],
            'apellido_paterno': row[5],
            'apellido_materno': row[6]
        }
    }, 200, request)


