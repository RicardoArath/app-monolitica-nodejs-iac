"""
authors/routes.py
Rutas del microservicio de Autores (puerto 5005).
Administra autores, asignación de libros a autores y relaciones book_authors.
Integra Cache-Aside en Redis con invalidación cruzada (authors:* y books:*).
"""
import sys, os
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
    jwt_required,
    roles_required,
    redis_client,
    config
)

authors_bp = Blueprint('authors', __name__, url_prefix='/authors')


# -----------------------------------------------------------------
# GET /authors -- LISTADO CON CACHE-ASIDE (FAIL-OPEN)
# -----------------------------------------------------------------
@authors_bp.route('', methods=['GET'])
def list_authors():
    """Lista todos los autores con soporte de caché en Redis."""
    cache_key = "authors:list"
    cached = redis_client.get_cache(cache_key, prefix='authors')
    if cached is not None:
        cached['from_cache'] = True
        return make_response_format(cached, 200, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT a.id, a.name, COUNT(ba.book_id) AS books_count
                         FROM authors a
                         LEFT JOIN book_authors ba ON ba.author_id = a.id
                        GROUP BY a.id, a.name
                        ORDER BY a.name ASC"""
                )
                authors = cur.fetchall()

        payload = {
            'status': 'success',
            'from_cache': False,
            'authors': authors,
            'count': len(authors)
        }
        redis_client.set_cache(cache_key, payload, ttl=config.CACHE_TTL_AUTHORS, prefix='authors')
        return make_response_format(payload, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /authors/<id> -- DETALLE DE AUTOR Y LIBROS ASOCIADOS
# -----------------------------------------------------------------
@authors_bp.route('/<int:author_id>', methods=['GET'])
def get_author(author_id):
    """Consulta detalles de un autor y sus libros asociados."""
    cache_key = f"authors:{author_id}"
    cached = redis_client.get_cache(cache_key, prefix='authors')
    if cached is not None:
        cached['from_cache'] = True
        return make_response_format(cached, 200, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute("SELECT id, name FROM authors WHERE id = %s", (author_id,))
                author = cur.fetchone()
                if not author:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Autor con ID {author_id} no encontrado.'
                    }, 404, request)

                # Libros del autor
                cur.execute(
                    """SELECT b.id, b.isbn, b.title, b.publication_year, b.price, b.stock
                         FROM books b
                         JOIN book_authors ba ON ba.book_id = b.id
                        WHERE ba.author_id = %s
                        ORDER BY b.title ASC""",
                    (author_id,)
                )
                books = cur.fetchall()
                author['books'] = books

        payload = {
            'status': 'success',
            'from_cache': False,
            'author': author
        }
        redis_client.set_cache(cache_key, payload, ttl=config.CACHE_TTL_AUTHORS, prefix='authors')
        return make_response_format(payload, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# POST /authors -- CREAR AUTOR (ADMIN ONLY)
# -----------------------------------------------------------------
@authors_bp.route('', methods=['POST'])
@jwt_required()
@roles_required('admin')
def create_author():
    """Crea un nuevo autor e invalida caché de autores."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = (data.get('name') or '').strip()

    if not name:
        return make_response_format({'status': 'error', 'message': 'El campo name es obligatorio.'}, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO authors (name) VALUES (%s) RETURNING id, name", (name,))
                new_author = cur.fetchone()
                conn.commit()

        # Invalidar caché
        redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': 'Autor creado exitosamente.',
            'author': {'id': new_author[0], 'name': new_author[1]}
        }, 201, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PUT/PATCH /authors/<id> -- ACTUALIZAR AUTOR (ADMIN ONLY)
# -----------------------------------------------------------------
@authors_bp.route('/<int:author_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@roles_required('admin')
def update_author(author_id):
    """Actualiza el nombre de un autor e invalida caché."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = (data.get('name') or '').strip()

    if not name:
        return make_response_format({'status': 'error', 'message': 'El campo name es obligatorio.'}, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE authors SET name = %s WHERE id = %s RETURNING id, name", (name, author_id))
                updated = cur.fetchone()
                if not updated:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Autor con ID {author_id} no encontrado.'
                    }, 404, request)
                conn.commit()

        # Invalidar caché de autores y libros asociados
        redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': 'Autor actualizado exitosamente.',
            'author': {'id': updated[0], 'name': updated[1]}
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /authors/<id> -- ELIMINAR AUTOR (ADMIN ONLY)
# -----------------------------------------------------------------
@authors_bp.route('/<int:author_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin')
def delete_author(author_id):
    """Elimina un autor si no tiene libros asociados."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM authors WHERE id = %s RETURNING id", (author_id,))
                deleted = cur.fetchone()
                if not deleted:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Autor con ID {author_id} no encontrado.'
                    }, 404, request)
                conn.commit()

        redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Autor {author_id} eliminado exitosamente.'
        }, 200, request)
    except Exception as e:
        err_msg = str(e)
        if '23503' in err_msg or 'foreign key' in err_msg.lower():
            return make_response_format({
                'status': 'error',
                'message': 'No se puede eliminar el autor porque tiene libros asociados en el catálogo.'
            }, 409, request)
        return make_response_format({'status': 'error', 'message': err_msg}, 500, request)


# -----------------------------------------------------------------
# POST /authors/<id>/books -- VINCULAR LIBRO CON AUTOR (ADMIN ONLY)
# -----------------------------------------------------------------
@authors_bp.route('/<int:author_id>/books', methods=['POST'])
@jwt_required()
@roles_required('admin')
def link_book(author_id):
    """Asocia un libro existente con un autor (book_authors). Invalida caché de books:* y authors:*."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    book_id = data.get('book_id')

    if not book_id:
        return make_response_format({'status': 'error', 'message': 'El campo book_id es obligatorio.'}, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Comprobar si ya existe la asociación
                cur.execute(
                    "SELECT 1 FROM book_authors WHERE book_id = %s AND author_id = %s",
                    (int(book_id), author_id)
                )
                if cur.fetchone():
                    return make_response_format({
                        'status': 'error',
                        'message': f'El libro {book_id} ya está asociado al autor {author_id}.'
                    }, 409, request)

                cur.execute(
                    "INSERT INTO book_authors (book_id, author_id) VALUES (%s, %s)",
                    (int(book_id), author_id)
                )
                conn.commit()

        # Invalidación cruzada en Redis
        redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Libro {book_id} asociado exitosamente al autor {author_id}.'
        }, 201, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /authors/<id>/books/<book_id> -- DESVINCULAR LIBRO (ADMIN ONLY)
# -----------------------------------------------------------------
@authors_bp.route('/<int:author_id>/books/<int:book_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin')
def unlink_book(author_id, book_id):
    """Desvincula un libro de un autor. Invalida caché de books:* y authors:*."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM book_authors WHERE book_id = %s AND author_id = %s RETURNING book_id",
                    (book_id, author_id)
                )
                deleted = cur.fetchone()
                if not deleted:
                    return make_response_format({
                        'status': 'error',
                        'message': f'No existe asociación entre el libro {book_id} y el autor {author_id}.'
                    }, 404, request)
                conn.commit()

        redis_client.invalidate_pattern('authors:*')
        redis_client.invalidate_pattern('books:*')

        return make_response_format({
            'status': 'success',
            'message': f'Libro {book_id} desvinculado del autor {author_id}.'
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)
