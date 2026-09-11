// middleware/auth.js
// Autenticación basada en sesión de servidor (no hay tokens ni JSON).
// Actualmente express-session usa su almacenamiento en memoria; la
// persistencia en PostgreSQL queda pendiente antes de escalar a varias
// instancias.

const cartService = require('../services/cartService');

async function attachUserToViews(req, res, next) {
  res.locals.currentUser = req.session.user || null;
  res.locals.cartCount = 0;
  if (req.session.user) {
    try {
      res.locals.cartCount = await cartService.getItemCount(req.session.user.id);
    } catch (err) {
      res.locals.cartCount = 0;
    }
  }
  next();
}

function requireLogin(req, res, next) {
  if (!req.session.user) {
    req.flash('error', 'Debes iniciar sesión para continuar.');
    return res.redirect('/login');
  }
  next();
}

function requireAdmin(req, res, next) {
  if (!req.session.user || req.session.user.role !== 'admin') {
    req.flash('error', 'Esta sección está reservada para el administrador.');
    return res.redirect('/');
  }
  next();
}

// Evita que un usuario ya autenticado vuelva a ver login/registro
function redirectIfAuthenticated(req, res, next) {
  if (req.session.user) {
    return res.redirect('/');
  }
  next();
}

module.exports = { attachUserToViews, requireLogin, requireAdmin, redirectIfAuthenticated };
