import tkinter as tk
from tkinter import ttk, messagebox
import threading

class CatalogView(ttk.Frame):
    def __init__(self, master, api_client, open_book_form, open_book_detail, **kwargs):
        super().__init__(master, **kwargs)
        self.api_client = api_client
        self.open_book_form = open_book_form
        self.open_book_detail = open_book_detail
        self.current_page = 1
        self.total_pages = 1
        
        self.pack(fill=tk.BOTH, expand=True)
        self._build_ui()
        self.load_data()
        
    def _build_ui(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Catálogo de Libros", font=('Helvetica', 14, 'bold')).pack(side=tk.LEFT)
        
        self.search_entry = ttk.Entry(top_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(20, 5))
        self.search_entry.bind('<Return>', lambda e: self._search())
        
        ttk.Button(top_frame, text="Buscar", command=self._search).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Nuevo Libro", command=lambda: self.open_book_form()).pack(side=tk.RIGHT)
        
        cols = ("title", "isbn", "authors", "price", "stock", "category", "format")
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        self.tree.heading("title", text="Título")
        self.tree.heading("isbn", text="ISBN")
        self.tree.heading("authors", text="Autor(es)")
        self.tree.heading("price", text="Precio")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("category", text="Categoría")
        self.tree.heading("format", text="Formato")
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree.bind("<Double-1>", self._on_double_click)
        
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.prev_btn = ttk.Button(bottom_frame, text="« Anterior", command=self._prev_page)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.page_label = ttk.Label(bottom_frame, text="Página 1 de 1")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.next_btn = ttk.Button(bottom_frame, text="Siguiente »", command=self._next_page)
        self.next_btn.pack(side=tk.LEFT)
        
    def _search(self):
        self.current_page = 1
        self.load_data()
        
    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()
            
    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_data()
            
    def load_data(self):
        q = self.search_entry.get().strip()
        threading.Thread(target=self._load_thread, args=(self.current_page, q), daemon=True).start()
        
    def _load_thread(self, page, q):
        try:
            res = self.api_client.get_books(page=page, q=q)
            self.after(0, self._update_ui, res)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error cargando libros: {e}"))
            
    def _update_ui(self, res):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        books = res.get('items', [])
        for b in books:
            authors = ", ".join([a.get('name', '') for a in b.get('authors', [])])
            cat = b.get('category', {}).get('name', '') if b.get('category') else ''
            fmt = b.get('format', {}).get('name', '') if b.get('format') else ''
            self.tree.insert("", tk.END, iid=b.get('id'), values=(
                b.get('title', ''), b.get('isbn', ''), authors, 
                f"${b.get('price', 0):.2f}", b.get('stock', 0), cat, fmt
            ))
            
        self.current_page = res.get('page', 1)
        self.total_pages = res.get('pages', 1)
        self.page_label.config(text=f"Página {self.current_page} de {self.total_pages}")
        
        self.prev_btn.config(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED)
        
    def _on_double_click(self, event):
        item_id = self.tree.selection()
        if item_id:
            self.open_book_detail(item_id[0])
