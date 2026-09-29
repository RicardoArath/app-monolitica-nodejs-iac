"""
routes/books.py
CRUD de libros para el microservicio de libros (puerto 5001).
Soporta GET, POST, PUT, PATCH, DELETE basados en ISBN y filtros de búsqueda.
"""
from flask import Blueprint, request, g
import psycopg.rows

from db import get_connection
from helpers.response import make_response_format
from middleware.jwt_guard import jwt_required

books_bp = Blueprint('books', __name__)

PAGE_SIZE = 12


def _find_book_by_isbn_or_id(cur, identifier):
    """Busca un libro por ISBN o por ID numérico."""
    ident_str = str(identifier).strip()
    cur.execute(
        """SELECT b.id, b.isbn, b.title, b.publication_year, b.price, b.stock,
                  b.format_id, f.name AS format_name,
                  b.category_id, c.name AS category_name,
                  b.description, b.created_at, b.updated_at
             FROM books b
             JOIN formats f    ON f.id = b.format_id
             JOIN categories c ON c.id = b.category_id
            WHERE b.isbn = %s OR (b.id::text = %s AND %s ~ '^[0-9]+$')""",
        (ident_str, ident_str, ident_str)
    )
    return cur.fetchone()


# -----------------------------------------------------------------
# GET /books (y alias /api/books)
# -----------------------------------------------------------------
@books_bp.route('/books', methods=['GET'])
@books_bp.route('/api/books', methods=['GET'])
def list_books():
    """
    Listado y búsqueda de libros con filtros:
    - isbn: coincidencia parcial de ISBN
    - title o q: búsqueda por título
    - year: año exacto de publicación
    - min_price: precio mínimo
    - max_price: precio máximo
    - page: número de página (default 1)
    """
    args = request.args
    isbn_term = args.get('isbn', '').strip() or None
    title_term = (args.get('title') or args.get('q') or '').strip() or None
    year_term = args.get('year', '').strip() or None
    min_price = args.get('min_price', '').strip() or None
    max_price = args.get('max_price', '').strip() or None

    try:
        page = max(1, int(args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    offset = (page - 1) * PAGE_SIZE

    where_clauses = []
    params = []

    if isbn_term:
        where_clauses.append("isbn ILIKE %s")
        params.append(f"%{isbn_term}%")
    if title_term:
        where_clauses.append("title ILIKE %s")
        params.append(f"%{title_term}%")
    if year_term:
        try:
            where_clauses.append("publication_year = %s")
            params.append(int(year_term))
        except ValueError:
            pass
    if min_price:
        try:
            where_clauses.append("price >= %s")
            params.append(float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            where_clauses.append("price <= %s")
            params.append(float(max_price))
        except ValueError:
            pass

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                # Contar registros
                cur.execute(f"SELECT COUNT(*) AS total FROM v_catalog {where_sql}", params)
                total = cur.fetchone()['total']
                total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

                # Obtener página
                query = f"""
                    SELECT id, isbn, title, publication_year, price, stock,
                           format_name, category_name, cover_image,
                           authors, genres
                      FROM v_catalog
                      {where_sql}
                     ORDER BY title
                     LIMIT %s OFFSET %s
                """
                cur.execute(query, params + [PAGE_SIZE, offset])
                records = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'books': records,
            'meta': {
                'total': total,
                'page': page,
                'totalPages': total_pages,
                'filters': {
                    'isbn': isbn_term,
                    'title': title_term,
                    'year': year_term,
                    'min_price': min_price,
                    'max_price': max_price
                }
            }
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /books/{isbn} (y alias /api/books/{isbn})
# -----------------------------------------------------------------
@books_bp.route('/books/<path:isbn>', methods=['GET'])
@books_bp.route('/api/books/<path:isbn>', methods=['GET'])
def get_book_by_isbn(isbn):
    """
    Obtiene la información detallada de un libro a partir de su ISBN.
    Incluye autores, géneros, conceptos/definiciones e imágenes.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                book = _find_book_by_isbn_or_id(cur, isbn)

                if not book:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Libro no encontrado para el ISBN o ID: "{isbn}".'
                    }, 404, request)

                book_id = book['id']

                # Autores
                cur.execute(
                    """SELECT a.id, a.name FROM authors a
                         JOIN book_authors ba ON ba.author_id = a.id
                        WHERE ba.book_id = %s ORDER BY a.name""",
                    (book_id,)
                )
                book['authors'] = cur.fetchall()

                # Géneros
                cur.execute(
                    """SELECT g.id, g.name FROM genres g
                         JOIN book_genres bg ON bg.genre_id = g.id
                        WHERE bg.book_id = %s ORDER BY g.name""",
                    (book_id,)
                )
                book['genres'] = cur.fetchall()

                # Conceptos y definiciones
                cur.execute(
                    """SELECT id, name, definition, chapter, page_number
                         FROM book_concepts WHERE book_id = %s ORDER BY name""",
                    (book_id,)
                )
                book['concepts'] = cur.fetchall()

                # Imágenes
                cur.execute(
                    """SELECT id, filename, mime_type, alt_text, is_primary
                         FROM book_images WHERE book_id = %s
                        ORDER BY is_primary DESC, id""",
                    (book_id,)
                )
                book['images'] = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'book': book
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# POST /books (y alias /api/books)
# -----------------------------------------------------------------
@books_bp.route('/books', methods=['POST'])
@books_bp.route('/api/books', methods=['POST'])
@jwt_required
def create_book():
    """
    Registra un nuevo libro.
    Valida campos obligatorios y unicidad de ISBN.
    """
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    isbn = (data.get('isbn') or '').strip()
    title = (data.get('title') or '').strip()
    format_id = data.get('format_id')
    category_id = data.get('category_id')

    if not isbn or not title:
        return make_response_format({
            'status': 'error',
            'message': 'El ISBN y el título son obligatorios.'
        }, 400, request)

    if not format_id or not category_id:
        return make_response_format({
            'status': 'error',
            'message': 'El formato y la categoría son obligatorios.'
        }, 400, request)

    author_ids = data.get('author_ids', [])
    genre_ids = data.get('genre_ids', [])

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Comprobar unicidad de ISBN
                cur.execute("SELECT id FROM books WHERE isbn = %s", (isbn,))
                if cur.fetchone():
                    return make_response_format({
                        'status': 'error',
                        'message': f'Ya existe un libro registrado con el ISBN "{isbn}".'
                    }, 409, request)

                # Insertar mediante sp_create_book con type casts explícitos
                cur.execute(
                    """SELECT sp_create_book(
                        %s::text,
                        %s::text,
                        %s::int,
                        %s::numeric,
                        %s::int,
                        %s::int,
                        %s::int,
                        %s::text,
                        COALESCE(%s::int[], ARRAY[1]::int[]),
                        COALESCE(%s::int[], ARRAY[1]::int[])
                    ) AS id""",
                    (
                        isbn,
                        title,
                        int(data.get('publication_year')) if data.get('publication_year') else None,
                        float(data.get('price', 0)),
                        int(data.get('stock', 0)),
                        int(format_id),
                        int(category_id),
                        data.get('description') or None,
                        [int(x) for x in author_ids] if author_ids else [1],
                        [int(x) for x in genre_ids] if genre_ids else [1],
                    )
                )
                new_id = cur.fetchone()[0]
                conn.commit()

        return make_response_format({
            'status': 'success',
            'message': 'Libro creado exitosamente.',
            'book': {
                'id': new_id,
                'isbn': isbn,
                'title': title
            }
        }, 201, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PUT /books/{isbn} (y alias /api/books/{isbn})
# Actualización COMPLETA
# -----------------------------------------------------------------
@books_bp.route('/books/<path:isbn>', methods=['PUT'])
@books_bp.route('/api/books/<path:isbn>', methods=['PUT'])
@jwt_required
def update_book_full(isbn):
    """
    Actualización COMPLETA de un libro (PUT).
    Sobrescribe todos los atributos principales del recurso.
    """
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    title = (data.get('title') or '').strip()
    format_id = data.get('format_id')
    category_id = data.get('category_id')

    if not title or not format_id or not category_id:
        return make_response_format({
            'status': 'error',
            'message': 'PUT requiere actualización completa: title, format_id y category_id son obligatorios.'
        }, 400, request)

    author_ids = data.get('author_ids', [])
    genre_ids = data.get('genre_ids', [])

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                existing = _find_book_by_isbn_or_id(cur, isbn)
                if not existing:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Libro no encontrado para el ISBN: "{isbn}".'
                    }, 404, request)

                book_id = existing['id']

                # Actualización completa
                cur.execute(
                    """UPDATE books
                          SET title = %s, publication_year = %s,
                              price = %s, stock = %s, format_id = %s,
                              category_id = %s, description = %s,
                              updated_at = now()
                        WHERE id = %s""",
                    (
                        title,
                        data.get('publication_year') or None,
                        float(data.get('price', 0)),
                        int(data.get('stock', 0)),
                        int(format_id),
                        int(category_id),
                        data.get('description') or None,
                        book_id,
                    )
                )

                # Reemplazo de autores y géneros con type casts
                cur.execute("SELECT sp_set_book_authors(%s, %s::int[])", (book_id, [int(x) for x in author_ids] if author_ids else [1]))
                cur.execute("SELECT sp_set_book_genres(%s, %s::int[])", (book_id, [int(x) for x in genre_ids] if genre_ids else [1]))
                conn.commit()

        return make_response_format({
            'status': 'success',
            'message': f'Libro con ISBN "{isbn}" actualizado completamente mediante PUT.',
            'operation': 'PUT (reemplazo completo de atributos)'
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PATCH /books/{isbn} (y alias /api/books/{isbn})
# Actualización PARCIAL
# -----------------------------------------------------------------
@books_bp.route('/books/<path:isbn>', methods=['PATCH'])
@books_bp.route('/api/books/<path:isbn>', methods=['PATCH'])
@jwt_required
def update_book_partial(isbn):
    """
    Actualización PARCIAL de un libro (PATCH).
    Modifica únicamente los campos enviados en el payload.
    """
    data = request.get_json(silent=True) or request.form.to_dict() or {}

    if not data:
        return make_response_format({
            'status': 'error',
            'message': 'No se proporcionaron datos para actualizar con PATCH.'
        }, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                existing = _find_book_by_isbn_or_id(cur, isbn)
                if not existing:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Libro no encontrado para el ISBN: "{isbn}".'
                    }, 404, request)

                book_id = existing['id']

                set_clauses = []
                params = []
                updated_fields = []

                if 'title' in data:
                    set_clauses.append("title = %s")
                    params.append(str(data['title']).strip())
                    updated_fields.append('title')

                if 'price' in data:
                    set_clauses.append("price = %s")
                    params.append(float(data['price']))
                    updated_fields.append('price')

                if 'stock' in data:
                    set_clauses.append("stock = %s")
                    params.append(int(data['stock']))
                    updated_fields.append('stock')

                if 'publication_year' in data:
                    val = data['publication_year']
                    set_clauses.append("publication_year = %s")
                    params.append(int(val) if val is not None else None)
                    updated_fields.append('publication_year')

                if 'description' in data:
                    set_clauses.append("description = %s")
                    params.append(data['description'])
                    updated_fields.append('description')

                if 'format_id' in data:
                    set_clauses.append("format_id = %s")
                    params.append(int(data['format_id']))
                    updated_fields.append('format_id')

                if 'category_id' in data:
                    set_clauses.append("category_id = %s")
                    params.append(int(data['category_id']))
                    updated_fields.append('category_id')

                if set_clauses:
                    set_clauses.append("updated_at = now()")
                    sql = f"UPDATE books SET {', '.join(set_clauses)} WHERE id = %s"
                    params.append(book_id)
                    cur.execute(sql, params)

                if 'author_ids' in data:
                    cur.execute("SELECT sp_set_book_authors(%s, %s::int[])", (book_id, [int(x) for x in data['author_ids']]))
                    updated_fields.append('author_ids')

                if 'genre_ids' in data:
                    cur.execute("SELECT sp_set_book_genres(%s, %s::int[])", (book_id, [int(x) for x in data['genre_ids']]))
                    updated_fields.append('genre_ids')

                conn.commit()

        return make_response_format({
            'status': 'success',
            'message': f'Libro con ISBN "{isbn}" actualizado parcialmente mediante PATCH.',
            'operation': 'PATCH (actualización parcial de atributos)',
            'updated_fields': updated_fields
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /books/{isbn} (y alias /api/books/{isbn})
# -----------------------------------------------------------------
@books_bp.route('/books/<path:isbn>', methods=['DELETE'])
@books_bp.route('/api/books/<path:isbn>', methods=['DELETE'])
@jwt_required
def delete_book(isbn):
    """
    Elimina un libro por su ISBN.
    """
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                existing = _find_book_by_isbn_or_id(cur, isbn)
                if not existing:
                    return make_response_format({
                        'status': 'error',
                        'message': f'No se puede eliminar: el libro con ISBN "{isbn}" no existe.'
                    }, 404, request)

                book_id = existing['id']
                cur.execute("SELECT sp_delete_book(%s)", (book_id,))
                conn.commit()

        return make_response_format({
            'status': 'success',
            'message': f'El libro con ISBN "{isbn}" fue eliminado exitosamente.'
        }, 200, request)
    except Exception as e:
        # Manejo de llave foránea si el libro está en pedidos
        err_msg = str(e)
        if '23503' in err_msg or 'foreign key' in err_msg.lower():
            return make_response_format({
                'status': 'error',
                'message': 'No se puede eliminar el libro porque está asociado a pedidos u órdenes existentes.'
            }, 409, request)
        return make_response_format({'status': 'error', 'message': err_msg}, 500, request)
