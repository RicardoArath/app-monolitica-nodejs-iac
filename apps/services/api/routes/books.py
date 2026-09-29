"""
routes/books.py
CRUD completo de libros para el microservicio API.
"""
from flask import Blueprint, request
import psycopg.rows
from db import get_connection
from helpers.response import make_response_format
from middleware.jwt_guard import jwt_required

books_bp = Blueprint('books_bp', __name__, url_prefix='/api')

PAGE_SIZE = 12


@books_bp.route('/books', methods=['GET'])
def list_books():
    """Listar libros con búsqueda y paginación."""
    q = request.args.get('q', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    offset = (page - 1) * PAGE_SIZE
    search_term = q if q else None

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                # Conteo total
                cur.execute(
                    """SELECT COUNT(*) AS total FROM v_catalog
                       WHERE (%s::text IS NULL
                              OR title ILIKE '%%' || %s || '%%'
                              OR isbn  ILIKE '%%' || %s || '%%')""",
                    (search_term, search_term, search_term)
                )
                total = cur.fetchone()['total']
                total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

                # Registros paginados
                cur.execute(
                    """SELECT id, isbn, title, publication_year, price, stock,
                              format_name, category_name, cover_image, authors, genres
                         FROM v_catalog
                        WHERE (%s::text IS NULL
                               OR title ILIKE '%%' || %s || '%%'
                               OR isbn  ILIKE '%%' || %s || '%%')
                        ORDER BY title
                        LIMIT %s OFFSET %s""",
                    (search_term, search_term, search_term, PAGE_SIZE, offset)
                )
                records = cur.fetchall()

                return make_response_format({
                    'status': 'success',
                    'data': records,
                    'meta': {
                        'total': total,
                        'page': page,
                        'totalPages': total_pages
                    }
                }, 200)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)


@books_bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Obtener detalle de un libro con autores, géneros, conceptos e imágenes."""
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT b.*, f.name AS format_name, c.name AS category_name
                         FROM books b
                         JOIN formats f    ON f.id = b.format_id
                         JOIN categories c ON c.id = b.category_id
                        WHERE b.id = %s""",
                    (book_id,)
                )
                book = cur.fetchone()

                if not book:
                    return make_response_format(
                        {'status': 'error', 'message': 'Libro no encontrado.'}, 404
                    )

                cur.execute(
                    """SELECT a.id, a.name FROM authors a
                         JOIN book_authors ba ON ba.author_id = a.id
                        WHERE ba.book_id = %s ORDER BY a.name""",
                    (book_id,)
                )
                book['authors'] = cur.fetchall()

                cur.execute(
                    """SELECT g.id, g.name FROM genres g
                         JOIN book_genres bg ON bg.genre_id = g.id
                        WHERE bg.book_id = %s ORDER BY g.name""",
                    (book_id,)
                )
                book['genres'] = cur.fetchall()

                cur.execute(
                    """SELECT id, name, definition, chapter, page_number
                         FROM book_concepts WHERE book_id = %s ORDER BY name""",
                    (book_id,)
                )
                book['concepts'] = cur.fetchall()

                cur.execute(
                    """SELECT id, filename, mime_type, alt_text, is_primary
                         FROM book_images WHERE book_id = %s
                        ORDER BY is_primary DESC, id""",
                    (book_id,)
                )
                book['images'] = cur.fetchall()

                return make_response_format({'status': 'success', 'data': book}, 200)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)


@books_bp.route('/books', methods=['POST'])
@jwt_required
def create_book():
    """Crear un libro nuevo usando el stored procedure sp_create_book."""
    data = request.get_json(silent=True) or {}

    isbn = (data.get('isbn') or '').strip()
    title = (data.get('title') or '').strip()
    if not isbn or not title:
        return make_response_format(
            {'status': 'error', 'message': 'ISBN y título son obligatorios.'}, 400
        )

    try:
        author_ids = data.get('author_ids', [])
        genre_ids = data.get('genre_ids', [])

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sp_create_book(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS id",
                    (
                        isbn,
                        title,
                        data.get('publication_year'),
                        float(data.get('price', 0)),
                        int(data.get('stock', 0)),
                        int(data['format_id']),
                        int(data['category_id']),
                        data.get('description'),
                        author_ids,
                        genre_ids,
                    )
                )
                book_id = cur.fetchone()[0]
                conn.commit()

        return make_response_format(
            {'status': 'success', 'message': 'Libro creado.', 'id': book_id}, 201
        )
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)


@books_bp.route('/books/<int:book_id>', methods=['PUT'])
@jwt_required
def update_book(book_id):
    """Actualizar un libro existente."""
    data = request.get_json(silent=True) or {}

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("BEGIN")
                cur.execute(
                    """UPDATE books
                          SET isbn = %s, title = %s, publication_year = %s,
                              price = %s, stock = %s, format_id = %s,
                              category_id = %s, description = %s
                        WHERE id = %s""",
                    (
                        data.get('isbn'), data.get('title'),
                        data.get('publication_year'),
                        float(data.get('price', 0)),
                        int(data.get('stock', 0)),
                        int(data.get('format_id')),
                        int(data.get('category_id')),
                        data.get('description'),
                        book_id,
                    )
                )
                if 'author_ids' in data:
                    cur.execute(
                        "SELECT sp_set_book_authors(%s, %s)",
                        (book_id, data['author_ids'])
                    )
                if 'genre_ids' in data:
                    cur.execute(
                        "SELECT sp_set_book_genres(%s, %s)",
                        (book_id, data['genre_ids'])
                    )
                conn.commit()

        return make_response_format(
            {'status': 'success', 'message': 'Libro actualizado.'}, 200
        )
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)


@books_bp.route('/books/<int:book_id>', methods=['DELETE'])
@jwt_required
def delete_book(book_id):
    """Eliminar un libro."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT sp_delete_book(%s)", (book_id,))
                conn.commit()

        return make_response_format(
            {'status': 'success', 'message': 'Libro eliminado.'}, 200
        )
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500)
