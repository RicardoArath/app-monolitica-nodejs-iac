// routes/catalogRoutes.js
// Consulta de catálogo y conceptos, disponible para usuarios registrados.
const express = require('express');
const router = express.Router();
const bookService = require('../services/bookService');
const { requireLogin } = require('../middleware/auth');

router.get('/', requireLogin, async (req, res, next) => {
  try {
    const page = parseInt(req.query.page, 10) || 1;
    const term = req.query.q || '';
    const result = await bookService.searchCatalog(term, page);
    res.render('books/index', { title: 'Catálogo', ...result });
  } catch (err) {
    next(err);
  }
});

router.get('/books/:id', requireLogin, async (req, res, next) => {
  try {
    const book = await bookService.getBookDetail(req.params.id);
    if (!book) {
      req.flash('error', 'El libro solicitado no existe.');
      return res.redirect('/');
    }
    res.render('books/detail', { title: book.title, book });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
