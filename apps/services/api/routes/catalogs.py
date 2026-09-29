from flask import Blueprint, request
import psycopg
from db import get_connection
from helpers.response import make_response_format

catalogs_bp = Blueprint('catalogs_bp', __name__, url_prefix='/api')

ALLOWED_TABLES = ['authors', 'genres', 'formats', 'categories']

@catalogs_bp.route('/<string:table>', methods=['GET'])
def list_items(table):
    if table not in ALLOWED_TABLES:
        return make_response_format({'status': 'error', 'message': 'Invalid table'}, 400)
    
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"SELECT id, name FROM {table} ORDER BY id ASC")
                records = cur.fetchall()
                return make_response_format({'status': 'success', 'data': records}, 200)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)

@catalogs_bp.route('/<string:table>', methods=['POST'])
def create_item(table):
    if table not in ALLOWED_TABLES:
        return make_response_format({'status': 'error', 'message': 'Invalid table'}, 400)
    
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return make_response_format({'status': 'error', 'message': 'Name is required'}, 400)
        
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"INSERT INTO {table} (name) VALUES (%s) RETURNING id, name", [name])
                record = cur.fetchone()
                conn.commit()
                return make_response_format({'status': 'success', 'data': record}, 201)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)

@catalogs_bp.route('/<string:table>/<int:item_id>', methods=['PUT'])
def update_item(table, item_id):
    if table not in ALLOWED_TABLES:
        return make_response_format({'status': 'error', 'message': 'Invalid table'}, 400)
        
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return make_response_format({'status': 'error', 'message': 'Name is required'}, 400)
        
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"UPDATE {table} SET name = %s WHERE id = %s", [name, item_id])
                conn.commit()
                return make_response_format({'status': 'success', 'message': 'Updated'}, 200)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)

@catalogs_bp.route('/<string:table>/<int:item_id>', methods=['DELETE'])
def delete_item(table, item_id):
    if table not in ALLOWED_TABLES:
        return make_response_format({'status': 'error', 'message': 'Invalid table'}, 400)
        
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {table} WHERE id = %s", [item_id])
                conn.commit()
                return make_response_format({'status': 'success', 'message': 'Deleted'}, 200)
    except psycopg.errors.ForeignKeyViolation:
        return make_response_format({'status': 'error', 'message': 'Cannot delete item, it is currently in use (foreign key constraint).'}, 409)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)
