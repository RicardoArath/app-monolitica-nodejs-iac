// services/userService.js
const bcrypt = require('bcryptjs');
const db = require('../config/db');

const SALT_ROUNDS = 10;

async function findByUsername(username) {
  const { rows } = await db.query(
    'SELECT id, username, email, password_hash, role FROM users WHERE username = $1',
    [username]
  );
  return rows[0] || null;
}

async function findByEmailOrUsername(email, username) {
  const { rows } = await db.query(
    'SELECT id FROM users WHERE email = $1 OR username = $2',
    [email, username]
  );
  return rows[0] || null;
}

async function register(username, email, plainPassword) {
  const passwordHash = await bcrypt.hash(plainPassword, SALT_ROUNDS);
  // sp_register_user siempre crea el usuario con role = 'user'
  const { rows } = await db.query(
    'SELECT sp_register_user($1, $2, $3) AS id',
    [username, email, passwordHash]
  );
  return rows[0].id;
}

async function verifyPassword(plainPassword, passwordHash) {
  return bcrypt.compare(plainPassword, passwordHash);
}

async function adminExists() {
  const { rows } = await db.query("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'");
  return parseInt(rows[0].total, 10) > 0;
}

async function listAll() {
  const { rows } = await db.query(
    'SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC'
  );
  return rows;
}

module.exports = {
  findByUsername,
  findByEmailOrUsername,
  register,
  verifyPassword,
  adminExists,
  listAll
};
