-- =====================================================================
-- 04_stored_procedures.sql
-- Encapsula en el servidor de BD las operaciones que combinan varias
-- tablas, para mantener consistencia aunque la app solo mande
-- parámetros escalares (nada de JSON/XML).
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Registrar un nuevo usuario. Fuerza role = 'user'; el único admin
-- se crea aparte y está protegido por el índice único parcial.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_register_user(
    p_username TEXT,
    p_email TEXT,
    p_password_hash TEXT
) RETURNS INT AS $$
DECLARE
    v_id INT;
BEGIN
    INSERT INTO users (username, email, password_hash, role)
    VALUES (p_username, p_email, p_password_hash, 'user')
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Reemplazar por completo la lista de autores de un libro
-- (recibe los ids como arreglo de enteros, no como JSON).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_set_book_authors(
    p_book_id INT,
    p_author_ids INT[]
) RETURNS VOID AS $$
BEGIN
    DELETE FROM book_authors WHERE book_id = p_book_id;

    INSERT INTO book_authors (book_id, author_id)
    SELECT p_book_id, unnest(p_author_ids)
    WHERE p_author_ids IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Reemplazar por completo la lista de géneros de un libro
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_set_book_genres(
    p_book_id INT,
    p_genre_ids INT[]
) RETURNS VOID AS $$
BEGIN
    DELETE FROM book_genres WHERE book_id = p_book_id;

    INSERT INTO book_genres (book_id, genre_id)
    SELECT p_book_id, unnest(p_genre_ids)
    WHERE p_genre_ids IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Crear libro completo (datos base + autores + géneros) en una sola
-- transacción atómica.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_create_book(
    p_isbn TEXT,
    p_title TEXT,
    p_year INT,
    p_price NUMERIC,
    p_stock INT,
    p_format_id INT,
    p_category_id INT,
    p_description TEXT,
    p_author_ids INT[],
    p_genre_ids INT[]
) RETURNS INT AS $$
DECLARE
    v_book_id INT;
BEGIN
    INSERT INTO books (isbn, title, publication_year, price, stock, format_id, category_id, description)
    VALUES (p_isbn, p_title, p_year, p_price, p_stock, p_format_id, p_category_id, p_description)
    RETURNING id INTO v_book_id;

    PERFORM sp_set_book_authors(v_book_id, p_author_ids);
    PERFORM sp_set_book_genres(v_book_id, p_genre_ids);

    RETURN v_book_id;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Eliminar un libro de forma segura junto con toda su información
-- dependiente (aprovecha ON DELETE CASCADE, pero se expone como
-- procedimiento para centralizar la regla de negocio y validaciones
-- futuras, p. ej. bloquear borrado si el libro tiene pedidos).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_delete_book(p_book_id INT) RETURNS VOID AS $$
BEGIN
    DELETE FROM books WHERE id = p_book_id;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Confirmar carrito con pago simulado.
-- El bloqueo de filas evita vender el mismo stock concurrentemente.
-- Un pago rechazado conserva el pedido como pendiente, no descuenta
-- stock y deja los elementos en el carrito para que puedan reintentarse.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_checkout_cart(
    p_user_id INT,
    p_payment_approved BOOLEAN
) RETURNS INT AS $$
DECLARE
    v_cart_id INT;
    v_order_id INT;
    v_subtotal NUMERIC(12,2) := 0;
    v_item RECORD;
BEGIN
    SELECT id INTO v_cart_id
    FROM carts
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF v_cart_id IS NULL THEN
        RAISE EXCEPTION 'El usuario no tiene carrito';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM cart_items WHERE cart_id = v_cart_id) THEN
        RAISE EXCEPTION 'El carrito esta vacio';
    END IF;

    -- Bloquea los libros en un orden estable para reducir interbloqueos.
    FOR v_item IN
        SELECT ci.book_id, ci.quantity, b.title, b.price, b.stock
        FROM cart_items ci
        JOIN books b ON b.id = ci.book_id
        WHERE ci.cart_id = v_cart_id
        ORDER BY ci.book_id
        FOR UPDATE OF b
    LOOP
        IF v_item.quantity > v_item.stock THEN
            RAISE EXCEPTION 'Stock insuficiente para el libro %', v_item.book_id;
        END IF;
        v_subtotal := v_subtotal + (v_item.price * v_item.quantity);
    END LOOP;

    INSERT INTO orders (user_id, status, subtotal, total)
    VALUES (
        p_user_id,
        CASE WHEN p_payment_approved THEN 'confirmed' ELSE 'pending' END,
        v_subtotal,
        v_subtotal
    )
    RETURNING id INTO v_order_id;

    INSERT INTO order_items (order_id, book_id, title_snapshot, unit_price, quantity, line_total)
    SELECT v_order_id, ci.book_id, b.title, b.price, ci.quantity, b.price * ci.quantity
    FROM cart_items ci
    JOIN books b ON b.id = ci.book_id
    WHERE ci.cart_id = v_cart_id;

    INSERT INTO simulated_payments (order_id, status, amount)
    VALUES (v_order_id, CASE WHEN p_payment_approved THEN 'approved' ELSE 'rejected' END, v_subtotal);

    IF p_payment_approved THEN
        UPDATE books b
        SET stock = b.stock - ci.quantity
        FROM cart_items ci
        WHERE ci.cart_id = v_cart_id
          AND b.id = ci.book_id;

        DELETE FROM cart_items WHERE cart_id = v_cart_id;
    END IF;

    RETURN v_order_id;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Actualizar el estado de un pedido desde la administracion.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION sp_set_order_status(
    p_order_id INT,
    p_status TEXT
) RETURNS VOID AS $$
BEGIN
    IF p_status NOT IN ('pending', 'confirmed', 'shipped', 'completed', 'cancelled') THEN
        RAISE EXCEPTION 'Estado de pedido no valido: %', p_status;
    END IF;

    UPDATE orders
    SET status = p_status
    WHERE id = p_order_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'El pedido % no existe', p_order_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMIT;
