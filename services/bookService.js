// services/bookService.js
const db = require('../config/db');

const PAGE_SIZE = 12;

async function searchCatalog(term, page = 1) {
  const safePage = Math.max(1, parseInt(page, 10) || 1);
  const offset = (safePage - 1) * PAGE_SIZE;
  const searchTerm = term && term.trim() !== '' ? term.trim() : null;

  const { rows } = await db.query(
    `SELECT id, isbn, title, price, stock, format_name, category_name, cover_image, authors, genres
       FROM v_catalog
      WHERE ($1::text IS NULL OR title ILIKE '%' || $1 || '%' OR isbn ILIKE '%' || $1 || '%')
      ORDER BY title
      LIMIT $2 OFFSET $3`,
    [searchTerm, PAGE_SIZE, offset]
  );

  const { rows: countRows } = await db.query(
    `SELECT COUNT(*) AS total
       FROM books
      WHERE ($1::text IS NULL OR title ILIKE '%' || $1 || '%' OR isbn ILIKE '%' || $1 || '%')`,
    [searchTerm]
  );

  const total = parseInt(countRows[0].total, 10);
  return {
    books: rows,
    total,
    page: safePage,
    totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)),
    term: term || ''
  };
}

async function getBookDetail(id) {
  const { rows } = await db.query(
    `SELECT b.*, f.name AS format_name, c.name AS category_name
       FROM books b
       JOIN formats f ON f.id = b.format_id
       JOIN categories c ON c.id = b.category_id
      WHERE b.id = $1`,
    [id]
  );
  const book = rows[0];
  if (!book) return null;

  const [authors, genres, concepts, images] = await Promise.all([
    db.query(
      `SELECT a.id, a.name FROM authors a
        JOIN book_authors ba ON ba.author_id = a.id
       WHERE ba.book_id = $1 ORDER BY a.name`,
      [id]
    ),
    db.query(
      `SELECT g.id, g.name FROM genres g
        JOIN book_genres bg ON bg.genre_id = g.id
       WHERE bg.book_id = $1 ORDER BY g.name`,
      [id]
    ),
    db.query(
      `SELECT id, name, definition, chapter, page_number FROM book_concepts
        WHERE book_id = $1 ORDER BY name`,
      [id]
    ),
    db.query(
      `SELECT id, filename, mime_type, alt_text, is_primary FROM book_images
        WHERE book_id = $1 ORDER BY is_primary DESC, id`,
      [id]
    )
  ]);

  return {
    ...book,
    authors: authors.rows,
    genres: genres.rows,
    concepts: concepts.rows,
    images: images.rows
  };
}

async function listAllBooksBasic() {
  const { rows } = await db.query(
    'SELECT id, isbn, title, price, stock FROM books ORDER BY title'
  );
  return rows;
}

async function createBook(data) {
  const { isbn, title, year, price, stock, formatId, categoryId, description, authorIds, genreIds } = data;
  const { rows } = await db.query(
    'SELECT sp_create_book($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) AS id',
    [isbn, title, year, price, stock, formatId, categoryId, description, authorIds, genreIds]
  );
  return rows[0].id;
}

async function updateBook(id, data) {
  const { isbn, title, year, price, stock, formatId, categoryId, description, authorIds, genreIds } = data;
  const client = await db.getClient();
  try {
    await client.query('BEGIN');
    await client.query(
      `UPDATE books
          SET isbn = $1, title = $2, publication_year = $3, price = $4,
              stock = $5, format_id = $6, category_id = $7, description = $8
        WHERE id = $9`,
      [isbn, title, year, price, stock, formatId, categoryId, description, id]
    );
    await client.query('SELECT sp_set_book_authors($1, $2)', [id, authorIds]);
    await client.query('SELECT sp_set_book_genres($1, $2)', [id, genreIds]);
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}

async function deleteBook(id) {
  await db.query('SELECT sp_delete_book($1)', [id]);
}

// --- Conceptos ---
async function addConcept(bookId, name, definition, chapter, pageNumber) {
  const { rows } = await db.query(
    'INSERT INTO book_concepts (book_id, name, definition, chapter, page_number) VALUES ($1,$2,$3,$4,$5) RETURNING id',
    [bookId, name, definition, chapter || null, pageNumber || null]
  );
  return rows[0].id;
}

async function updateConcept(conceptId, name, definition, chapter, pageNumber) {
  await db.query(
    'UPDATE book_concepts SET name = $1, definition = $2, chapter = $3, page_number = $4 WHERE id = $5',
    [name, definition, chapter || null, pageNumber || null, conceptId]
  );
}

async function deleteConcept(conceptId) {
  await db.query('DELETE FROM book_concepts WHERE id = $1', [conceptId]);
}

// --- Imágenes ---
async function addImage(bookId, filename, mimeType, altText, isPrimary) {
  const { rows } = await db.query(
    'INSERT INTO book_images (book_id, filename, mime_type, alt_text, is_primary) VALUES ($1,$2,$3,$4,$5) RETURNING id',
    [bookId, filename, mimeType, altText, isPrimary]
  );
  return rows[0].id;
}

async function setPrimaryImage(imageId) {
  await db.query('UPDATE book_images SET is_primary = true WHERE id = $1', [imageId]);
}

async function getImageById(imageId) {
  const { rows } = await db.query('SELECT * FROM book_images WHERE id = $1', [imageId]);
  return rows[0] || null;
}

async function deleteImage(imageId) {
  await db.query('DELETE FROM book_images WHERE id = $1', [imageId]);
}

module.exports = {
  searchCatalog,
  getBookDetail,
  listAllBooksBasic,
  createBook,
  updateBook,
  deleteBook,
  addConcept,
  updateConcept,
  deleteConcept,
  addImage,
  setPrimaryImage,
  getImageById,
  deleteImage
};
