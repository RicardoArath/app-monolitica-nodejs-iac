// routes/orderRoutes.js
// Rutas para consultar historial y detalle de pedidos de un usuario.
// Protegido por requireLogin y validación de propiedad (aislamiento de datos).
const express = require('express');
const router = express.Router();
const orderService = require('../services/orderService');
const { requireLogin } = require('../middleware/auth');

router.use(requireLogin);

// Historial de pedidos del usuario autenticado
router.get('/', async (req, res, next) => {
  try {
    const orders = await orderService.getUserOrders(req.session.user.id);
    res.render('orders/index', {
      title: 'Mis Pedidos',
      orders
    });
  } catch (err) {
    next(err);
  }
});

// Detalle de un pedido específico
router.get('/:id', async (req, res, next) => {
  try {
    const orderId = parseInt(req.params.id, 10);
    if (Number.isNaN(orderId)) {
      req.flash('error', 'Identificador de pedido no válido.');
      return res.redirect('/orders');
    }

    // Pasamos req.session.user.id para que la consulta restrinja a sus pedidos (defensa IDOR / CA-07)
    const order = await orderService.getOrderDetail(orderId, req.session.user.id);
    if (!order) {
      req.flash('error', 'Pedido no encontrado o no tienes permiso para verlo.');
      return res.redirect('/orders');
    }

    res.render('orders/detail', {
      title: `Pedido #${order.id}`,
      order
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;

