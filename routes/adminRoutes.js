// routes/adminRoutes.js
// Todo lo que requiere rol 'admin'. Los formularios postean
// directamente aquí (application/x-www-form-urlencoded o
// multipart/form-data para imágenes); nunca JSON.
const express = require('express');
const fs = require('fs');
const path = require('path');
const router = express.Router();

const bookService = require('../services/bookService');
const catalogService = require('../services/catalogService');
const userService = require('../services/userService');
const orderService = require('../services/orderService');
const { requireAdmin } = require('../middleware/auth');
const { upload } = require('../middleware/upload');

router.use(requireAdmin);

// ---------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------
router.get('/', async (req, res, next) => {
  try {
    const [books, authors, genres, formats, categories, users, orders] = await Promise.all([
      bookService.listAllBooksBasic(),
      catalogService.list('authors'),
      catalogService.list('genres'),
      catalogService.list('formats'),
      catalogService.list('categories'),
      userService.listAll(),
      orderService.listAllOrders()
    ]);
    res.render('admin/dashboard', {
      title: 'Panel de administración',
      counts: {
        books: books.length,
        authors: authors.length,
        genres: genres.length,
        formats: formats.length,
        categories: categories.length,
        users: users.length,
        orders: orders.length
      }
    });
  } catch (err) {
    next(err);
  }
});

// ---------------------------------------------------------------------
// LIBROS
// ---------------------------------------------------------------------
router.get('/books', async (req, res, next) => {
  try {
    const books = await bookService.listAllBooksBasic();
    res.render('admin/books-list', { title: 'Administrar libros', books });
  } catch (err) {
    next(err);
  }
});

async function loadFormCatalogs() {
  const [authors, genres, formats, categories] = await Promise.all([
    catalogService.list('authors'),
    catalogService.list('genres'),
    catalogService.list('formats'),
    catalogService.list('categories')
  ]);
  return { authors, genres, formats, categories };
}

router.get('/books/new', async (req, res, next) => {
  try {
    const catalogs = await loadFormCatalogs();
    res.render('admin/book-form', {
      title: 'Nuevo libro',
      book: null,
      selectedAuthorIds: [],
      selectedGenreIds: [],
      ...catalogs
    });
  } catch (err) {
    next(err);
  }
});

function toIdArray(value) {
  if (!value) return [];
  const arr = Array.isArray(value) ? value : [value];
  return arr.map((v) => parseInt(v, 10)).filter((n) => !Number.isNaN(n));
}

router.post('/books/new', async (req, res, next) => {
  try {
    const { isbn, title, year, price, stock, formatId, categoryId, description } = req.body;
    const authorIds = toIdArray(req.body.authorIds);
    const genreIds = toIdArray(req.body.genreIds);

    if (!isbn || !title || !formatId || !categoryId) {
      req.flash('error', 'ISBN, título, formato y categoría son obligatorios.');
      return res.redirect('/admin/books/new');
    }

    const id = await bookService.createBook({
      isbn: isbn.trim(),
      title: title.trim(),
      year: year ? parseInt(year, 10) : null,
      price: parseFloat(price) || 0,
      stock: parseInt(stock, 10) || 0,
      formatId: parseInt(formatId, 10),
      categoryId: parseInt(categoryId, 10),
      description: description || null,
      authorIds,
      genreIds
    });

    req.flash('success', 'Libro creado correctamente.');
    res.redirect(`/admin/books/${id}/edit`);
  } catch (err) {
    if (err.code === '23505') {
      req.flash('error', 'Ya existe un libro con ese ISBN.');
      return res.redirect('/admin/books/new');
    }
    next(err);
  }
});

router.get('/books/:id/edit', async (req, res, next) => {
  try {
    const book = await bookService.getBookDetail(req.params.id);
    if (!book) {
      req.flash('error', 'El libro no existe.');
      return res.redirect('/admin/books');
    }
    const catalogs = await loadFormCatalogs();
    res.render('admin/book-form', {
      title: `Editar: ${book.title}`,
      book,
      selectedAuthorIds: book.authors.map((a) => a.id),
      selectedGenreIds: book.genres.map((g) => g.id),
      ...catalogs
    });
  } catch (err) {
    next(err);
  }
});

router.post('/books/:id/edit', async (req, res, next) => {
  try {
    const { isbn, title, year, price, stock, formatId, categoryId, description } = req.body;
    const authorIds = toIdArray(req.body.authorIds);
    const genreIds = toIdArray(req.body.genreIds);

    await bookService.updateBook(req.params.id, {
      isbn: isbn.trim(),
      title: title.trim(),
      year: year ? parseInt(year, 10) : null,
      price: parseFloat(price) || 0,
      stock: parseInt(stock, 10) || 0,
      formatId: parseInt(formatId, 10),
      categoryId: parseInt(categoryId, 10),
      description: description || null,
      authorIds,
      genreIds
    });

    req.flash('success', 'Libro actualizado correctamente.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    if (err.code === '23505') {
      req.flash('error', 'Ya existe un libro con ese ISBN.');
      return res.redirect(`/admin/books/${req.params.id}/edit`);
    }
    next(err);
  }
});

router.post('/books/:id/delete', async (req, res, next) => {
  try {
    await bookService.deleteBook(req.params.id);
    req.flash('success', 'Libro eliminado.');
    res.redirect('/admin/books');
  } catch (err) {
    next(err);
  }
});

// ---------------------------------------------------------------------
// CONCEPTOS de un libro
// ---------------------------------------------------------------------
router.post('/books/:id/concepts', async (req, res, next) => {
  try {
    const { name, definition, chapter, pageNumber } = req.body;
    if (!name || !definition) {
      req.flash('error', 'El concepto necesita nombre y definición.');
      return res.redirect(`/admin/books/${req.params.id}/edit`);
    }
    await bookService.addConcept(
      req.params.id, name.trim(), definition.trim(),
      chapter ? chapter.trim() : null,
      pageNumber ? parseInt(pageNumber, 10) : null
    );
    req.flash('success', 'Concepto agregado.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    if (err.code === '23505') {
      req.flash('error', 'Ese concepto ya existe para este libro.');
      return res.redirect(`/admin/books/${req.params.id}/edit`);
    }
    next(err);
  }
});

router.post('/books/:id/concepts/:conceptId/edit', async (req, res, next) => {
  try {
    const { name, definition, chapter, pageNumber } = req.body;
    await bookService.updateConcept(
      req.params.conceptId, name.trim(), definition.trim(),
      chapter ? chapter.trim() : null,
      pageNumber ? parseInt(pageNumber, 10) : null
    );
    req.flash('success', 'Concepto actualizado.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    next(err);
  }
});

router.post('/books/:id/concepts/:conceptId/delete', async (req, res, next) => {
  try {
    await bookService.deleteConcept(req.params.conceptId);
    req.flash('success', 'Concepto eliminado.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    next(err);
  }
});

// ---------------------------------------------------------------------
// IMÁGENES de un libro
// ---------------------------------------------------------------------
router.post('/books/:id/images', (req, res, next) => {
  upload.single('image')(req, res, (err) => {
    if (err) {
      req.flash('error', err.message);
      return res.redirect(`/admin/books/${req.params.id}/edit`);
    }
    next();
  });
}, async (req, res, next) => {
  try {
    if (!req.file) {
      req.flash('error', 'Selecciona una imagen JPG, PNG o WebP.');
      return res.redirect(`/admin/books/${req.params.id}/edit`);
    }
    const altText = (req.body.altText || '').trim();
    if (!altText) {
      req.flash('error', 'El texto alternativo es obligatorio.');
      return res.redirect(`/admin/books/${req.params.id}/edit`);
    }
    const isPrimary = req.body.isPrimary === 'on';
    await bookService.addImage(req.params.id, req.file.filename, req.file.mimetype, isPrimary);
    await bookService.addImage(req.params.id, req.file.filename, req.file.mimetype, altText, isPrimary);
    req.flash('success', 'Imagen subida correctamente.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    next(err);
  }
});

router.post('/books/:id/images/:imageId/primary', async (req, res, next) => {
  try {
    await bookService.setPrimaryImage(req.params.imageId);
    req.flash('success', 'Imagen principal actualizada.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    next(err);
  }
});

router.post('/books/:id/images/:imageId/delete', async (req, res, next) => {
  try {
    const image = await bookService.getImageById(req.params.imageId);
    await bookService.deleteImage(req.params.imageId);
    if (image) {
      const filePath = path.join(__dirname, '..', 'public', 'uploads', image.filename);
      fs.unlink(filePath, () => {});
    }
    req.flash('success', 'Imagen eliminada.');
    res.redirect(`/admin/books/${req.params.id}/edit`);
  } catch (err) {
    next(err);
  }
});

// ---------------------------------------------------------------------
// CATÁLOGOS MAESTROS: autores, géneros, formatos, categorías
// ---------------------------------------------------------------------
const CATALOG_LABELS = {
  authors: 'Autores',
  genres: 'Géneros',
  formats: 'Formatos',
  categories: 'Categorías'
};

router.get('/catalog/:table', async (req, res, next) => {
  try {
    const { table } = req.params;
    if (!CATALOG_LABELS[table]) return res.status(404).render('errors/404', { title: 'No encontrado' });
    const items = await catalogService.list(table);
    res.render('admin/catalog-list', {
      title: CATALOG_LABELS[table],
      table,
      label: CATALOG_LABELS[table],
      items
    });
  } catch (err) {
    next(err);
  }
});

router.post('/catalog/:table/new', async (req, res, next) => {
  try {
    const { table } = req.params;
    if (!CATALOG_LABELS[table]) return res.status(404).render('errors/404', { title: 'No encontrado' });
    const { name } = req.body;
    if (!name || !name.trim()) {
      req.flash('error', 'El nombre es obligatorio.');
      return res.redirect(`/admin/catalog/${table}`);
    }
    await catalogService.create(table, name.trim());
    req.flash('success', 'Registro creado.');
    res.redirect(`/admin/catalog/${table}`);
  } catch (err) {
    if (err.code === '23505') {
      req.flash('error', 'Ya existe un registro con ese nombre.');
      return res.redirect(`/admin/catalog/${req.params.table}`);
    }
    next(err);
  }
});

router.post('/catalog/:table/:id/edit', async (req, res, next) => {
  try {
    const { table, id } = req.params;
    if (!CATALOG_LABELS[table]) return res.status(404).render('errors/404', { title: 'No encontrado' });
    await catalogService.update(table, id, req.body.name.trim());
    req.flash('success', 'Registro actualizado.');
    res.redirect(`/admin/catalog/${table}`);
  } catch (err) {
    if (err.code === '23505') {
      req.flash('error', 'Ya existe un registro con ese nombre.');
      return res.redirect(`/admin/catalog/${req.params.table}`);
    }
    next(err);
  }
});

router.post('/catalog/:table/:id/delete', async (req, res, next) => {
  try {
    const { table, id } = req.params;
    if (!CATALOG_LABELS[table]) return res.status(404).render('errors/404', { title: 'No encontrado' });
    await catalogService.remove(table, id);
    req.flash('success', 'Registro eliminado.');
    res.redirect(`/admin/catalog/${table}`);
  } catch (err) {
    if (err.code === '23503') {
      req.flash('error', 'No se puede eliminar: está en uso por uno o más libros.');
      return res.redirect(`/admin/catalog/${req.params.table}`);
    }
    next(err);
  }
});

// ---------------------------------------------------------------------
// USUARIOS (solo lectura: el alta ocurre por /register)
// ---------------------------------------------------------------------
router.get('/users', async (req, res, next) => {
  try {
    const users = await userService.listAll();
    res.render('admin/users-list', { title: 'Usuarios registrados', users });
  } catch (err) {
    next(err);
  }
});

// ---------------------------------------------------------------------
// PEDIDOS (gestión de estados)
// ---------------------------------------------------------------------
router.get('/orders', async (req, res, next) => {
  try {
    const orders = await orderService.listAllOrders();
    res.render('admin/orders-list', { title: 'Gestión de pedidos', orders });
  } catch (err) {
    next(err);
  }
});

router.get('/orders/:id', async (req, res, next) => {
  try {
    const orderId = parseInt(req.params.id, 10);
    if (Number.isNaN(orderId)) {
      req.flash('error', 'Pedido no válido.');
      return res.redirect('/admin/orders');
    }

    const order = await orderService.getOrderDetail(orderId);
    if (!order) {
      req.flash('error', 'Pedido no encontrado.');
      return res.redirect('/admin/orders');
    }

    res.render('admin/order-detail', { title: `Administrar Pedido #${order.id}`, order });
  } catch (err) {
    next(err);
  }
});

router.post('/orders/:id/status', async (req, res, next) => {
  try {
    const orderId = parseInt(req.params.id, 10);
    const { status } = req.body;

    await orderService.setOrderStatus(orderId, status);
    req.flash('success', `Estado del pedido #${orderId} actualizado a "${status}".`);
    res.redirect(`/admin/orders/${orderId}`);
  } catch (err) {
    req.flash('error', err.message || 'Error al actualizar el estado del pedido.');
    res.redirect(`/admin/orders/${req.params.id}`);
  }
});

module.exports = router;
