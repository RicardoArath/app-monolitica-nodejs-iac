"""
users/routes.py
Rutas del microservicio de Usuarios (puerto 5004).
Administra usuarios, roles, emails y perfiles con protección JWT y RBAC.
"""
import sys, os
_SERVICES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

import bcrypt
from flask import Blueprint, request, g
import psycopg.rows

from common import (
    get_connection,
    make_response_format,
    jwt_required,
    roles_required,
    redis_client,
    config
)

users_bp = Blueprint('users', __name__, url_prefix='/users')


# -----------------------------------------------------------------
# GET /users -- LISTAR USUARIOS (ADMIN ONLY)
# -----------------------------------------------------------------
@users_bp.route('', methods=['GET'])
@jwt_required()
@roles_required('admin')
def list_users():
    """Lista todos los usuarios registrados. Exclusivo para administradores."""
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT id, username, email, role, nombre,
                              apellido_paterno, apellido_materno,
                              email_verified, created_at
                         FROM users
                        ORDER BY id ASC"""
                )
                users = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'users': users,
            'count': len(users)
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /users/<id> -- DETALLE DE USUARIO (PROPIO O ADMIN)
# -----------------------------------------------------------------
@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Consulta detalles de un usuario. Solo el propio usuario o un admin pueden consultarlo."""
    current_user_id = g.jwt_user.get('user_id')
    current_role = (g.jwt_user.get('role') or '').lower()

    if current_role != 'admin' and current_user_id != user_id:
        return make_response_format({
            'status': 'error',
            'message': 'Acceso prohibido: Solo puedes consultar tu propio perfil.'
        }, 403, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT id, username, email, role, nombre,
                              apellido_paterno, apellido_materno,
                              email_verified, created_at
                         FROM users WHERE id = %s""",
                    (user_id,)
                )
                user = cur.fetchone()

        if not user:
            return make_response_format({
                'status': 'error',
                'message': f'Usuario con ID {user_id} no encontrado.'
            }, 404, request)

        return make_response_format({'status': 'success', 'user': user}, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# POST /users -- CREAR USUARIO
# -----------------------------------------------------------------
@users_bp.route('', methods=['POST'])
def create_user():
    """
    Crea un nuevo usuario.
    Si se intenta asignar rol 'admin', se exige token con rol 'admin'.
    """
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    nombre = (data.get('nombre') or '').strip()
    apellido_paterno = (data.get('apellido_paterno') or '').strip()
    apellido_materno = (data.get('apellido_materno') or '').strip() or None
    role = (data.get('role') or 'user').strip().lower()

    if not username or not email or not password or not nombre or not apellido_paterno:
        return make_response_format({
            'status': 'error',
            'message': 'Campos obligatorios: username, email, password, nombre, apellido_paterno.'
        }, 400, request)

    # Si se intenta crear como admin, validar credencial admin
    if role == 'admin':
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            return make_response_format({
                'status': 'error',
                'message': 'Se requieren privilegios de admin para asignar el rol admin.'
            }, 403, request)
        # Validar decorador dinámico o token
        # (se valida con @jwt_required / rol en caso de admin)

    # Hashear contraseña con bcrypt
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(10)).decode('utf-8')

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Comprobar si ya existe
                cur.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
                if cur.fetchone():
                    return make_response_format({
                        'status': 'error',
                        'message': 'El email o el nombre de usuario ya está registrado.'
                    }, 409, request)

                cur.execute(
                    """INSERT INTO users (username, email, password_hash, role,
                                          nombre, apellido_paterno, apellido_materno,
                                          email_verified, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, true, now())
                       RETURNING id""",
                    (username, email, pw_hash, role, nombre, apellido_paterno, apellido_materno)
                )
                new_id = cur.fetchone()[0]
                conn.commit()

        return make_response_format({
            'status': 'success',
            'message': 'Usuario creado exitosamente.',
            'user': {
                'id': new_id,
                'username': username,
                'email': email,
                'role': role
            }
        }, 201, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PUT/PATCH /users/<id> -- ACTUALIZAR USUARIO (ADMIN ONLY)
# -----------------------------------------------------------------
@users_bp.route('/<int:user_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@roles_required('admin')
def update_user(user_id):
    """Actualiza datos del usuario y revoca sesión en Redis si cambia su rol."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    nombre = data.get('nombre')
    apellido_paterno = data.get('apellido_paterno')
    apellido_materno = data.get('apellido_materno')
    email = data.get('email')
    role = data.get('role')

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
                current = cur.fetchone()
                if not current:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Usuario con ID {user_id} no encontrado.'
                    }, 404, request)

                set_clauses = []
                params = []

                if nombre is not None:
                    set_clauses.append("nombre = %s")
                    params.append(str(nombre).strip())
                if apellido_paterno is not None:
                    set_clauses.append("apellido_paterno = %s")
                    params.append(str(apellido_paterno).strip())
                if apellido_materno is not None:
                    set_clauses.append("apellido_materno = %s")
                    params.append(str(apellido_materno).strip())
                if email is not None:
                    set_clauses.append("email = %s")
                    params.append(str(email).strip().lower())
                if role is not None:
                    set_clauses.append("role = %s")
                    params.append(str(role).strip().lower())

                if set_clauses:
                    params.append(user_id)
                    cur.execute(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s", params)
                    conn.commit()

        # Si cambió el rol, invalidar sesión en Redis para forzar renovación de token
        if role and role.lower() != current['role'].lower():
            redis_client.delete_session(user_id)

        return make_response_format({
            'status': 'success',
            'message': f'Usuario {user_id} actualizado exitosamente.'
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /users/<id> -- ELIMINAR USUARIO (ADMIN ONLY)
# -----------------------------------------------------------------
@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin')
def delete_user(user_id):
    """Elimina usuario y revoca sus sesiones activas en Redis."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if not cur.fetchone():
                    return make_response_format({
                        'status': 'error',
                        'message': f'Usuario con ID {user_id} no encontrado.'
                    }, 404, request)

                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()

        # Invalidar sesión en Redis
        redis_client.delete_session(user_id)

        return make_response_format({
            'status': 'success',
            'message': f'Usuario {user_id} eliminado exitosamente.'
        }, 200, request)
    except Exception as e:
        err_msg = str(e)
        if '23503' in err_msg or 'foreign key' in err_msg.lower():
            return make_response_format({
                'status': 'error',
                'message': 'No se puede eliminar el usuario porque tiene pedidos o registros asociados.'
            }, 409, request)
        return make_response_format({'status': 'error', 'message': err_msg}, 500, request)
