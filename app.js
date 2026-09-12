// app.js
// -----------------------------------------------------------------------
// Aplicación web MONOLÍTICA (interfaz + lógica de negocio + acceso a
// datos en un único proceso Node.js). Renderizado 100% del lado del
// servidor con EJS. No expone APIs REST/GraphQL/SOAP ni intercambia
// JSON/XML entre "componentes": los formularios HTML postean
// directamente a estas mismas rutas.
// -----------------------------------------------------------------------
require('dotenv').config();

const express = require('express');
const fs = require('fs');
const path = require('path');
const session = require('express-session');
const flash = require('express-flash');

const { attachUserToViews } = require('./middleware/auth');

const authRoutes = require('./routes/authRoutes');
const catalogRoutes = require('./routes/catalogRoutes');
const adminRoutes = require('./routes/adminRoutes');
const cartRoutes = require('./routes/cartRoutes');
const orderRoutes = require('./routes/orderRoutes');

const app = express();

// Asegurar que el directorio de uploads exista físicamente
fs.mkdirSync(path.join(__dirname, 'public', 'uploads'), { recursive: true });

// Vistas (capa de presentación)
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.set('trust proxy', 1);

// Middlewares de infraestructura
app.use(express.urlencoded({ extended: true })); // formularios HTML clásicos
app.use(express.static(path.join(__dirname, 'public')));

// Sesión en memoria del propio proceso Node.js: coherente con el
// despliegue monolítico de una sola instancia (ver docs/DECISIONES.md,
// sección "Sesiones", para la limitación de escalabilidad horizontal
// que esto implica y cómo migrarlo si la app creciera).
app.use(session({
  secret: process.env.SESSION_SECRET || 'dev-secret-cambiar',
  resave: false,
  saveUninitialized: false,
  cookie: {
    maxAge: 1000 * 60 * 60 * 8, // 8 horas
    httpOnly: true,
    sameSite: 'lax'
  }
}));

app.use(flash());
app.use(attachUserToViews);

// Rutas (todas renderizan HTML del lado del servidor)
app.use('/', authRoutes);
app.use('/', catalogRoutes);
app.use('/cart', cartRoutes);
app.use('/orders', orderRoutes);
app.use('/admin', adminRoutes);

// 404
app.use((req, res) => {
  res.status(404).render('errors/404', { title: 'Página no encontrada' });
});

// Manejo centralizado de errores
app.use((err, req, res, next) => { // eslint-disable-line no-unused-vars
  console.error(err);
  res.status(500).render('errors/500', {
    title: 'Error del servidor',
    message: process.env.NODE_ENV === 'production' ? null : err.message
  });
});

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';
app.listen(PORT, HOST, () => {
  console.log(`Librería en línea escuchando en http://${HOST}:${PORT}`);
});
