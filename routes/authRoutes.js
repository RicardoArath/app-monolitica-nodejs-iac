// routes/authRoutes.js
const express = require('express');
const router = express.Router();
const userService = require('../services/userService');
const { redirectIfAuthenticated } = require('../middleware/auth');

router.get('/register', redirectIfAuthenticated, (req, res) => {
  res.render('auth/register', { title: 'Crear cuenta' });
});

router.post('/register', redirectIfAuthenticated, async (req, res, next) => {
  try {
    const { username, email, password, confirmPassword } = req.body;

    if (!username || !email || !password) {
      req.flash('error', 'Todos los campos son obligatorios.');
      return res.redirect('/register');
    }
    if (password !== confirmPassword) {
      req.flash('error', 'Las contraseñas no coinciden.');
      return res.redirect('/register');
    }
    if (password.length < 8) {
      req.flash('error', 'La contraseña debe tener al menos 8 caracteres.');
      return res.redirect('/register');
    }

    const existing = await userService.findByEmailOrUsername(email, username);
    if (existing) {
      req.flash('error', 'Ya existe una cuenta con ese usuario o correo.');
      return res.redirect('/register');
    }

    await userService.register(username.trim(), email.trim().toLowerCase(), password);
    req.flash('success', 'Cuenta creada. Ahora puedes iniciar sesión.');
    res.redirect('/login');
  } catch (err) {
    next(err);
  }
});

router.get('/login', redirectIfAuthenticated, (req, res) => {
  res.render('auth/login', { title: 'Iniciar sesión' });
});

router.post('/login', redirectIfAuthenticated, async (req, res, next) => {
  try {
    const { username, password } = req.body;
    const user = await userService.findByUsername(username);

    if (!user) {
      req.flash('error', 'Usuario o contraseña incorrectos.');
      return res.redirect('/login');
    }

    const validPassword = await userService.verifyPassword(password, user.password_hash);
    if (!validPassword) {
      req.flash('error', 'Usuario o contraseña incorrectos.');
      return res.redirect('/login');
    }

    req.session.regenerate((err) => {
      if (err) return next(err);
      req.session.user = { id: user.id, username: user.username, role: user.role };
      req.flash('success', `Bienvenido, ${user.username}.`);
      res.redirect(user.role === 'admin' ? '/admin' : '/');
    });
  } catch (err) {
    next(err);
  }
});

router.post('/logout', (req, res) => {
  req.session.destroy(() => {
    res.redirect('/login');
  });
});

module.exports = router;
