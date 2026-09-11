-- =====================================================================
-- 01_schema.sql
-- Diseño normalizado hasta 4FN (con tratamiento de multivaluados:
-- autores y géneros se separan en tablas puente para eliminar
-- dependencias multivaluadas dentro de "books").
--
-- Ejecutar conectado a la base "libreria_online":
--   psql -U libreria_app -h <host> -d libreria_online -f db/01_schema.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- USUARIOS (autenticación y roles). Regla: máximo un administrador.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(150) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(10)  NOT NULL DEFAULT 'user'
                        CHECK (role IN ('user', 'admin')),
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- Restringe a UN SOLO administrador en todo el sistema
CREATE UNIQUE INDEX one_admin_only ON users ((role)) WHERE role = 'admin';

-- ---------------------------------------------------------------------
-- CATÁLOGOS INDEPENDIENTES (evitan atributos repetidos / listas planas)
-- ---------------------------------------------------------------------
CREATE TABLE formats (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(50) NOT NULL UNIQUE     -- Tapa dura, Rústica, Digital...
);

CREATE TABLE categories (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(80) NOT NULL UNIQUE     -- Ficción, Técnico, Infantil...
);

CREATE TABLE authors (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE genres (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(80) NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- LIBROS (entidad central, atributos monovaluados y dependientes de ISBN)
-- ---------------------------------------------------------------------
CREATE TABLE books (
    id                  SERIAL PRIMARY KEY,
    isbn                VARCHAR(20)   NOT NULL UNIQUE,
    title               VARCHAR(250)  NOT NULL,
    publication_year    INT           CHECK (publication_year BETWEEN 1450 AND 2100),
    price               NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    stock               INT           NOT NULL DEFAULT 0 CHECK (stock >= 0),
    format_id           INT           NOT NULL REFERENCES formats(id),
    category_id         INT           NOT NULL REFERENCES categories(id),
    description         TEXT,
    created_at          TIMESTAMP     NOT NULL DEFAULT now(),
    updated_at          TIMESTAMP     NOT NULL DEFAULT now()
);

CREATE INDEX idx_books_title ON books (title);
CREATE INDEX idx_books_isbn  ON books (isbn);

-- ---------------------------------------------------------------------
-- RELACIONES MUCHOS-A-MUCHOS (4FN: separan dependencias multivaluadas
-- independientes: "un libro puede tener varios autores" y "un libro
-- puede pertenecer a varios géneros" no deben mezclarse en una sola
-- tabla ni almacenarse como listas dentro de books).
-- ---------------------------------------------------------------------
CREATE TABLE book_authors (
    book_id     INT NOT NULL REFERENCES books(id)   ON DELETE CASCADE,
    author_id   INT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, author_id)
);

CREATE TABLE book_genres (
    book_id     INT NOT NULL REFERENCES books(id)  ON DELETE CASCADE,
    genre_id    INT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, genre_id)
);

-- ---------------------------------------------------------------------
-- CONCEPTOS: un libro puede definir muchos conceptos, y el MISMO
-- concepto puede aparecer en distintos libros con definición distinta.
-- Por eso NO es un catálogo compartido: la definición depende del
-- par (libro, concepto), así que vive en una tabla propia ligada a books.
-- ---------------------------------------------------------------------
CREATE TABLE book_concepts (
    id          SERIAL PRIMARY KEY,
    book_id     INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    name        VARCHAR(150) NOT NULL,
    definition  TEXT NOT NULL,
    chapter     VARCHAR(100),
    page_number INT CHECK (page_number IS NULL OR page_number > 0),
    UNIQUE (book_id, name)
);

-- ---------------------------------------------------------------------
-- IMÁGENES: un libro puede tener varias imágenes (multivaluado ->
-- tabla propia en vez de columna repetida).
-- ---------------------------------------------------------------------
CREATE TABLE book_images (
    id          SERIAL PRIMARY KEY,
    book_id     INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    filename    VARCHAR(255) NOT NULL,
    mime_type   VARCHAR(50)  NOT NULL
                    CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp')),
    alt_text    VARCHAR(255) NOT NULL CHECK (length(trim(alt_text)) > 0),
    is_primary  BOOLEAN      NOT NULL DEFAULT false,
    uploaded_at TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX idx_book_images_book ON book_images (book_id);

-- ---------------------------------------------------------------------
-- CARRITO (un carrito activo por usuario y multiples libros por carrito)
-- ---------------------------------------------------------------------
CREATE TABLE carts (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE cart_items (
    cart_id     INT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    book_id     INT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    quantity    INT NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (cart_id, book_id)
);

CREATE INDEX idx_cart_items_book ON cart_items (book_id);

-- ---------------------------------------------------------------------
-- PEDIDOS Y PAGOS SIMULADOS
-- Los snapshots conservan la informacion historica aunque cambie el libro.
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'confirmed', 'shipped', 'completed', 'cancelled')),
    subtotal    NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    total       NUMERIC(12,2) NOT NULL CHECK (total >= 0),
    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP NOT NULL DEFAULT now(),
    CHECK (total = subtotal)
);

CREATE TABLE order_items (
    id              SERIAL PRIMARY KEY,
    order_id        INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    book_id         INT REFERENCES books(id) ON DELETE SET NULL,
    title_snapshot  VARCHAR(250) NOT NULL,
    unit_price      NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    quantity        INT NOT NULL CHECK (quantity > 0),
    line_total      NUMERIC(12,2) NOT NULL CHECK (line_total = unit_price * quantity)
);

CREATE INDEX idx_orders_user ON orders (user_id, created_at DESC);
CREATE INDEX idx_order_items_order ON order_items (order_id);

CREATE TABLE simulated_payments (
    id              SERIAL PRIMARY KEY,
    order_id        INT NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    method          VARCHAR(30) NOT NULL DEFAULT 'simulated_card'
                        CHECK (method = 'simulated_card'),
    status          VARCHAR(20) NOT NULL
                        CHECK (status IN ('approved', 'rejected')),
    amount          NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    processed_at    TIMESTAMP NOT NULL DEFAULT now()
);

-- Nota: los triggers (updated_at automático, imagen primaria única, etc.)
-- se definen en db/05_triggers.sql para mantener el orden del roadmap
-- del ejercicio (schema -> seed -> queries -> stored procedures -> triggers -> views).

COMMIT;
