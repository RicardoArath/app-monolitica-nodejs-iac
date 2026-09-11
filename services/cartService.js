// services/cartService.js
// Operaciones del carrito de compras. Un usuario tiene como máximo
// un carrito activo (restricción UNIQUE en carts.user_id).
// Todas las consultas son parametrizadas ($1, $2…).
const db = require('../config/db');

/**
 * Obtiene el carrito del usuario o lo crea si no existe.
 * Devuelve el id del carrito.
 */
async function getOrCreateCart(userId) {
  // Intenta obtener el carrito existente
  const { rows } = await db.query(
    'SELECT id FROM carts WHERE user_id = $1',
    [userId]
  );
  if (rows.length > 0) return rows[0].id;

  // Si no existe, lo crea
  const { rows: created } = await db.query(
    'INSERT INTO carts (user_id) VALUES ($1) RETURNING id',
    [userId]
  );
  return created[0].id;
}

/**
 * Devuelve el carrito con sus partidas, incluyendo datos del libro
 * (título, precio, stock, portada) para renderizar la vista.
 */
async function getCartWithItems(userId) {
  const cartId = await getOrCreateCart(userId);

  const { rows: items } = await db.query(
    `SELECT ci.book_id, ci.quantity,
            b.title, b.price, b.stock,
            (SELECT bi.filename FROM book_images bi
              WHERE bi.book_id = b.id AND bi.is_primary LIMIT 1) AS cover_image
       FROM cart_items ci
       JOIN books b ON b.id = ci.book_id
      WHERE ci.cart_id = $1
      ORDER BY b.title`,
    [cartId]
  );

  // Calcular subtotales por línea y total general
  let total = 0;
  const enrichedItems = items.map(item => {
    const lineTotal = parseFloat(item.price) * item.quantity;
    total += lineTotal;
    return { ...item, lineTotal };
  });

  return {
    cartId,
    items: enrichedItems,
    total,
    itemCount: enrichedItems.reduce((sum, i) => sum + i.quantity, 0)
  };
}

/**
 * Agrega un libro al carrito. Si ya existe, incrementa la cantidad.
 * Valida contra el stock disponible antes de insertar.
 */
async function addItem(userId, bookId, quantity) {
  const qty = parseInt(quantity, 10);
  if (!qty || qty < 1) throw new Error('La cantidad debe ser al menos 1.');

  const cartId = await getOrCreateCart(userId);

  // Verificar stock disponible
  const { rows: bookRows } = await db.query(
    'SELECT stock, title FROM books WHERE id = $1', [bookId]
  );
  if (bookRows.length === 0) throw new Error('El libro no existe.');

  // Verificar cantidad actual en carrito
  const { rows: existing } = await db.query(
    'SELECT quantity FROM cart_items WHERE cart_id = $1 AND book_id = $2',
    [cartId, bookId]
  );
  const currentQty = existing.length > 0 ? existing[0].quantity : 0;
  const newQty = currentQty + qty;

  if (newQty > bookRows[0].stock) {
    throw new Error(`Stock insuficiente para "${bookRows[0].title}". Disponible: ${bookRows[0].stock}, solicitado: ${newQty}.`);
  }

  if (currentQty > 0) {
    // UPSERT: actualizar cantidad
    await db.query(
      'UPDATE cart_items SET quantity = $1 WHERE cart_id = $2 AND book_id = $3',
      [newQty, cartId, bookId]
    );
  } else {
    await db.query(
      'INSERT INTO cart_items (cart_id, book_id, quantity) VALUES ($1, $2, $3)',
      [cartId, bookId, qty]
    );
  }
}

/**
 * Actualiza la cantidad de un libro en el carrito.
 * Si la cantidad es 0 o menor, elimina la partida.
 */
async function updateItemQuantity(userId, bookId, quantity) {
  const qty = parseInt(quantity, 10);
  const cartId = await getOrCreateCart(userId);

  if (qty <= 0) {
    await db.query(
      'DELETE FROM cart_items WHERE cart_id = $1 AND book_id = $2',
      [cartId, bookId]
    );
    return;
  }

  // Verificar stock
  const { rows: bookRows } = await db.query(
    'SELECT stock, title FROM books WHERE id = $1', [bookId]
  );
  if (bookRows.length === 0) throw new Error('El libro no existe.');
  if (qty > bookRows[0].stock) {
    throw new Error(`Stock insuficiente para "${bookRows[0].title}". Disponible: ${bookRows[0].stock}.`);
  }

  await db.query(
    'UPDATE cart_items SET quantity = $1 WHERE cart_id = $2 AND book_id = $3',
    [qty, cartId, bookId]
  );
}

/**
 * Elimina un libro del carrito.
 */
async function removeItem(userId, bookId) {
  const cartId = await getOrCreateCart(userId);
  await db.query(
    'DELETE FROM cart_items WHERE cart_id = $1 AND book_id = $2',
    [cartId, bookId]
  );
}

/**
 * Cuenta el número total de artículos en el carrito (para el badge del navbar).
 */
async function getItemCount(userId) {
  const { rows } = await db.query(
    `SELECT COALESCE(SUM(ci.quantity), 0) AS count
       FROM cart_items ci
       JOIN carts c ON c.id = ci.cart_id
      WHERE c.user_id = $1`,
    [userId]
  );
  return parseInt(rows[0].count, 10);
}

module.exports = {
  getOrCreateCart,
  getCartWithItems,
  addItem,
  updateItemQuantity,
  removeItem,
  getItemCount
};
