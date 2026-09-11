// config/db.js
// Punto único de acceso a PostgreSQL. Toda consulta SQL de la
// aplicación pasa por este pool, siempre con SQL parametrizado
// ($1, $2...) para evitar inyección SQL.

require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.PGHOST,
  port: process.env.PGPORT,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  max: 10,
  idleTimeoutMillis: 30000
});

pool.on('error', (err) => {
  console.error('Error inesperado en el pool de PostgreSQL:', err);
});

module.exports = {
  // Consulta simple
  query: (text, params) => pool.query(text, params),
  // Cliente dedicado para transacciones multi-sentencia
  getClient: () => pool.connect(),
  pool
};
