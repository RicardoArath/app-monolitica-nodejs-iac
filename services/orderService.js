// services/orderService.js
// Lógica de negocio para órdenes, pagos simulados y estados de pedidos.
// Consume los procedimientos almacenados y vistas de PostgreSQL para
// garantizar consistencia transaccional y snapshots históricos.
const db = require('../config/db');

/**
 * Ejecuta el checkout invocando el procedimiento almacenado atómico en PostgreSQL.
 * sp_checkout_cart bloquea filas con FOR UPDATE, verifica stock, crea la orden,
 * congela precios históricos en snapshots, registra el pago simulado y, si es aprobado,
 * descuenta existencias y vacía el carrito.
 *
 * @param {number} userId - ID del usuario autenticado
 * @param {boolean} paymentApproved - true para simular pago aprobado, false para rechazado
 * @returns {Promise<number>} - ID de la orden creada
 */
async function checkout(userId, paymentApproved) {
  const { rows } = await db.query(
    'SELECT sp_checkout_cart($1, $2) AS order_id',
    [userId, Boolean(paymentApproved)]
  );
  return rows[0].order_id;
}

/**
 * Obtiene el historial de pedidos de un usuario específico usando la vista v_order_summary.
 *
 * @param {number} userId
 * @returns {Promise<Array>}
 */
async function getUserOrders(userId) {
  const { rows } = await db.query(
    `SELECT id, user_id, username, status, subtotal, total, payment_status, created_at, updated_at
       FROM v_order_summary
      WHERE user_id = $1
      ORDER BY created_at DESC`,
    [userId]
  );
  return rows;
}

/**
 * Obtiene el detalle completo de un pedido con sus partidas (snapshots) e información de pago.
 * Si se especifica userId, verifica que pertenezca a dicho usuario para evitar IDOR (CA-07).
 *
 * @param {number} orderId
 * @param {number|null} userId - Opcional; si se pasa, comprueba propiedad
 * @returns {Promise<Object|null>}
 */
async function getOrderDetail(orderId, userId = null) {
  let orderQuery = 'SELECT * FROM v_order_summary WHERE id = $1';
  const params = [orderId];

  if (userId !== null) {
    orderQuery += ' AND user_id = $2';
    params.push(userId);
  }

  const { rows: orderRows } = await db.query(orderQuery, params);
  const order = orderRows[0];
  if (!order) return null;

  const [itemsRes, paymentRes] = await Promise.all([
    db.query(
      `SELECT oi.id, oi.book_id, oi.title_snapshot, oi.unit_price, oi.quantity, oi.line_total,
              (SELECT bi.filename FROM book_images bi WHERE bi.book_id = oi.book_id AND bi.is_primary LIMIT 1) AS cover_image
         FROM order_items oi
        WHERE oi.order_id = $1
        ORDER BY oi.id`,
      [orderId]
    ),
    db.query(
      `SELECT id, method, status, amount, processed_at
         FROM simulated_payments
        WHERE order_id = $1`,
      [orderId]
    )
  ]);

  return {
    ...order,
    items: itemsRes.rows,
    payment: paymentRes.rows[0] || null
  };
}

/**
 * Lista todos los pedidos del sistema para el panel de administración.
 *
 * @returns {Promise<Array>}
 */
async function listAllOrders() {
  const { rows } = await db.query(
    `SELECT id, user_id, username, status, subtotal, total, payment_status, created_at, updated_at
       FROM v_order_summary
      ORDER BY created_at DESC`
  );
  return rows;
}

/**
 * Actualiza el estado de un pedido invocando sp_set_order_status.
 *
 * @param {number} orderId
 * @param {string} status - 'pending'|'confirmed'|'shipped'|'completed'|'cancelled'
 */
async function setOrderStatus(orderId, status) {
  await db.query('SELECT sp_set_order_status($1, $2)', [orderId, status]);
}

module.exports = {
  checkout,
  getUserOrders,
  getOrderDetail,
  listAllOrders,
  setOrderStatus
};

