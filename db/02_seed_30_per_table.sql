-- =====================================================================
-- 02_seed_30_per_table.sql
-- Genera 30 registros sintéticos por tabla usando generate_series.
-- Requiere la extensión pgcrypto para generar hashes bcrypt reales
-- (compatibles con bcryptjs usado en la app Node.js).
-- =====================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
-- USERS: 1 administrador + 29 usuarios regulares
-- Password de todos los usuarios sintéticos: "Passw0rd!"
-- ---------------------------------------------------------------------
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@libreria.local', crypt('Passw0rd!', gen_salt('bf')), 'admin');

INSERT INTO users (username, email, password_hash, role)
SELECT
    'usuario' || n,
    'usuario' || n || '@correo.com',
    crypt('Passw0rd!', gen_salt('bf')),
    'user'
FROM generate_series(1, 29) AS n;

-- ---------------------------------------------------------------------
-- FORMATS (catálogo independiente) - 30 combinaciones únicas
-- ---------------------------------------------------------------------
INSERT INTO formats (name)
SELECT DISTINCT base.nombre || CASE WHEN suf.n > 1 THEN ' ' || suf.n ELSE '' END
FROM (VALUES ('Tapa dura'), ('Rústica'), ('Digital (ePub)'), ('Digital (PDF)'),
             ('Audiolibro'), ('Bolsillo'), ('Edición especial'), ('Pasta blanda'),
             ('Empastado'), ('Coleccionista')) AS base(nombre)
CROSS JOIN generate_series(1, 3) AS suf(n)
LIMIT 30;

-- ---------------------------------------------------------------------
-- CATEGORIES (catálogo independiente) - 30 categorías
-- ---------------------------------------------------------------------
INSERT INTO categories (name) VALUES
('Ficción'), ('No ficción'), ('Ciencia'), ('Tecnología'), ('Historia'),
('Biografía'), ('Infantil'), ('Juvenil'), ('Poesía'), ('Filosofía'),
('Negocios'), ('Autoayuda'), ('Arte'), ('Cocina'), ('Viajes'),
('Misterio'), ('Terror'), ('Fantasía'), ('Ciencia ficción'), ('Romance'),
('Ensayo'), ('Política'), ('Psicología'), ('Educación'), ('Deportes'),
('Religión'), ('Salud'), ('Economía'), ('Derecho'), ('Matemáticas');

-- ---------------------------------------------------------------------
-- AUTHORS - 30 autores sintéticos
-- ---------------------------------------------------------------------
INSERT INTO authors (name) VALUES
('Elena Martínez'), ('Carlos Fuentes Jr.'), ('Laura Gómez'), ('Miguel Ángel Ruiz'),
('Sofía Torres'), ('Javier Morales'), ('Ana Belén Castro'), ('Ricardo Salinas'),
('Patricia Núñez'), ('Fernando León'), ('Isabel Prado'), ('Diego Herrera'),
('Camila Rivas'), ('Andrés Paredes'), ('Valeria Soto'), ('Tomás Aguilar'),
('Lucía Vega'), ('Emilio Cordero'), ('Marta Delgado'), ('Sergio Navarro'),
('Daniela Reyes'), ('Hugo Campos'), ('Renata Silva'), ('Iván Domínguez'),
('Paula Cabrera'), ('Alejandro Vidal'), ('Gabriela Ortiz'), ('Raúl Escobar'),
('Natalia Peña'), ('Mario Contreras');

-- ---------------------------------------------------------------------
-- GENRES - 30 géneros
-- ---------------------------------------------------------------------
INSERT INTO genres (name) VALUES
('Drama'), ('Aventura'), ('Distopía'), ('Realismo mágico'), ('Thriller'),
('Comedia'), ('Épica'), ('Gótico'), ('Policiaco'), ('Utopía'),
('Costumbrista'), ('Bélico'), ('Satírico'), ('Experimental'), ('Histórico'),
('Steampunk'), ('Cyberpunk'), ('Western'), ('Fábula'), ('Alegoría'),
('Melodrama'), ('Slice of life'), ('Noir'), ('Absurdo'), ('Gótico sureño'),
('Postapocalíptico'), ('Space opera'), ('Bildungsroman'), ('Picaresca'), ('Surrealista');

-- ---------------------------------------------------------------------
-- BOOKS - 30 libros
-- ---------------------------------------------------------------------
INSERT INTO books (isbn, title, publication_year, price, stock, format_id, category_id, description)
SELECT
    '978-0-' || LPAD(n::text, 6, '0') || '-' || (n % 10),
    'Libro sintético número ' || n,
    1980 + (n % 44),
    ROUND((150 + (n * 37 % 700))::numeric, 2),
    (n * 3 % 40),
    ((n - 1) % 30) + 1,
    ((n - 1) % 30) + 1,
    'Descripción generada automáticamente para el libro de prueba número ' || n || '.'
FROM generate_series(1, 30) AS n;

-- ---------------------------------------------------------------------
-- BOOK_AUTHORS - al menos 30 relaciones (1 a 2 autores por libro)
-- ---------------------------------------------------------------------
INSERT INTO book_authors (book_id, author_id)
SELECT b.id, ((b.id - 1) % 30) + 1
FROM books b;

INSERT INTO book_authors (book_id, author_id)
SELECT b.id, ((b.id + 4) % 30) + 1
FROM books b
WHERE b.id % 2 = 0
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- BOOK_GENRES - al menos 30 relaciones (1 a 2 géneros por libro)
-- ---------------------------------------------------------------------
INSERT INTO book_genres (book_id, genre_id)
SELECT b.id, ((b.id - 1) % 30) + 1
FROM books b;

INSERT INTO book_genres (book_id, genre_id)
SELECT b.id, ((b.id + 7) % 30) + 1
FROM books b
WHERE b.id % 2 = 1
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- BOOK_CONCEPTS - 30 conceptos (un mismo nombre puede repetirse
-- en libros distintos con definición distinta, como pide el enunciado)
-- ---------------------------------------------------------------------
INSERT INTO book_concepts (book_id, name, definition, chapter, page_number)
SELECT
    b.id,
    (ARRAY['Protagonista', 'Antagonista', 'Clímax', 'Metáfora central', 'Tema principal'])[((b.id - 1) % 5) + 1],
    'Definición sintética del concepto para el libro ' || b.id || ', en el contexto de su trama particular.',
    'Capítulo ' || (((b.id - 1) % 10) + 1),
    ((b.id - 1) % 10) + 1
FROM books b;

-- ---------------------------------------------------------------------
-- BOOK_IMAGES - 30 imágenes de referencia (nombres de archivo simulados)
-- ---------------------------------------------------------------------
INSERT INTO book_images (book_id, filename, mime_type, alt_text, is_primary)
SELECT
    b.id,
    'seed-book-' || b.id || '.jpg',
    'image/jpeg',
    'Portada del libro sintético número ' || b.id,
    true
FROM books b;

-- ---------------------------------------------------------------------
-- CARTS - un carrito inicial por usuario
-- ---------------------------------------------------------------------
INSERT INTO carts (user_id)
SELECT id FROM users ORDER BY id;

-- ---------------------------------------------------------------------
-- CART_ITEMS - una relación de prueba por carrito
-- ---------------------------------------------------------------------
INSERT INTO cart_items (cart_id, book_id, quantity)
SELECT c.id, b.id, 1
FROM carts c
JOIN books b ON b.id = ((c.id - 1) % 30) + 1;

-- ---------------------------------------------------------------------
-- ORDERS - pedidos sintéticos con un libro por pedido
-- ---------------------------------------------------------------------
INSERT INTO orders (user_id, status, subtotal, total)
SELECT u.id, 'confirmed', b.price, b.price
FROM users u
JOIN books b ON b.id = ((u.id - 1) % 30) + 1
ORDER BY u.id;

INSERT INTO order_items (order_id, book_id, title_snapshot, unit_price, quantity, line_total)
SELECT o.id, b.id, b.title, b.price, 1, b.price
FROM orders o
JOIN books b ON b.id = ((o.id - 1) % 30) + 1
ORDER BY o.id;

INSERT INTO simulated_payments (order_id, method, status, amount)
SELECT id, 'simulated_card', 'approved', total
FROM orders
ORDER BY id;

COMMIT;
