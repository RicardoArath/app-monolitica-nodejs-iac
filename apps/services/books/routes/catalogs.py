"""
routes/catalogs.py
Endpoints auxiliares de catálogos para llenar selectores en la interfaz gráfica:
- /authors
- /genres
- /formats
- /categories
"""
from flask import Blueprint, request
import psycopg.rows

from db import get_connection
from helpers.response import make_response_format

catalogs_bp = Blueprint('catalogs', __name__)

VALID_TABLES = {'authors', 'genres', 'formats', 'categories'}


@catalogs_bp.route('/<table_name>', methods=['GET'])
@catalogs_bp.route('/api/<table_name>', methods=['GET'])
def list_catalog(table_name):
    """Listar registros de un catálogo auxiliar."""
    if table_name not in VALID_TABLES:
        return make_response_format({'status': 'error', 'message': 'Catálogo no válido.'}, 404, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"SELECT id, name FROM {table_name} ORDER BY name")
                rows = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'catalog': table_name,
            'items': rows
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)
