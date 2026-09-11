-- =====================================================================
-- 03_all_quieries_before_stored_procedures.sql
-- Consultas de referencia (parametrizadas con $1, $2... como las usa
-- pg desde Node.js) que soportan las pantallas de la aplicación.
-- =====================================================================

-- Listado de catálogo con paginación simple y búsqueda por título o ISBN
SELECT b.id, b.isbn, b.title, b.price, b.stock, f.name AS format_name, c.name AS category_name,
       (SELECT filename FROM book_images bi WHERE bi.book_id = b.id AND bi.is_primary LIMIT 1) AS cover
FROM books b
JOIN formats f    ON f.id = b.format_id
JOIN categories c ON c.id = b.category_id
WHERE ($1::text IS NULL OR b.title ILIKE '%' || $1 || '%' OR b.isbn ILIKE '%' || $1 || '%')
ORDER BY b.title
LIMIT $2 OFFSET $3;

-- Detalle completo de un libro (autores, géneros, conceptos, imágenes)
SELECT b.*, f.name AS format_name, c.name AS category_name
FROM books b
JOIN formats f    ON f.id = b.format_id
JOIN categories c ON c.id = b.category_id
WHERE b.id = $1;

SELECT a.id, a.name
FROM authors a
JOIN book_authors ba ON ba.author_id = a.id
WHERE ba.book_id = $1
ORDER BY a.name;

SELECT g.id, g.name
FROM genres g
JOIN book_genres bg ON bg.genre_id = g.id
WHERE bg.book_id = $1
ORDER BY g.name;

SELECT id, name, definition
FROM book_concepts
WHERE book_id = $1
ORDER BY name;

SELECT id, filename, mime_type, is_primary
FROM book_images
WHERE book_id = $1
ORDER BY is_primary DESC, id;

-- Autenticación
SELECT id, username, email, password_hash, role
FROM users
WHERE username = $1;

-- Verificar si ya existe un administrador (regla de negocio)
SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin';

-- CRUD de libro (INSERT / UPDATE / DELETE)
INSERT INTO books (isbn, title, publication_year, price, stock, format_id, category_id, description)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id;

UPDATE books
   SET isbn = $1, title = $2, publication_year = $3, price = $4,
       stock = $5, format_id = $6, category_id = $7, description = $8
 WHERE id = $9;

DELETE FROM books WHERE id = $1;

-- Reemplazo de relaciones muchos-a-muchos (autores / géneros) de un libro
DELETE FROM book_authors WHERE book_id = $1;
INSERT INTO book_authors (book_id, author_id) VALUES ($1, $2);

DELETE FROM book_genres WHERE book_id = $1;
INSERT INTO book_genres (book_id, genre_id) VALUES ($1, $2);

-- CRUD de catálogos maestros (autores, géneros, formatos, categorías)
INSERT INTO authors (name) VALUES ($1) RETURNING id;
UPDATE authors SET name = $1 WHERE id = $2;
DELETE FROM authors WHERE id = $1;

INSERT INTO genres (name) VALUES ($1) RETURNING id;
UPDATE genres SET name = $1 WHERE id = $2;
DELETE FROM genres WHERE id = $1;

INSERT INTO formats (name) VALUES ($1) RETURNING id;
UPDATE formats SET name = $1 WHERE id = $2;
DELETE FROM formats WHERE id = $1;

INSERT INTO categories (name) VALUES ($1) RETURNING id;
UPDATE categories SET name = $1 WHERE id = $2;
DELETE FROM categories WHERE id = $1;

-- CRUD de conceptos por libro
INSERT INTO book_concepts (book_id, name, definition) VALUES ($1, $2, $3) RETURNING id;
UPDATE book_concepts SET name = $1, definition = $2 WHERE id = $3;
DELETE FROM book_concepts WHERE id = $1;

-- CRUD de imágenes por libro
INSERT INTO book_images (book_id, filename, mime_type, is_primary) VALUES ($1, $2, $3, $4) RETURNING id;
UPDATE book_images SET is_primary = true WHERE id = $1;
DELETE FROM book_images WHERE id = $1;
