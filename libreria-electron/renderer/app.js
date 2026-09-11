/**
 * app.js – Renderer process
 * --------------------------
 * • Consume EXCLUSIVAMENTE XML del microservicio.
 * • Parsea el XML con DOMParser (nativo del browser).
 * • URL y endpoint configurables, persistidos en localStorage.
 * • Paginación del lado del cliente (el microservicio devuelve todo).
 */

// ══════════════════════════════════════════════════════════════════════════
//  CONFIGURACIÓN (localStorage)
// ══════════════════════════════════════════════════════════════════════════

const DEFAULTS = {
  baseUrl:  'http://34.51.99.221:5001',
  endpoint: '/books',
};

function getConfig() {
  return {
    baseUrl:  localStorage.getItem('cfg_baseUrl')  || DEFAULTS.baseUrl,
    endpoint: localStorage.getItem('cfg_endpoint') || DEFAULTS.endpoint,
  };
}

function saveConfig(baseUrl, endpoint) {
  localStorage.setItem('cfg_baseUrl',  baseUrl);
  localStorage.setItem('cfg_endpoint', endpoint);
}

function getFullUrl() {
  const cfg = getConfig();
  // Quitar trailing slash de baseUrl y asegurar leading slash en endpoint
  const base = cfg.baseUrl.replace(/\/+$/, '');
  const ep   = cfg.endpoint.startsWith('/') ? cfg.endpoint : '/' + cfg.endpoint;
  return base + ep;
}

// ══════════════════════════════════════════════════════════════════════════
//  ESTADO
// ══════════════════════════════════════════════════════════════════════════

const PAGE_SIZE    = 12;
let allBooks       = [];   // todos los libros parseados del XML
let filteredBooks  = [];   // filtrados por búsqueda
let currentPage    = 1;
let currentSearch  = '';
let isLoading      = false;

// ══════════════════════════════════════════════════════════════════════════
//  DOM
// ══════════════════════════════════════════════════════════════════════════

const grid            = document.getElementById('booksGrid');
const loadingEl       = document.getElementById('loading');
const emptyState      = document.getElementById('emptyState');
const errorState      = document.getElementById('errorState');
const errorMessage    = document.getElementById('errorMessage');
const pagination      = document.getElementById('pagination');
const searchInput     = document.getElementById('searchInput');
const searchBtn       = document.getElementById('searchBtn');
const clearBtn        = document.getElementById('clearBtn');
const refreshBtn      = document.getElementById('refreshBtn');
const retryBtn        = document.getElementById('retryBtn');
const resultCount     = document.getElementById('resultCount');
const connStatus      = document.getElementById('connectionStatus');
const sourceUrlEl     = document.getElementById('sourceUrl');

// Settings modal
const settingsBtn     = document.getElementById('settingsBtn');
const settingsModal   = document.getElementById('settingsModal');
const closeModal      = document.getElementById('closeModal');
const cfgBaseUrl      = document.getElementById('cfgBaseUrl');
const cfgEndpoint     = document.getElementById('cfgEndpoint');
const cfgPreview      = document.getElementById('cfgPreview');
const cfgSave         = document.getElementById('cfgSave');
const cfgReset        = document.getElementById('cfgReset');

// ══════════════════════════════════════════════════════════════════════════
//  XML PARSER
// ══════════════════════════════════════════════════════════════════════════

function parseXMLBooks(xmlText, sourceUrl = '') {
  const parser  = new DOMParser();
  const xmlDoc  = parser.parseFromString(xmlText, 'application/xml');

  // Verificar errores de parsing
  const parseError = xmlDoc.querySelector('parsererror');
  if (parseError) {
    throw new Error('El XML recibido no es válido');
  }

  const bookElements = xmlDoc.querySelectorAll('book');
  const books = [];

  bookElements.forEach(bookEl => {
    const book = {};

    // ISBN (atributo)
    book.isbn = bookEl.getAttribute('isbn') || '';

    // Campos de texto simples
    book.title   = getTextContent(bookEl, 'title');
    book.year    = getTextContent(bookEl, 'year');
    book.price   = getTextContent(bookEl, 'price');
    book.stock   = getTextContent(bookEl, 'stock');
    book.format  = getTextContent(bookEl, 'format');

    // Autores (array)
    book.authors = [];
    bookEl.querySelectorAll('authors > author').forEach(a => {
      if (a.textContent.trim()) book.authors.push(a.textContent.trim());
    });

    // Géneros (array)
    book.genres = [];
    bookEl.querySelectorAll('genres > genre').forEach(g => {
      if (g.textContent.trim()) book.genres.push(g.textContent.trim());
    });

    // Imágenes (array de objetos con soporte para cualquier atributo, texto interno o ruta relativa)
    book.images = extractBookImages(bookEl, sourceUrl);

    books.push(book);
  });

  return books;
}

function extractBookImages(bookEl, sourceUrl) {
  const images = [];
  const imgNodes = bookEl.querySelectorAll('images > image, image, cover, cover_image, img');

  imgNodes.forEach(node => {
    let rawUri = node.getAttribute('uri') ||
                 node.getAttribute('url') ||
                 node.getAttribute('src') ||
                 node.getAttribute('href') ||
                 node.getAttribute('filename');

    const textContent = node.textContent ? node.textContent.trim() : '';

    if (!rawUri && textContent) {
      if (textContent.startsWith('http://') ||
          textContent.startsWith('https://') ||
          textContent.startsWith('/') ||
          /\.(jpg|jpeg|png|webp|gif|svg)/i.test(textContent)) {
        rawUri = textContent;
      }
    }

    if (rawUri) {
      const resolved = resolveUri(rawUri, sourceUrl);
      images.push({
        uri: resolved,
        rawUri: rawUri,
        alt: (textContent && !textContent.startsWith('http')) ? textContent : ''
      });
    }
  });

  return images;
}

function resolveUri(uri, sourceUrl) {
  if (!uri) return '';
  uri = uri.trim();
  if (uri.startsWith('http://') || uri.startsWith('https://') || uri.startsWith('data:')) {
    return uri;
  }
  try {
    const parsed = new URL(sourceUrl);
    const origin = parsed.origin;
    if (uri.startsWith('/')) {
      return origin + uri;
    }
    if (!uri.includes('/')) {
      return origin + '/uploads/' + uri;
    }
    return origin + '/' + uri;
  } catch {
    return uri;
  }
}

function getTextContent(parent, tag) {
  const el = parent.querySelector(':scope > ' + tag);
  return el ? el.textContent.trim() : '';
}

// ══════════════════════════════════════════════════════════════════════════
//  FETCH + RENDER
// ══════════════════════════════════════════════════════════════════════════

async function fetchBooks() {
  if (isLoading) return;
  isLoading = true;

  const url = getFullUrl();

  // UI: loading
  grid.innerHTML = '';
  loadingEl.style.display   = 'block';
  emptyState.style.display  = 'none';
  errorState.style.display  = 'none';
  pagination.style.display  = 'none';
  resultCount.textContent   = '';

  setStatus('loading', '⏳ Cargando...');
  sourceUrlEl.textContent = url;

  try {
    const result = await window.api.fetchXML(url);

    if (!result.ok) {
      throw new Error(result.error);
    }

    allBooks = parseXMLBooks(result.data, url);

    setStatus('ok', `✅ Conectado · ${allBooks.length} libros`);
    loadingEl.style.display = 'none';

    // Aplicar búsqueda si hay una activa
    applyFilterAndRender();

  } catch (err) {
    loadingEl.style.display = 'none';
    errorState.style.display = 'block';
    errorMessage.textContent = err.message;
    setStatus('err', '❌ Error de conexión');
    console.error('Error fetching XML:', err);
  } finally {
    isLoading = false;
  }
}

function applyFilterAndRender() {
  const term = currentSearch.toLowerCase();

  if (term) {
    filteredBooks = allBooks.filter(b =>
      b.title.toLowerCase().includes(term) ||
      b.isbn.toLowerCase().includes(term) ||
      b.authors.join(', ').toLowerCase().includes(term)
    );
  } else {
    filteredBooks = [...allBooks];
  }

  if (filteredBooks.length === 0) {
    grid.innerHTML = '';
    emptyState.style.display = 'block';
    pagination.style.display = 'none';
    resultCount.textContent = 'Sin resultados';
    return;
  }

  emptyState.style.display = 'none';
  renderPage(currentPage);
}

function renderPage(page) {
  const totalPages = Math.max(1, Math.ceil(filteredBooks.length / PAGE_SIZE));
  page = Math.max(1, Math.min(page, totalPages));
  currentPage = page;

  const start = (page - 1) * PAGE_SIZE;
  const end   = Math.min(start + PAGE_SIZE, filteredBooks.length);
  const pageBooks = filteredBooks.slice(start, end);

  // Info
  resultCount.textContent = `Mostrando ${start + 1}–${end} de ${filteredBooks.length} libros`;

  // Renderizar cards
  grid.innerHTML = '';
  pageBooks.forEach(book => {
    grid.appendChild(createBookCard(book));
  });

  // Paginación
  renderPagination(page, totalPages);

  // Scroll arriba suavemente
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ══════════════════════════════════════════════════════════════════════════
//  CARD
// ══════════════════════════════════════════════════════════════════════════

function createBookCard(book) {
  const card = document.createElement('div');
  card.className = 'book-card';

  // ── Cover
  const coverDiv = document.createElement('div');
  coverDiv.className = 'book-cover';

  const primaryImage = (book.images && book.images.length > 0 && book.images[0].uri) ? book.images[0].uri : null;
  const isbnClean = book.isbn ? book.isbn.replace(/[^0-9X]/gi, '') : '';
  const openLibraryUrl = isbnClean.length >= 9
    ? `https://covers.openlibrary.org/b/isbn/${isbnClean}-L.jpg`
    : null;

  const targetSrc = primaryImage || openLibraryUrl;

  if (targetSrc) {
    const img = document.createElement('img');
    img.src = targetSrc;
    img.alt = book.title;
    img.loading = 'lazy';
    img.referrerPolicy = 'no-referrer';

    let fallbackStage = 0;
    img.onerror = () => {
      fallbackStage++;
      // Si la imagen falló en el puerto 5001 (Flask), probar en el puerto 3000 (Node.js public/uploads)
      if (fallbackStage === 1 && primaryImage && primaryImage.includes(':5001/')) {
        img.src = primaryImage.replace(':5001/', ':3000/');
        return;
      }
      // Si falló y tenemos URL de OpenLibrary por ISBN, probar con OpenLibrary
      if (fallbackStage <= 2 && openLibraryUrl && img.src !== openLibraryUrl) {
        img.src = openLibraryUrl;
        return;
      }
      // Si todo falla, mostrar placeholder con la letra inicial
      img.remove();
      addPlaceholder(coverDiv, book.title);
    };

    coverDiv.appendChild(img);
  } else {
    addPlaceholder(coverDiv, book.title);
  }
  card.appendChild(coverDiv);

  // ── Body
  const body = document.createElement('div');
  body.className = 'book-body';

  const titleEl = document.createElement('h3');
  titleEl.className = 'book-title';
  titleEl.textContent = book.title;
  titleEl.title = book.title;
  body.appendChild(titleEl);

  const authorsEl = document.createElement('p');
  authorsEl.className = 'book-authors';
  authorsEl.textContent = book.authors.length > 0
    ? book.authors.join(', ')
    : 'Autor desconocido';
  body.appendChild(authorsEl);

  // Tags
  const metaDiv = document.createElement('div');
  metaDiv.className = 'book-meta';

  metaDiv.appendChild(createTag(`ISBN: ${book.isbn}`));

  if (book.year) {
    metaDiv.appendChild(createTag(`📅 ${book.year}`));
  }

  book.genres.forEach(g => {
    const tag = createTag(g);
    tag.classList.add('tag-genre');
    metaDiv.appendChild(tag);
  });

  if (book.format) {
    metaDiv.appendChild(createTag(book.format));
  }

  body.appendChild(metaDiv);
  card.appendChild(body);

  // ── Footer
  const footer = document.createElement('div');
  footer.className = 'book-footer';

  const priceEl = document.createElement('span');
  priceEl.className = 'book-price';
  priceEl.textContent = `$${parseFloat(book.price || 0).toFixed(2)}`;
  footer.appendChild(priceEl);

  const stockEl = document.createElement('span');
  stockEl.className = 'book-stock';
  const stockNum = parseInt(book.stock, 10) || 0;
  if (stockNum > 5) {
    stockEl.classList.add('stock-available');
    stockEl.textContent = `${stockNum} en stock`;
  } else if (stockNum > 0) {
    stockEl.classList.add('stock-low');
    stockEl.textContent = `¡Solo ${stockNum}!`;
  } else {
    stockEl.classList.add('stock-none');
    stockEl.textContent = 'Sin stock';
  }
  footer.appendChild(stockEl);
  card.appendChild(footer);

  return card;
}

// ══════════════════════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════════════════════

function addPlaceholder(container, title) {
  const ph = document.createElement('div');
  ph.className = 'book-cover-placeholder';
  ph.textContent = title ? title.charAt(0).toUpperCase() : '?';
  container.appendChild(ph);
}

function createTag(text) {
  const span = document.createElement('span');
  span.className = 'tag';
  span.textContent = text;
  return span;
}

function setStatus(type, text) {
  connStatus.textContent = text;
  connStatus.className = 'status-badge';
  if (type === 'ok')      connStatus.classList.add('status-ok');
  if (type === 'err')     connStatus.classList.add('status-err');
  if (type === 'loading') connStatus.classList.add('status-loading');
}

// ══════════════════════════════════════════════════════════════════════════
//  PAGINATION
// ══════════════════════════════════════════════════════════════════════════

function renderPagination(page, totalPages) {
  pagination.innerHTML = '';

  if (totalPages <= 1) {
    pagination.style.display = 'none';
    return;
  }

  pagination.style.display = 'flex';

  // Anterior
  const prevBtn = document.createElement('button');
  prevBtn.className = 'page-btn';
  prevBtn.textContent = '◀ Anterior';
  prevBtn.disabled = page <= 1;
  prevBtn.addEventListener('click', () => renderPage(page - 1));
  pagination.appendChild(prevBtn);

  // Números
  const pages = getVisiblePages(page, totalPages);
  for (const p of pages) {
    if (p === '...') {
      const el = document.createElement('span');
      el.className = 'page-info';
      el.textContent = '···';
      pagination.appendChild(el);
    } else {
      const btn = document.createElement('button');
      btn.className = 'page-btn' + (p === page ? ' active' : '');
      btn.textContent = p;
      btn.addEventListener('click', () => renderPage(p));
      pagination.appendChild(btn);
    }
  }

  // Info
  const info = document.createElement('span');
  info.className = 'page-info';
  info.textContent = `Pág. ${page} de ${totalPages}`;
  pagination.appendChild(info);

  // Siguiente
  const nextBtn = document.createElement('button');
  nextBtn.className = 'page-btn';
  nextBtn.textContent = 'Siguiente ▶';
  nextBtn.disabled = page >= totalPages;
  nextBtn.addEventListener('click', () => renderPage(page + 1));
  pagination.appendChild(nextBtn);
}

function getVisiblePages(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = [1];
  if (current > 3)  pages.push('...');
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i);
  }
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

// ══════════════════════════════════════════════════════════════════════════
//  SETTINGS MODAL
// ══════════════════════════════════════════════════════════════════════════

function openSettings() {
  const cfg = getConfig();
  cfgBaseUrl.value   = cfg.baseUrl;
  cfgEndpoint.value  = cfg.endpoint;
  updatePreview();
  settingsModal.style.display = 'flex';
  cfgBaseUrl.focus();
}

function closeSettings() {
  settingsModal.style.display = 'none';
}

function updatePreview() {
  const base = (cfgBaseUrl.value || DEFAULTS.baseUrl).replace(/\/+$/, '');
  const ep   = cfgEndpoint.value || DEFAULTS.endpoint;
  const epFormatted = ep.startsWith('/') ? ep : '/' + ep;
  cfgPreview.textContent = base + epFormatted;
}

settingsBtn.addEventListener('click', openSettings);
closeModal.addEventListener('click', closeSettings);

settingsModal.addEventListener('click', (e) => {
  if (e.target === settingsModal) closeSettings();
});

cfgBaseUrl.addEventListener('input', updatePreview);
cfgEndpoint.addEventListener('input', updatePreview);

cfgSave.addEventListener('click', () => {
  const base = cfgBaseUrl.value.trim() || DEFAULTS.baseUrl;
  const ep   = cfgEndpoint.value.trim() || DEFAULTS.endpoint;
  saveConfig(base, ep);
  closeSettings();
  currentPage = 1;
  currentSearch = '';
  searchInput.value = '';
  clearBtn.style.display = 'none';
  fetchBooks();
});

cfgReset.addEventListener('click', () => {
  cfgBaseUrl.value  = DEFAULTS.baseUrl;
  cfgEndpoint.value = DEFAULTS.endpoint;
  updatePreview();
});

// Escape para cerrar
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && settingsModal.style.display === 'flex') {
    closeSettings();
  }
});

// ══════════════════════════════════════════════════════════════════════════
//  EVENTOS
// ══════════════════════════════════════════════════════════════════════════

searchBtn.addEventListener('click', () => {
  currentSearch = searchInput.value.trim();
  currentPage = 1;
  clearBtn.style.display = currentSearch ? 'inline-block' : 'none';
  applyFilterAndRender();
});

clearBtn.addEventListener('click', () => {
  searchInput.value = '';
  currentSearch = '';
  currentPage = 1;
  clearBtn.style.display = 'none';
  applyFilterAndRender();
});

searchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') searchBtn.click();
});

refreshBtn.addEventListener('click', () => fetchBooks());
retryBtn.addEventListener('click',   () => fetchBooks());

// ══════════════════════════════════════════════════════════════════════════
//  CARGA INICIAL
// ══════════════════════════════════════════════════════════════════════════

sourceUrlEl.textContent = getFullUrl();
fetchBooks();
