/**
 * migrate_add_missing.js
 * ---------------------
 * Script de migración que agrega las tablas, triggers, stored procedures
 * y vistas que faltan en la base de datos sin tocar lo que ya existe.
 *
 * Uso: node db/migrate_add_missing.js
 */
const db = require('../config/db');

async function migrate() {
  const client = await db.getClient();
  try {
    await client.query('BEGIN');

    // =====================================================================
    // 1. TABLAS que faltan (IF NOT EXISTS para no fallar si ya existen)
    // =====================================================================
    console.log('1/5 Creando tablas faltantes...');

    await client.query(`
      CREATE TABLE IF NOT EXISTS carts (
        id          SERIAL PRIMARY KEY,
        user_id     INT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        created_at  TIMESTAMP NOT NULL DEFAULT now(),
        updated_at  TIMESTAMP NOT NULL DEFAULT now()
      );
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS cart_items (
        cart_id     INT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
        book_id     INT NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
        quantity    INT NOT NULL CHECK (quantity > 0),
        PRIMARY KEY (cart_id, book_id)
      );
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_cart_items_book ON cart_items (book_id);
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS orders (
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
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS order_items (
        id              SERIAL PRIMARY KEY,
        order_id        INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        book_id         INT REFERENCES books(id) ON DELETE SET NULL,
        title_snapshot  VARCHAR(250) NOT NULL,
        unit_price      NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
        quantity        INT NOT NULL CHECK (quantity > 0),
        line_total      NUMERIC(12,2) NOT NULL CHECK (line_total = unit_price * quantity)
      );
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id, created_at DESC);
    `);
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id);
    `);

    await client.query(`
      CREATE TABLE IF NOT EXISTS simulated_payments (
        id              SERIAL PRIMARY KEY,
        order_id        INT NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
        method          VARCHAR(30) NOT NULL DEFAULT 'simulated_card'
                            CHECK (method = 'simulated_card'),
        status          VARCHAR(20) NOT NULL
                            CHECK (status IN ('approved', 'rejected')),
        amount          NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
        processed_at    TIMESTAMP NOT NULL DEFAULT now()
      );
    `);

    // Columnas faltantes en tablas existentes
    await client.query(`
      ALTER TABLE book_concepts 
        ADD COLUMN IF NOT EXISTS chapter VARCHAR(100),
        ADD COLUMN IF NOT EXISTS page_number INT CHECK (page_number IS NULL OR page_number > 0);
    `);

    console.log('   ✔ Tablas creadas y actualizadas');

    // =====================================================================
    // 2. TRIGGERS (CREATE OR REPLACE + DROP IF EXISTS = idempotente)
    // =====================================================================
    console.log('2/5 Creando triggers...');

    // updated_at para carts
    await client.query(`
      CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS TRIGGER AS $$
      BEGIN
        NEW.updated_at = now();
        RETURN NEW;
      END;
      $$ LANGUAGE plpgsql;
    `);

    await client.query(`DROP TRIGGER IF EXISTS carts_set_updated_at ON carts;`);
    await client.query(`
      CREATE TRIGGER carts_set_updated_at
        BEFORE UPDATE ON carts
        FOR EACH ROW
        EXECUTE FUNCTION trg_set_updated_at();
    `);

    // updated_at para orders
    await client.query(`DROP TRIGGER IF EXISTS orders_set_updated_at ON orders;`);
    await client.query(`
      CREATE TRIGGER orders_set_updated_at
        BEFORE UPDATE ON orders
        FOR EACH ROW
        EXECUTE FUNCTION trg_set_updated_at();
    `);

    // Validar que el pago coincida con el total del pedido
    await client.query(`
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
    `);

    await client.query(`DROP TRIGGER IF EXISTS simulated_payments_validate_amount ON simulated_payments;`);
    await client.query(`
      CREATE TRIGGER simulated_payments_validate_amount
        BEFORE INSERT OR UPDATE ON simulated_payments
        FOR EACH ROW
        EXECUTE FUNCTION trg_validate_simulated_payment();
    `);

    console.log('   ✔ Triggers creados');

    // =====================================================================
    // 3. STORED PROCEDURES (CREATE OR REPLACE = idempotente)
    // =====================================================================
    console.log('3/5 Creando stored procedures...');

    await client.query(`
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
        SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id FOR UPDATE;
        IF v_cart_id IS NULL THEN
          RAISE EXCEPTION 'El usuario no tiene carrito';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM cart_items WHERE cart_id = v_cart_id) THEN
          RAISE EXCEPTION 'El carrito esta vacio';
        END IF;

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
          v_subtotal, v_subtotal
        ) RETURNING id INTO v_order_id;

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
          WHERE ci.cart_id = v_cart_id AND b.id = ci.book_id;

          DELETE FROM cart_items WHERE cart_id = v_cart_id;
        END IF;

        RETURN v_order_id;
      END;
      $$ LANGUAGE plpgsql;
    `);

    await client.query(`
      CREATE OR REPLACE FUNCTION sp_set_order_status(
        p_order_id INT,
        p_status TEXT
      ) RETURNS VOID AS $$
      BEGIN
        IF p_status NOT IN ('pending', 'confirmed', 'shipped', 'completed', 'cancelled') THEN
          RAISE EXCEPTION 'Estado de pedido no valido: %', p_status;
        END IF;
        UPDATE orders SET status = p_status WHERE id = p_order_id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'El pedido % no existe', p_order_id;
        END IF;
      END;
      $$ LANGUAGE plpgsql;
    `);

    console.log('   ✔ Stored procedures creados');

    // =====================================================================
    // 4. VISTAS (CREATE OR REPLACE = idempotente)
    // =====================================================================
    console.log('4/5 Actualizando vistas...');

    await client.query(`
      CREATE OR REPLACE VIEW v_order_summary AS
      SELECT
        o.id,
        o.user_id,
        u.username,
        o.status,
        o.subtotal,
        o.total,
        sp.status AS payment_status,
        o.created_at,
        o.updated_at
      FROM orders o
      JOIN users u ON u.id = o.user_id
      LEFT JOIN simulated_payments sp ON sp.order_id = o.id;
    `);

    console.log('   ✔ Vistas actualizadas');

    // =====================================================================
    // 5. COMMIT
    // =====================================================================
    await client.query('COMMIT');
    console.log('5/5 ✔ Migración completada exitosamente');

  } catch (err) {
    await client.query('ROLLBACK');
    console.error('✘ Error en la migración:', err.message);
    process.exit(1);
  } finally {
    client.release();
    await db.pool.end();
  }
}

migrate();

