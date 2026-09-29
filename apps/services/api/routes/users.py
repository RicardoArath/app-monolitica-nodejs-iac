from flask import Blueprint, request
import psycopg
from db import get_connection
from helpers.response import make_response_format

users_bp = Blueprint('users_bp', __name__, url_prefix='/api')

@users_bp.route('/users', methods=['GET'])
def list_users():
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute("""
                    SELECT id, username, email, role, nombre, apellido_paterno, apellido_materno, created_at
                    FROM users
                    ORDER BY id DESC
                """)
                records = cur.fetchall()
                return make_response_format({'status': 'success', 'data': records}, 200)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)
