// routes/cartRoutes.js
// Rutas de gestión de carrito y checkout simulado.
// Requiere autenticación (requireLogin). Sin JSON; formularios clásicos.
const express = require('express');
const router = express.Router();
const cartService = require('../services/cartService');
const orderService = require('../services/orderService');
const { requireLogin } = require('../middleware/auth');

router.use(requireLogin);

// Ver carrito
router.get('/', async (req, res, next) => {
  try {
    const cart = await cartService.getCartWithItems(req.session.user.id);
    res.render('cart/index', {
      title: 'Carrito de compras',
      cart
    });
  } catch (err) {
    next(err);
  }
});

// Agregar item al carrito
router.post('/add', async (req, res, next) => {
  try {
    const bookId = parseInt(req.body.bookId, 10);
    const quantity = parseInt(req.body.quantity, 10) || 1;

    if (Number.isNaN(bookId) || quantity <= 0) {
      req.flash('error', 'Datos de libro o cantidad no válidos.');
      return res.redirect('/');
    }

    await cartService.addItem(req.session.user.id, bookId, quantity);
    req.flash('success', 'Libro agregado al carrito.');
    res.redirect('/cart');
  } catch (err) {
    req.flash('error', err.message || 'Error al agregar al carrito.');
    res.redirect(req.body.bookId ? `/books/${req.body.bookId}` : '/cart');
  }
});

// Actualizar cantidad de un item
router.post('/update', async (req, res, next) => {
  try {
    const bookId = parseInt(req.body.bookId, 10);
    const quantity = parseInt(req.body.quantity, 10);

    if (Number.isNaN(bookId) || Number.isNaN(quantity)) {
      req.flash('error', 'Cantidad no válida.');
      return res.redirect('/cart');
    }

    await cartService.updateItemQuantity(req.session.user.id, bookId, quantity);
    req.flash('success', 'Carrito actualizado.');
    res.redirect('/cart');
  } catch (err) {
    req.flash('error', err.message || 'Error al actualizar el carrito.');
    res.redirect('/cart');
  }
});

// Eliminar un item del carrito
router.post('/remove', async (req, res, next) => {
  try {
    const bookId = parseInt(req.body.bookId, 10);
    if (!Number.isNaN(bookId)) {
      await cartService.removeItem(req.session.user.id, bookId);
      req.flash('success', 'Artículo eliminado del carrito.');
    }
    res.redirect('/cart');
  } catch (err) {
    next(err);
  }
});

// Checkout con pago simulado (Opción 1: botón aprobado vs rechazado)
router.post('/checkout', async (req, res, next) => {
  try {
    const paymentOutcome = req.body.paymentOutcome;
    const paymentApproved = (paymentOutcome === 'approved');

    const orderId = await orderService.checkout(req.session.user.id, paymentApproved);

    if (paymentApproved) {
      req.flash('success', `¡Compra finalizada con éxito! Pedido #${orderId} confirmado y stock actualizado.`);
    } else {
      req.flash('error', `Pago simulado RECHAZADO. El pedido #${orderId} quedó pendiente y tus artículos siguen en el carrito.`);
    }

    res.redirect(`/orders/${orderId}`);
  } catch (err) {
    req.flash('error', err.message || 'No se pudo completar el checkout.');
    res.redirect('/cart');
  }
});

module.exports = router;

