-- =====================================================================
-- 06_views.sql
-- =====================================================================

BEGIN;

-- Vista de catálogo enriquecida: usada por la búsqueda y el home
CREATE OR REPLACE VIEW v_catalog AS
SELECT
    b.id,
    b.isbn,
    b.title,
    b.publication_year,
    b.price,
    b.stock,
    f.name AS format_name,
    c.name AS category_name,
    (SELECT filename FROM book_images bi
      WHERE bi.book_id = b.id AND bi.is_primary
      LIMIT 1) AS cover_image,
    (SELECT alt_text FROM book_images bi
      WHERE bi.book_id = b.id AND bi.is_primary
      LIMIT 1) AS cover_alt_text,
    (SELECT string_agg(a.name, ', ' ORDER BY a.name)
       FROM book_authors ba JOIN authors a ON a.id = ba.author_id
      WHERE ba.book_id = b.id) AS authors,
    (SELECT string_agg(g.name, ', ' ORDER BY g.name)
       FROM book_genres bg JOIN genres g ON g.id = bg.genre_id
      WHERE bg.book_id = b.id) AS genres
FROM books b
JOIN formats f    ON f.id = b.format_id
JOIN categories c ON c.id = b.category_id;

-- Vista de conteo de conceptos por libro (útil para el detalle)
CREATE OR REPLACE VIEW v_book_concept_counts AS
SELECT book_id, COUNT(*) AS total_concepts
FROM book_concepts
GROUP BY book_id;

-- Vista administrativa: resumen de usuarios por rol
CREATE OR REPLACE VIEW v_user_role_summary AS
SELECT role, COUNT(*) AS total
FROM users
GROUP BY role;

-- Vista administrativa y de historial: conserva el total del pedido y
-- su usuario sin exponer datos de pago fuera del servidor.
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

COMMIT;
