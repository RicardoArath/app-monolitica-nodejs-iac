"""
ui/tabs/catalog_tab.py
Pestaña del Catálogo de Libros (GET /books?format=json).
Incluye:
- Filtros por ISBN, Título, Año, Precio Mínimo y Precio Máximo
- Tabla interactiva (Treeview) con columnas formateadas
- Paginación dinámica
- Apertura de ventana modal de detalle al hacer doble clic o pulsar 'Ver Detalle'
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.books_service import books_service
from ui.tabs.book_detail_dialog import BookDetailDialog


class CatalogTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.current_page = 1
        self.total_pages = 1
        self.books_cache = []

        self._build_ui()
        self.load_books()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Barra de Filtros
        # ---------------------------------------------------------
        filter_box = ttk.LabelFrame(self, text="🔍 Búsqueda y Filtros de Catálogo", padding=10)
        filter_box.pack(fill=tk.X, pady=(0, 10))

        # Fila 1: Título e ISBN
        r1 = ttk.Frame(filter_box)
        r1.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(r1, text="Título:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.txt_filter_title = ttk.Entry(r1, width=28)
        self.txt_filter_title.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(r1, text="ISBN:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.txt_filter_isbn = ttk.Entry(r1, width=18)
        self.txt_filter_isbn.pack(side=tk.LEFT, padx=(0, 15))

        # Fila 2: Año y Rango de Precios
        r2 = ttk.Frame(filter_box)
        r2.pack(fill=tk.X)

        ttk.Label(r2, text="Año:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.txt_filter_year = ttk.Entry(r2, width=8)
        self.txt_filter_year.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(r2, text="Precio Mín:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.txt_filter_min_price = ttk.Entry(r2, width=8)
        self.txt_filter_min_price.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(r2, text="Precio Máx:", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.txt_filter_max_price = ttk.Entry(r2, width=8)
        self.txt_filter_max_price.pack(side=tk.LEFT, padx=(0, 15))

        # Botones de Filtro
        self.btn_search = ttk.Button(r2, text="🔎 Filtrar", command=self._on_search)
        self.btn_search.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = ttk.Button(r2, text="↺ Limpiar", command=self._on_clear_filters)
        self.btn_clear.pack(side=tk.LEFT)

        # ---------------------------------------------------------
        # Tabla de Libros (Treeview)
        # ---------------------------------------------------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("isbn", "title", "authors", "genres", "year", "price", "stock", "format", "category")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("isbn", text="ISBN")
        self.tree.heading("title", text="Título")
        self.tree.heading("authors", text="Autor(es)")
        self.tree.heading("genres", text="Género(s)")
        self.tree.heading("year", text="Año")
        self.tree.heading("price", text="Precio")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("format", text="Formato")
        self.tree.heading("category", text="Categoría")

        self.tree.column("isbn", width=110, anchor=tk.W)
        self.tree.column("title", width=220, anchor=tk.W)
        self.tree.column("authors", width=150, anchor=tk.W)
        self.tree.column("genres", width=120, anchor=tk.W)
        self.tree.column("year", width=55, anchor=tk.CENTER)
        self.tree.column("price", width=70, anchor=tk.E)
        self.tree.column("stock", width=55, anchor=tk.CENTER)
        self.tree.column("format", width=110, anchor=tk.W)
        self.tree.column("category", width=100, anchor=tk.W)

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_double_click)

        # ---------------------------------------------------------
        # Barra Inferior: Paginación y Botón de Detalle
        # ---------------------------------------------------------
        bot_bar = ttk.Frame(self)
        bot_bar.pack(fill=tk.X, pady=(10, 0))

        self.btn_detail = ttk.Button(bot_bar, text="📖 Ver Detalle de Libro", command=self._open_selected_detail)
        self.btn_detail.pack(side=tk.LEFT)

        # Paginación (a la derecha)
        pager_frame = ttk.Frame(bot_bar)
        pager_frame.pack(side=tk.RIGHT)

        self.btn_prev = ttk.Button(pager_frame, text="◀ Anterior", command=self._prev_page)
        self.btn_prev.pack(side=tk.LEFT, padx=3)

        self.lbl_page_info = ttk.Label(pager_frame, text="Página 1 de 1", font=("Segoe UI", 9))
        self.lbl_page_info.pack(side=tk.LEFT, padx=8)

        self.btn_next = ttk.Button(pager_frame, text="Siguiente ▶", command=self._next_page)
        self.btn_next.pack(side=tk.LEFT, padx=3)

    def _on_search(self):
        self.current_page = 1
        self.load_books()

    def _on_clear_filters(self):
        self.txt_filter_title.delete(0, tk.END)
        self.txt_filter_isbn.delete(0, tk.END)
        self.txt_filter_year.delete(0, tk.END)
        self.txt_filter_min_price.delete(0, tk.END)
        self.txt_filter_max_price.delete(0, tk.END)
        self.current_page = 1
        self.load_books()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_books()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_books()

    def load_books(self):
        """Consulta el endpoint GET /books con los filtros actuales en un hilo secundario."""
        title = self.txt_filter_title.get().strip() or None
        isbn = self.txt_filter_isbn.get().strip() or None
        year = self.txt_filter_year.get().strip() or None
        min_p = self.txt_filter_min_price.get().strip() or None
        max_p = self.txt_filter_max_price.get().strip() or None

        self.btn_search.config(state=tk.DISABLED)

        def thread_task():
            res = books_service.get_books(
                isbn=isbn,
                title=title,
                year=year,
                min_price=min_p,
                max_price=max_p,
                page=self.current_page
            )
            self.after(0, lambda: self._on_books_loaded(res))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_books_loaded(self, res):
        self.btn_search.config(state=tk.NORMAL)

        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not res["success"]:
            msg = res["error"] or "Error al obtener libros del catálogo."
            if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                msg = res["data"]["message"]
            self.lbl_page_info.config(text="Error de conexión")
            messagebox.showwarning("Microservicio de Libros", f"No se pudo cargar el catálogo:\n\n{msg}")
            return

        data = res["data"] or {}
        books = data.get("books", [])
        meta = data.get("meta", {})

        self.total_pages = meta.get("totalPages", 1)
        total_items = meta.get("total", len(books))
        self.lbl_page_info.config(text=f"Página {self.current_page} de {self.total_pages} ({total_items} libros)")

        self.btn_prev.config(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED)

        self.books_cache = books

        for b in books:
            price_str = f"${b.get('price', 0):,.2f}"
            self.tree.insert("", tk.END, values=(
                b.get("isbn", ""),
                b.get("title", ""),
                b.get("authors", "") or "Sin autor",
                b.get("genres", "") or "Sin género",
                b.get("publication_year", "") or "N/A",
                price_str,
                b.get("stock", 0),
                b.get("format_name", ""),
                b.get("category_name", "")
            ))

    def _on_double_click(self, event):
        self._open_selected_detail()

    def _open_selected_detail(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selección requerida", "Seleccione un libro de la lista para ver su detalle.")
            return

        item = self.tree.item(selected[0])
        isbn = item["values"][0]
        BookDetailDialog(self, isbn)
