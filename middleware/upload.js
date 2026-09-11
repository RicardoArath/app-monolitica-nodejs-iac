// middleware/upload.js
// multipart/form-data se procesa aquí y se guarda directamente en
// disco (public/uploads). Nunca se serializa la imagen como JSON/base64
// para "enviarla" a otro componente: todo ocurre dentro del mismo
// proceso monolítico.
const path = require('path');
const crypto = require('crypto');
const multer = require('multer');

const ALLOWED_MIME = {
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp'
};

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, path.join(__dirname, '..', 'public', 'uploads'));
  },
  filename: (req, file, cb) => {
    const ext = ALLOWED_MIME[file.mimetype] || path.extname(file.originalname);
    const unique = crypto.randomBytes(12).toString('hex');
    cb(null, `book-${Date.now()}-${unique}${ext}`);
  }
});

function fileFilter(req, file, cb) {
  if (ALLOWED_MIME[file.mimetype]) {
    cb(null, true);
  } else {
    cb(new Error('Formato de imagen no permitido. Solo JPG, PNG o WebP.'));
  }
}

const maxBytes = parseInt(process.env.MAX_UPLOAD_BYTES, 10) || 5 * 1024 * 1024;

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: maxBytes }
});

module.exports = { upload, ALLOWED_MIME };
