"""
app/services/soap/app.py
-------------------------------------------------------------------------
Microservicio bilingüe (XML / JSON) para la Librería en Línea.

  • Formato por defecto: XML
  • Para obtener JSON:  ?format=json  en cualquier endpoint.

Puerto: 5001  (no interfiere con la app Node.js en el 3000).

Endpoints:
  GET /books                 → Lista completa de libros
  GET /books/<isbn>          → Detalle de un libro por ISBN
  GET /cloud-concepts        → Conceptos de Cloud Computing + libros
  GET /books-with-images     → Datos mínimos de libros + imágenes

Universidad de Monterrey – Integración de Aplicaciones Computacionales
-------------------------------------------------------------------------
"""

import os
import json
from decimal import Decimal
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

from flask import Flask, request, Response
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# ── Configuración ────────────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

app = Flask(__name__)

DB_CONFIG = {
    'host':     os.getenv('PGHOST', 'localhost'),
    'port':     int(os.getenv('PGPORT', 5432)),
    'dbname':   os.getenv('PGDATABASE', 'libreria_online'),
    'user':     os.getenv('PGUSER', 'libreria_app'),
    'password': os.getenv('PGPASSWORD', 'libreria_app_pass'),
}

# ── Conceptos de Cloud Computing (datos estáticos) ───────────────────────
CLOUD_CONCEPTS = [
    {
        'name': 'IaaS',
        'full_name': 'Infrastructure as a Service',
        'definition': (
            'Modelo de servicio en la nube que ofrece recursos de '
            'infraestructura virtualizados (servidores, almacenamiento, '
            'redes) bajo demanda. El proveedor gestiona el hardware '
            'físico y el usuario administra sistemas operativos, '
            'middleware y aplicaciones.'
        ),
        'examples': ['Google Compute Engine', 'AWS EC2', 'Azure Virtual Machines'],
    },
    {
        'name': 'PaaS',
        'full_name': 'Platform as a Service',
        'definition': (
            'Modelo de servicio en la nube que proporciona una '
            'plataforma completa de desarrollo y despliegue. El '
            'proveedor gestiona la infraestructura, el sistema operativo '
            'y el middleware; el usuario solo se ocupa de su código y '
            'datos.'
        ),
        'examples': ['Google App Engine', 'Heroku', 'Azure App Service'],
    },
    {
        'name': 'SaaS',
        'full_name': 'Software as a Service',
        'definition': (
            'Modelo de servicio en la nube donde el proveedor entrega '
            'aplicaciones listas para usar a través de Internet. El '
            'usuario no gestiona infraestructura, plataforma ni código; '
            'simplemente consume la aplicación.'
        ),
        'examples': ['Google Workspace', 'Microsoft 365', 'Salesforce'],
    },
    {
        'name': 'FaaS',
        'full_name': 'Functions as a Service',
        'definition': (
            'Modelo de computación sin servidor (serverless) donde el '
            'usuario despliega funciones individuales que se ejecutan en '
            'respuesta a eventos. El proveedor gestiona toda la '
            'infraestructura, escalando automáticamente a cero cuando no '
            'hay peticiones.'
        ),
        'examples': ['Google Cloud Functions', 'AWS Lambda', 'Azure Functions'],
    },
]


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════

def get_db():
    """Abre una conexión a PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def _serializable(obj):
    """Convierte tipos no serializables a tipos nativos de Python."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _prettify_xml(elem):
    """Retorna XML con indentación legible."""
    rough = ET.tostring(elem, encoding='unicode')
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent='  ', encoding='UTF-8')


def _get_format():
    """Devuelve 'json' o 'xml' según el query param ?format=."""
    return request.args.get('format', 'xml').lower()


# ── XML builders para cada endpoint ─────────────────────────────────────

def _books_list_to_xml(books, lang='es'):
    """Genera XML en formato <library> con <book> por cada libro."""
    root = ET.Element('library', attrib={'language': lang})
    for b in books:
        book_el = ET.SubElement(root, 'book', attrib={'isbn': str(b['isbn'])})

        ET.SubElement(book_el, 'title').text = b['title']

        # Autores
        authors_el = ET.SubElement(book_el, 'authors')
        authors_str = b.get('authors', '') or ''
        for name in [a.strip() for a in authors_str.split(',') if a.strip()]:
            ET.SubElement(authors_el, 'author').text = name

        if b.get('publication_year'):
            ET.SubElement(book_el, 'year').text = str(b['publication_year'])

        # Géneros
        genres_str = b.get('genres', '') or ''
        if genres_str:
            genres_el = ET.SubElement(book_el, 'genres')
            for g in [x.strip() for x in genres_str.split(',') if x.strip()]:
                ET.SubElement(genres_el, 'genre').text = g

        ET.SubElement(book_el, 'price').text = str(_serializable(b['price']))
        ET.SubElement(book_el, 'stock').text = str(b['stock'])

        if b.get('format_name'):
            ET.SubElement(book_el, 'format').text = b['format_name']

        if b.get('category_name'):
            ET.SubElement(book_el, 'category').text = b['category_name']

        if b.get('description'):
            ET.SubElement(book_el, 'description').text = b['description']

    return root


def _book_detail_to_xml(book):
    """Genera XML para un libro con conceptos e imágenes."""
    root = ET.Element('library', attrib={'language': 'es'})
    book_el = ET.SubElement(root, 'book', attrib={'isbn': str(book['isbn'])})

    ET.SubElement(book_el, 'title').text = book['title']

    # Autores (ya vienen como lista)
    authors_el = ET.SubElement(book_el, 'authors')
    for name in book.get('authors', []):
        ET.SubElement(authors_el, 'author').text = name

    if book.get('publication_year'):
        ET.SubElement(book_el, 'year').text = str(book['publication_year'])

    # Géneros
    if book.get('genres'):
        genres_el = ET.SubElement(book_el, 'genres')
        for g in book['genres']:
            ET.SubElement(genres_el, 'genre').text = g

    ET.SubElement(book_el, 'price').text = str(_serializable(book['price']))
    ET.SubElement(book_el, 'stock').text = str(book['stock'])

    if book.get('format_name'):
        ET.SubElement(book_el, 'format').text = book['format_name']

    if book.get('category_name'):
        ET.SubElement(book_el, 'category').text = book['category_name']

    if book.get('description'):
        ET.SubElement(book_el, 'description').text = book['description']

    # Imágenes
    if book.get('images'):
        images_el = ET.SubElement(book_el, 'images')
        for img in book['images']:
            img_el = ET.SubElement(images_el, 'image',
                                   attrib={'filename': img['filename'],
                                           'mime_type': img['mime_type'],
                                           'is_primary': str(img['is_primary']).lower()})

    # Conceptos
    if book.get('concepts'):
        concepts_el = ET.SubElement(book_el, 'concepts')
        for c in book['concepts']:
            concept_el = ET.SubElement(concepts_el, 'concept', attrib={'name': c['name']})
            ET.SubElement(concept_el, 'definition').text = c['definition']

    return root


def _cloud_concepts_to_xml(concepts, books):
    """Genera XML con conceptos de Cloud Computing y libros."""
    root = ET.Element('cloud_computing_response', attrib={'language': 'es'})

    # Conceptos
    concepts_el = ET.SubElement(root, 'cloud_concepts')
    for c in concepts:
        concept_el = ET.SubElement(concepts_el, 'concept', attrib={'name': c['name']})
        ET.SubElement(concept_el, 'full_name').text = c['full_name']
        ET.SubElement(concept_el, 'definition').text = c['definition']
        examples_el = ET.SubElement(concept_el, 'examples')
        for ex in c['examples']:
            ET.SubElement(examples_el, 'example').text = ex

    # Libros
    books_el = ET.SubElement(root, 'books')
    for b in books:
        book_el = ET.SubElement(books_el, 'book', attrib={'isbn': str(b['isbn'])})
        ET.SubElement(book_el, 'title').text = b['title']
        ET.SubElement(book_el, 'price').text = str(_serializable(b['price']))
        ET.SubElement(book_el, 'stock').text = str(b['stock'])
        if b.get('format_name'):
            ET.SubElement(book_el, 'format').text = b['format_name']
        if b.get('category_name'):
            ET.SubElement(book_el, 'category').text = b['category_name']
        authors_str = b.get('authors', '') or ''
        if authors_str:
            authors_el = ET.SubElement(book_el, 'authors')
            for a in [x.strip() for x in authors_str.split(',') if x.strip()]:
                ET.SubElement(authors_el, 'author').text = a

    return root


def _books_with_images_to_xml(books):
    """Genera XML con datos mínimos de libros y sus imágenes."""
    root = ET.Element('books_with_images', attrib={'language': 'es'})
    for b in books:
        book_el = ET.SubElement(root, 'book', attrib={'isbn': str(b['isbn'])})
        ET.SubElement(book_el, 'title').text = b['title']
        ET.SubElement(book_el, 'price').text = str(_serializable(b['price']))
        images_el = ET.SubElement(book_el, 'images')
        for img in b.get('images', []):
            img_el = ET.SubElement(images_el, 'image',
                                   attrib={'filename': img['filename'],
                                           'mime_type': img['mime_type'],
                                           'is_primary': str(img['is_primary']).lower()})
    return root


def _respond_json(data, status=200):
    """Responde en JSON."""
    safe = json.loads(json.dumps(data, default=_serializable))
    return Response(
        json.dumps(safe, ensure_ascii=False, indent=2),
        mimetype='application/json', status=status)


def _respond_xml(root_element, status=200):
    """Responde en XML."""
    xml_bytes = _prettify_xml(root_element)
    return Response(xml_bytes, mimetype='application/xml', status=status)


def _respond_error(message, status_code=404):
    """Error en JSON o XML."""
    fmt = _get_format()
    if fmt == 'json':
        return _respond_json({'error': message, 'status': status_code}, status_code)
    else:
        root = ET.Element('error')
        ET.SubElement(root, 'message').text = message
        ET.SubElement(root, 'status').text = str(status_code)
        return _respond_xml(root, status_code)


# ══════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

# ── 1. GET /books ────────────────────────────────────────────────────────
@app.route('/books', methods=['GET'])
def get_books():
    """Lista completa de libros con autores y géneros."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    b.id, b.isbn, b.title, b.publication_year,
                    b.price, b.stock, b.description,
                    f.name  AS format_name,
                    c.name  AS category_name,
                    (SELECT string_agg(a.name, ', ' ORDER BY a.name)
                       FROM book_authors ba JOIN authors a ON a.id = ba.author_id
                      WHERE ba.book_id = b.id) AS authors,
                    (SELECT string_agg(g.name, ', ' ORDER BY g.name)
                       FROM book_genres bg JOIN genres g ON g.id = bg.genre_id
                      WHERE bg.book_id = b.id) AS genres
                FROM books b
                JOIN formats    f ON f.id = b.format_id
                JOIN categories c ON c.id = b.category_id
                ORDER BY b.title
            """)
            books = [dict(r) for r in cur.fetchall()]

        fmt = _get_format()
        if fmt == 'json':
            return _respond_json(books)
        else:
            return _respond_xml(_books_list_to_xml(books))
    finally:
        conn.close()


# ── 2. GET /books/<isbn> ─────────────────────────────────────────────────
@app.route('/books/<isbn>', methods=['GET'])
def get_book_by_isbn(isbn):
    """Detalle de un libro por su ISBN."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    b.id, b.isbn, b.title, b.publication_year,
                    b.price, b.stock, b.description,
                    f.name  AS format_name,
                    c.name  AS category_name
                FROM books b
                JOIN formats    f ON f.id = b.format_id
                JOIN categories c ON c.id = b.category_id
                WHERE b.isbn = %s
            """, (isbn,))
            book = cur.fetchone()

            if not book:
                return _respond_error(f'Libro con ISBN {isbn} no encontrado', 404)

            book = dict(book)
            book_id = book['id']

            # Autores
            cur.execute("""
                SELECT a.name FROM authors a
                JOIN book_authors ba ON ba.author_id = a.id
                WHERE ba.book_id = %s ORDER BY a.name
            """, (book_id,))
            book['authors'] = [r['name'] for r in cur.fetchall()]

            # Géneros
            cur.execute("""
                SELECT g.name FROM genres g
                JOIN book_genres bg ON bg.genre_id = g.id
                WHERE bg.book_id = %s ORDER BY g.name
            """, (book_id,))
            book['genres'] = [r['name'] for r in cur.fetchall()]

            # Conceptos
            cur.execute("""
                SELECT name, definition FROM book_concepts
                WHERE book_id = %s ORDER BY name
            """, (book_id,))
            book['concepts'] = [dict(r) for r in cur.fetchall()]

            # Imágenes
            cur.execute("""
                SELECT filename, mime_type, is_primary FROM book_images
                WHERE book_id = %s ORDER BY is_primary DESC, id
            """, (book_id,))
            book['images'] = [dict(r) for r in cur.fetchall()]

        fmt = _get_format()
        if fmt == 'json':
            return _respond_json(book)
        else:
            return _respond_xml(_book_detail_to_xml(book))
    finally:
        conn.close()


# ── 3. GET /cloud-concepts ───────────────────────────────────────────────
@app.route('/cloud-concepts', methods=['GET'])
def get_cloud_concepts():
    """
    Conceptos de Cloud Computing (IaaS, PaaS, SaaS, FaaS)
    junto con los libros almacenados en la base de datos.
    """
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT b.id, b.isbn, b.title, b.price, b.stock,
                       f.name AS format_name, c.name AS category_name,
                       (SELECT string_agg(a.name, ', ' ORDER BY a.name)
                          FROM book_authors ba JOIN authors a ON a.id = ba.author_id
                         WHERE ba.book_id = b.id) AS authors
                FROM books b
                JOIN formats    f ON f.id = b.format_id
                JOIN categories c ON c.id = b.category_id
                ORDER BY b.title
            """)
            books = [dict(r) for r in cur.fetchall()]

        fmt = _get_format()
        if fmt == 'json':
            return _respond_json({
                'cloud_concepts': CLOUD_CONCEPTS,
                'books': books,
            })
        else:
            return _respond_xml(_cloud_concepts_to_xml(CLOUD_CONCEPTS, books))
    finally:
        conn.close()


# ── 4. GET /books-with-images ────────────────────────────────────────────
@app.route('/books-with-images', methods=['GET'])
def get_books_with_images():
    """Datos mínimos de libros junto con sus imágenes."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT b.id, b.isbn, b.title, b.price
                FROM books b ORDER BY b.title
            """)
            books = cur.fetchall()

            result = []
            for book in books:
                cur.execute("""
                    SELECT filename, mime_type, is_primary
                    FROM book_images WHERE book_id = %s
                    ORDER BY is_primary DESC, id
                """, (book['id'],))
                images = [dict(r) for r in cur.fetchall()]
                book_data = dict(book)
                book_data['images'] = images
                result.append(book_data)

        fmt = _get_format()
        if fmt == 'json':
            return _respond_json(result)
        else:
            return _respond_xml(_books_with_images_to_xml(result))
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.getenv('SOAP_PORT', 5001))
    print(f'Microservicio bilingüe (XML/JSON) escuchando en http://127.0.0.1:{port}')
    print(f'  GET /books                  → Lista de libros')
    print(f'  GET /books/<isbn>           → Detalle por ISBN')
    print(f'  GET /cloud-concepts         → Conceptos Cloud + libros')
    print(f'  GET /books-with-images      → Libros con imágenes')
    print(f'  Agrega ?format=json para respuesta JSON (default: XML)')
    app.run(host='0.0.0.0', port=port, debug=True)

