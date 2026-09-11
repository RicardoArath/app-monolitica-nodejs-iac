-- =====================================================================
-- 05_triggers.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- updated_at automático en books ante cualquier UPDATE
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS books_set_updated_at ON books;
CREATE TRIGGER books_set_updated_at
    BEFORE UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION trg_set_updated_at();

DROP TRIGGER IF EXISTS carts_set_updated_at ON carts;
CREATE TRIGGER carts_set_updated_at
    BEFORE UPDATE ON carts
    FOR EACH ROW
    EXECUTE FUNCTION trg_set_updated_at();

DROP TRIGGER IF EXISTS orders_set_updated_at ON orders;
CREATE TRIGGER orders_set_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION trg_set_updated_at();

-- ---------------------------------------------------------------------
-- Garantiza que exista como máximo UNA imagen marcada como primaria
-- por libro (complementa el índice único parcial de administrador,
-- aquí aplicado a datos, no a esquema).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_single_primary_image() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_primary THEN
        UPDATE book_images
           SET is_primary = false
         WHERE book_id = NEW.book_id
           AND id <> NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS book_images_single_primary ON book_images;
CREATE TRIGGER book_images_single_primary
    AFTER INSERT OR UPDATE ON book_images
    FOR EACH ROW
    WHEN (NEW.is_primary)
    EXECUTE FUNCTION trg_single_primary_image();

-- ---------------------------------------------------------------------
-- Evita stock negativo por una vía distinta al CHECK (defensa en
-- profundidad para futuras rutas que descuenten stock directamente).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_prevent_negative_stock() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.stock < 0 THEN
        RAISE EXCEPTION 'El stock del libro % no puede ser negativo', NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS books_prevent_negative_stock ON books;
CREATE TRIGGER books_prevent_negative_stock
    BEFORE INSERT OR UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION trg_prevent_negative_stock();

-- ---------------------------------------------------------------------
-- El importe de un pago simulado debe coincidir con el total del pedido.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_validate_simulated_payment() RETURNS TRIGGER AS $$
DECLARE
    v_total NUMERIC(12,2);
BEGIN
    SELECT total INTO v_total FROM orders WHERE id = NEW.order_id;
    IF v_total IS NULL OR NEW.amount <> v_total THEN
        RAISE EXCEPTION 'El importe del pago no coincide con el total del pedido';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS simulated_payments_validate_amount ON simulated_payments;
CREATE TRIGGER simulated_payments_validate_amount
    BEFORE INSERT OR UPDATE ON simulated_payments
    FOR EACH ROW
    EXECUTE FUNCTION trg_validate_simulated_payment();

COMMIT;
