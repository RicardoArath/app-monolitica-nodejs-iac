"""
ui/tabs/book_detail_dialog.py
Ventana modal de Detalle de Libro (GET /books/{isbn}).
Muestra:
- Datos editoriales completos (ISBN, Título, Año, Precio, Existencia, Formato, Categoría)
- Lista de Autores y Géneros
- Lista de Conceptos y Definiciones asociadas al libro
- Visualización de carátula o indicador visual si no dispone de imagen
"""
import io
import threading
import tkinter as tk
from tkinter import ttk
import urllib.request
from PIL import Image, ImageTk

from network.books_service import books_service
from config.settings import settings


class BookDetailDialog(tk.Toplevel):
    def __init__(self, parent, isbn):
        super().__init__(parent)
        self.isbn = isbn
        self.title(f"Detalle de Libro — ISBN: {isbn}")
        self.geometry("640x620")
        self.minsize(580, 500)

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (640 // 2)
        y = (self.winfo_screenheight() // 2) - (620 // 2)
        self.geometry(f"+{x}+{y}")

        self.cover_img_tk = None

        self._build_ui()
        self._load_detail()

    def _build_ui(self):
        # Header
        self.header = tk.Frame(self, bg="#0f172a", height=60)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        self.lbl_title = tk.Label(self.header, text="Cargando información...", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#0f172a")
        self.lbl_title.pack(anchor=tk.W, padx=15, pady=(10, 0))

        self.lbl_isbn_header = tk.Label(self.header, text=f"ISBN: {self.isbn}", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        self.lbl_isbn_header.pack(anchor=tk.W, padx=15)

        # Contenedor con scroll
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, padding=15)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Layout superior: carátula (izq) + metadatos (der)
        top_row = ttk.Frame(self.scrollable_frame)
        top_row.pack(fill=tk.X, pady=(0, 15))

        # Marco de carátula
        self.img_frame = tk.Frame(top_row, width=130, height=180, bg="#e2e8f0", relief="solid", bd=1)
        self.img_frame.pack(side=tk.LEFT, padx=(0, 15))
        self.img_frame.pack_propagate(False)

        self.lbl_image = tk.Label(self.img_frame, text="📖 Sin Imagen", font=("Segoe UI", 9), bg="#e2e8f0", fg="#64748b")
        self.lbl_image.pack(expand=True)

        # Metadatos básicos
        self.meta_frame = ttk.Frame(top_row)
        self.meta_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.lbl_price = ttk.Label(self.meta_frame, text="Precio: -", font=("Segoe UI", 11, "bold"), foreground="#0f766e")
        self.lbl_price.pack(anchor=tk.W, pady=2)

        self.lbl_stock = ttk.Label(self.meta_frame, text="Existencia: -", font=("Segoe UI", 10))
        self.lbl_stock.pack(anchor=tk.W, pady=2)

        self.lbl_year = ttk.Label(self.meta_frame, text="Año de publicación: -", font=("Segoe UI", 10))
        self.lbl_year.pack(anchor=tk.W, pady=2)

        self.lbl_format = ttk.Label(self.meta_frame, text="Formato: -", font=("Segoe UI", 10))
        self.lbl_format.pack(anchor=tk.W, pady=2)

        self.lbl_category = ttk.Label(self.meta_frame, text="Categoría: -", font=("Segoe UI", 10))
        self.lbl_category.pack(anchor=tk.W, pady=2)

        # Autores y Géneros
        self.lbl_authors = ttk.Label(self.scrollable_frame, text="✍️ Autores: -", font=("Segoe UI", 10, "bold"))
        self.lbl_authors.pack(anchor=tk.W, pady=(5, 3))

        self.lbl_genres = ttk.Label(self.scrollable_frame, text="🏷️ Géneros: -", font=("Segoe UI", 10))
        self.lbl_genres.pack(anchor=tk.W, pady=(0, 10))

        # Descripción
        ttk.Label(self.scrollable_frame, text="📝 Sinopsis / Descripción:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.txt_desc = tk.Text(self.scrollable_frame, height=4, wrap="word", font=("Segoe UI", 9), relief="solid", bd=1)
        self.txt_desc.pack(fill=tk.X, pady=(4, 15))

        # Conceptos y definiciones
        ttk.Separator(self.scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Label(self.scrollable_frame, text="🧠 Conceptos y Definiciones Asociados:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(5, 5))

        self.concepts_frame = ttk.Frame(self.scrollable_frame)
        self.concepts_frame.pack(fill=tk.X, pady=(0, 10))

    def _load_detail(self):
        def thread_task():
            res = books_service.get_book_by_isbn(self.isbn)
            self.after(0, lambda: self._on_detail_loaded(res))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_detail_loaded(self, res):
        if not res["success"]:
            msg = res["error"] or "Error al consultar el detalle del libro."
            if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                msg = res["data"]["message"]
            self.lbl_title.config(text="Error al cargar")
            self.lbl_price.config(text=msg, foreground="#ef4444")
            return

        book = res["data"].get("book", {})

        title_text = book.get("title", "Sin Título")
        self.lbl_title.config(text=title_text)
        self.lbl_price.config(text=f"Precio: ${book.get('price', 0):,.2f}")
        self.lbl_stock.config(text=f"Existencia en almacén: {book.get('stock', 0)} unidades")
        self.lbl_year.config(text=f"Año de publicación: {book.get('publication_year') or 'N/A'}")
        self.lbl_format.config(text=f"Formato: {book.get('format_name', 'N/A')}")
        self.lbl_category.config(text=f"Categoría: {book.get('category_name', 'N/A')}")

        # Autores
        authors = [a["name"] for a in book.get("authors", [])]
        self.lbl_authors.config(text=f"✍️ Autores: {', '.join(authors) if authors else 'Sin autor registrado'}")

        # Géneros
        genres = [g["name"] for g in book.get("genres", [])]
        self.lbl_genres.config(text=f"🏷️ Géneros: {', '.join(genres) if genres else 'Sin géneros asignados'}")

        # Descripción
        desc = book.get("description") or "Sin descripción disponible."
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert(tk.END, desc)
        self.txt_desc.config(state=tk.DISABLED)

        # Conceptos
        concepts = book.get("concepts", [])
        for widget in self.concepts_frame.winfo_children():
            widget.destroy()

        if not concepts:
            ttk.Label(self.concepts_frame, text="Este libro no tiene conceptos registrados en la base de datos.", font=("Segoe UI", 9, "italic"), foreground="#64748b").pack(anchor=tk.W)
        else:
            for c in concepts:
                card = ttk.Frame(self.concepts_frame, padding=5, relief="groove")
                card.pack(fill=tk.X, pady=3)
                c_name = c.get("name", "Concepto")
                c_def = c.get("definition", "")
                c_chap = f" (Cap: {c.get('chapter')})" if c.get("chapter") else ""
                c_page = f" pág. {c.get('page_number')}" if c.get("page_number") else ""

                ttk.Label(card, text=f"• {c_name}{c_chap}{c_page}", font=("Segoe UI", 9, "bold"), foreground="#0369a1").pack(anchor=tk.W)
                ttk.Label(card, text=c_def, font=("Segoe UI", 9), wraplength=520, justify=tk.LEFT).pack(anchor=tk.W, padx=(10, 0))

        # Imagen
        images = book.get("images", [])
        if images:
            img_info = images[0]
            filename = img_info.get("filename")
            if filename:
                self._load_cover_image(filename)

    def _load_cover_image(self, filename):
        # Intentar descargar desde el monolito Node.js /uploads/ o mostrar placeholder
        image_url = f"http://35.193.230.144:3000/uploads/{filename}"

        def thread_task():
            try:
                req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    raw_data = resp.read()
                image = Image.open(io.BytesIO(raw_data))
                image.thumbnail((120, 170))
                tk_img = ImageTk.PhotoImage(image)
                self.after(0, lambda: self._apply_cover_image(tk_img))
            except Exception:
                # Si falla o no existe carátula, se mantiene el placeholder sin error
                pass

        threading.Thread(target=thread_task, daemon=True).start()

    def _apply_cover_image(self, tk_img):
        self.cover_img_tk = tk_img
        self.lbl_image.config(image=self.cover_img_tk, text="")
