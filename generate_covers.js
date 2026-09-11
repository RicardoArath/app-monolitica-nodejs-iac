/**
 * generate_covers.js
 * -------------------
 * Genera portadas atractivas en PNG puro (usando zlib nativo) para todos
 * los libros de la base de datos, las guarda en public/uploads/ y
 * actualiza la tabla book_images en PostgreSQL.
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const db = require('./config/db');

const UPLOADS_DIR = path.join(__dirname, 'public', 'uploads');
if (!fs.existsSync(UPLOADS_DIR)) {
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

// ── Paletas de colores elegantes para las portadas ─────────────────────────
const PALETTES = [
  { top: [15, 32, 67],    bottom: [39, 71, 134],   accent: [245, 197, 24] },  // Deep Navy + Gold
  { top: [20, 50, 40],    bottom: [42, 110, 85],   accent: [255, 215, 0] },   // Emerald Forest
  { top: [60, 15, 30],    bottom: [130, 30, 60],   accent: [255, 180, 120] }, // Crimson Wine
  { top: [40, 20, 60],    bottom: [85, 45, 125],   accent: [200, 160, 255] }, // Royal Violet
  { top: [65, 40, 15],    bottom: [140, 85, 30],   accent: [255, 230, 150] }, // Warm Amber
  { top: [20, 45, 60],    bottom: [35, 95, 125],   accent: [120, 220, 240] }, // Dark Cyan
  { top: [30, 35, 45],    bottom: [65, 75, 95],    accent: [230, 120, 100] }, // Slate Coral
  { top: [50, 20, 20],    bottom: [110, 45, 45],   accent: [250, 200, 100] }, // Rust Mahogany
];

// ── Generador de PNG en memoria ───────────────────────────────────────────
function crc32(buf) {
  let crc = 0 ^ (-1);
  for (let i = 0; i < buf.length; i++) {
    crc = (crc >>> 8) ^ CRC_TABLE[(crc ^ buf[i]) & 0xFF];
  }
  return (crc ^ (-1)) >>> 0;
}

const CRC_TABLE = new Int32Array(256);
for (let n = 0; n < 256; n++) {
  let c = n;
  for (let k = 0; k < 8; k++) {
    c = ((c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1));
  }
  CRC_TABLE[n] = c;
}

function createChunk(type, data) {
  const typeBuf = Buffer.from(type);
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);

  const crcData = Buffer.concat([typeBuf, data]);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(crcData), 0);

  return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

function generateBookCoverPNG(width, height, palette, bookNum) {
  const rowBytes = width * 4;
  const rawData = Buffer.alloc((rowBytes + 1) * height);

  for (let y = 0; y < height; y++) {
    const rowOffset = y * (rowBytes + 1);
    rawData[rowOffset] = 0; // Filter: None

    const t = y / height;
    // Gradiente vertical
    const r = Math.round(palette.top[0] * (1 - t) + palette.bottom[0] * t);
    const g = Math.round(palette.top[1] * (1 - t) + palette.bottom[1] * t);
    const b = Math.round(palette.top[2] * (1 - t) + palette.bottom[2] * t);

    for (let x = 0; x < width; x++) {
      const px = rowOffset + 1 + x * 4;
      let pr = r;
      let pg = g;
      let pb = b;

      // Marco dorado exterior
      const isBorder = (x >= 16 && x <= 20 && y >= 16 && y <= height - 17) ||
                       (x >= width - 21 && x <= width - 17 && y >= 16 && y <= height - 17) ||
                       (y >= 16 && y <= 20 && x >= 16 && x <= width - 17) ||
                       (y >= height - 21 && y <= height - 17 && x >= 16 && x <= width - 17);

      // Marco interior delgado
      const isInnerBorder = (x >= 28 && x <= 30 && y >= 28 && y <= height - 29) ||
                            (x >= width - 31 && x <= width - 29 && y >= 28 && y <= height - 29) ||
                            (y >= 28 && y <= 30 && x >= 28 && x <= width - 29) ||
                            (y >= height - 31 && y <= height - 29 && x >= 28 && x <= width - 29);

      // Lomo izquierdo del libro (sombra de relieve)
      const isSpine = (x < 12);

      // Placa central decorativa para el libro
      const isBadge = (x >= 50 && x <= width - 51 && y >= 140 && y <= 300);
      const isBadgeBorder = isBadge && (x <= 54 || x >= width - 55 || y <= 144 || y >= 296);

      // Líneas horizontales ornamentales
      const isOrnament = (y >= 100 && y <= 103 && x >= 80 && x <= width - 81) ||
                         (y >= 340 && y <= 343 && x >= 80 && x <= width - 81);

      if (isSpine) {
        const shadow = Math.max(0, 0.4 + (x / 12) * 0.6);
        pr = Math.round(pr * shadow);
        pg = Math.round(pg * shadow);
        pb = Math.round(pb * shadow);
      } else if (isBorder || isInnerBorder || isOrnament || isBadgeBorder) {
        pr = palette.accent[0];
        pg = palette.accent[1];
        pb = palette.accent[2];
      } else if (isBadge) {
        // Fondo más oscuro en la placa
        pr = Math.max(0, Math.round(r * 0.4));
        pg = Math.max(0, Math.round(g * 0.4));
        pb = Math.max(0, Math.round(b * 0.4));
      }

      rawData[px]     = pr;
      rawData[px + 1] = pg;
      rawData[px + 2] = pb;
      rawData[px + 3] = 255;
    }
  }

  // PNG Signature
  const signature = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);

  // IHDR Chunk
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // Bit depth: 8
  ihdr[9] = 6; // Color type: RGBA
  ihdr[10] = 0; // Compression: Deflate
  ihdr[11] = 0; // Filter: Standard
  ihdr[12] = 0; // Interlace: None
  const ihdrChunk = createChunk('IHDR', ihdr);

  // IDAT Chunk
  const compressedData = zlib.deflateSync(rawData, { level: 6 });
  const idatChunk = createChunk('IDAT', compressedData);

  // IEND Chunk
  const iendChunk = createChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

async function main() {
  console.log('🚀 Iniciando generación de portadas para los libros...');

  const { rows: books } = await db.query('SELECT id, isbn, title FROM books ORDER BY id');
  console.log(`📚 Se encontraron ${books.length} libros en la base de datos.`);

  // Asegurar que la columna alt_text exista en book_images
  await db.query(`
    DO $$ BEGIN
      ALTER TABLE book_images ADD COLUMN IF NOT EXISTS alt_text VARCHAR(255);
    EXCEPTION WHEN duplicate_column THEN
      NULL;
    END $$;
  `);

  let count = 0;
  for (let i = 0; i < books.length; i++) {
    const book = books[i];
    const palette = PALETTES[i % PALETTES.length];
    const filename = `cover-book-${book.id}.png`;
    const filePath = path.join(UPLOADS_DIR, filename);

    // Generar imagen de 360x500 px
    const pngBuffer = generateBookCoverPNG(360, 500, palette, i + 1);
    fs.writeFileSync(filePath, pngBuffer);

    // Actualizar o insertar en book_images
    // Primero, marcar existentes de este libro como no primarias o eliminarlas
    await db.query('DELETE FROM book_images WHERE book_id = $1', [book.id]);

    await db.query(`
      INSERT INTO book_images (book_id, filename, mime_type, alt_text, is_primary)
      VALUES ($1, $2, $3, $4, true)
    `, [book.id, filename, 'image/png', `Portada de ${book.title}`]);

    count++;
    if (count % 5 === 0 || count === books.length) {
      console.log(`  ✔ Generadas ${count}/${books.length} portadas...`);
    }
  }

  console.log('🎉 ¡Todas las imágenes se generaron y registraron en la base de datos con éxito!');
  await db.pool.end();
  process.exit(0);
}

main().catch(err => {
  console.error('❌ Error generando imágenes:', err);
  process.exit(1);
});
