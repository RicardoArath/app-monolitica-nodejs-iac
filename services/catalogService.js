// services/catalogService.js
// CRUD genérico para las tablas maestras/catálogo:
// authors, genres, formats, categories.
const db = require('../config/db');

const TABLES = {
  authors: 'authors',
  genres: 'genres',
  formats: 'formats',
  categories: 'categories'
};

function assertTable(table) {
  if (!TABLES[table]) {
    throw new Error(`Catálogo no soportado: ${table}`);
  }
  return TABLES[table];
}

async function list(table) {
  const t = assertTable(table);
  const { rows } = await db.query(`SELECT id, name FROM ${t} ORDER BY name`);
  return rows;
}

async function getById(table, id) {
  const t = assertTable(table);
  const { rows } = await db.query(`SELECT id, name FROM ${t} WHERE id = $1`, [id]);
  return rows[0] || null;
}

async function create(table, name) {
  const t = assertTable(table);
  const { rows } = await db.query(
    `INSERT INTO ${t} (name) VALUES ($1) RETURNING id`,
    [name]
  );
  return rows[0].id;
}

async function update(table, id, name) {
  const t = assertTable(table);
  await db.query(`UPDATE ${t} SET name = $1 WHERE id = $2`, [name, id]);
}

async function remove(table, id) {
  const t = assertTable(table);
  await db.query(`DELETE FROM ${t} WHERE id = $1`, [id]);
}

module.exports = { list, getById, create, update, remove, TABLES };
