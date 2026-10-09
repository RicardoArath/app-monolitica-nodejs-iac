"""
routes/catalogs.py
Endpoints auxiliares de catálogos para llenar selectores en la interfaz gráfica:
- /authors
- /genres
- /formats
- /categories
Integra Cache-Aside en Redis (catalogs:<table>, TTL 300s) con invalidación ante escrituras.
"""
import os
import sys

_curr = os.path.abspath(__file__)
for _ in range(4):
    _curr = os.path.dirname(_curr)
    _cand = os.path.join(_curr, 'apps', 'services')
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
    if os.path.isdir(os.path.join(_curr, 'common')) and _curr not in sys.path:
        sys.path.insert(0, _curr)

from flask import Blueprint, request
import psycopg.rows

from common import (
    get_connection,
    make_response_format,
    redis_client,
    jwt_required,
    roles_required
)

catalogs_bp = Blueprint('catalogs', __name__)

VALID_TABLES = {'authors', 'genres', 'formats', 'categories'}


# -----------------------------------------------------------------
# GET /<table_name> y GET /api/<table_name> -- LISTAR CATÁLOGO CON CACHÉ
# -----------------------------------------------------------------
@catalogs_bp.route('/<table_name>', methods=['GET'])
@catalogs_bp.route('/api/<table_name>', methods=['GET'])
def list_catalog(table_name):
    """Listar registros de un catálogo auxiliar con Cache-Aside en Redis."""
    if table_name not in VALID_TABLES:
        return make_response_format({'status': 'error', 'message': 'Catálogo no válido.'}, 404, request)

    cache_key = f"catalogs:{table_name}"
    cached = redis_client.get_cache(cache_key, prefix='catalogs')
    if cached is not None:
        cached['from_cache'] = True
        return make_response_format(cached, 200, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"SELECT id, name FROM {table_name} ORDER BY name")
                rows = cur.fetchall()

        payload = {
            'status': 'success',
            'from_cache': False,
            'catalog': table_name,
            'items': rows,
            'count': len(rows)
        }
        redis_client.set_cache(cache_key, payload, ttl=300, prefix='catalogs')
        return make_response_format(payload, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# POST /<table_name> y POST /api/<table_name> -- CREAR REGISTRO (ADMIN ONLY)
# -----------------------------------------------------------------
@catalogs_bp.route('/<table_name>', methods=['POST'])
@catalogs_bp.route('/api/<table_name>', methods=['POST'])
@jwt_required()
@roles_required('admin')
def create_catalog_item(table_name):
    """Crear un nuevo registro en el catálogo auxiliar e invalidar su caché."""
    if table_name not in VALID_TABLES:
        return make_response_format({'status': 'error', 'message': 'Catálogo no válido.'}, 404, request)

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return make_response_format({'status': 'error', 'message': 'El campo name es obligatorio.'}, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"INSERT INTO {table_name} (name) VALUES (%s) RETURNING id, name", (name,))
                new_item = cur.fetchone()
                conn.commit()

        # Invalida la clave de catálogo en Redis
        redis_client.delete_cache(f"catalogs:{table_name}")
        if table_name == 'authors':
            redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Registro creado en catálogo {table_name}.',
            'item': new_item
        }, 201, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PUT/PATCH /<table_name>/<id> -- ACTUALIZAR REGISTRO (ADMIN ONLY)
# -----------------------------------------------------------------
@catalogs_bp.route('/<table_name>/<int:item_id>', methods=['PUT', 'PATCH'])
@catalogs_bp.route('/api/<table_name>/<int:item_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@roles_required('admin')
def update_catalog_item(table_name, item_id):
    """Actualizar un registro del catálogo auxiliar e invalidar su caché."""
    if table_name not in VALID_TABLES:
        return make_response_format({'status': 'error', 'message': 'Catálogo no válido.'}, 404, request)

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return make_response_format({'status': 'error', 'message': 'El campo name es obligatorio.'}, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(f"UPDATE {table_name} SET name = %s WHERE id = %s RETURNING id, name", (name, item_id))
                updated = cur.fetchone()
                if not updated:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Registro con ID {item_id} no encontrado en {table_name}.'
                    }, 404, request)
                conn.commit()

        # Invalida la clave de catálogo en Redis
        redis_client.delete_cache(f"catalogs:{table_name}")
        if table_name == 'authors':
            redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Registro {item_id} en {table_name} actualizado exitosamente.',
            'item': updated
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /<table_name>/<id> -- ELIMINAR REGISTRO (ADMIN ONLY)
# -----------------------------------------------------------------
@catalogs_bp.route('/<table_name>/<int:item_id>', methods=['DELETE'])
@catalogs_bp.route('/api/<table_name>/<int:item_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin')
def delete_catalog_item(table_name, item_id):
    """Eliminar un registro del catálogo auxiliar e invalidar su caché."""
    if table_name not in VALID_TABLES:
        return make_response_format({'status': 'error', 'message': 'Catálogo no válido.'}, 404, request)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id FROM {table_name} WHERE id = %s", (item_id,))
                if not cur.fetchone():
                    return make_response_format({
                        'status': 'error',
                        'message': f'Registro con ID {item_id} no encontrado en {table_name}.'
                    }, 404, request)

                cur.execute(f"DELETE FROM {table_name} WHERE id = %s", (item_id,))
                conn.commit()

        # Invalida la clave de catálogo en Redis
        redis_client.delete_cache(f"catalogs:{table_name}")
        if table_name == 'authors':
            redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Registro {item_id} eliminado exitosamente de {table_name}.'
        }, 200, request)
    except Exception as e:
        err_str = str(e)
        if 'foreign key' in err_str.lower() or '23503' in err_str:
            return make_response_format({
                'status': 'error',
                'message': f'No se puede eliminar el registro {item_id} porque está referenciado por otros libros.'
            }, 409, request)
        return make_response_format({'status': 'error', 'message': err_str}, 500, request)
