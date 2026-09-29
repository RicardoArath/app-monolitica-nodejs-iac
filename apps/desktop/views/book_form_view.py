import tkinter as tk
from tkinter import ttk, messagebox
import threading

class BookFormView(tk.Toplevel):
    def __init__(self, master, api_client, book_id=None, on_success_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.api_client = api_client
        self.book_id = book_id
        self.on_success_callback = on_success_callback
        
        self.title("Editar Libro" if book_id else "Nuevo Libro")
        self.geometry("600x700")
        self.grab_set()
        
        self.catalogs = {}
        self._build_ui()
        self._load_dependencies()
        
    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        
        fields = [
            ("ISBN:", "isbn"),
            ("Título:", "title"),
            ("Año:", "publication_year"),
            ("Precio:", "price"),
            ("Stock:", "stock")
        ]
        
        self.entries = {}
        for i, f in enumerate(fields):
            ttk.Label(container, text=f[0]).grid(row=i, column=0, sticky=tk.W, pady=2)
            ent = ttk.Entry(container, width=50)
            ent.grid(row=i, column=1, pady=2, sticky=tk.W)
            self.entries[f[1]] = ent
            
        row = len(fields)
        
        ttk.Label(container, text="Formato:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.format_cb = ttk.Combobox(container, width=47, state="readonly")
        self.format_cb.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        
        ttk.Label(container, text="Categoría:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.category_cb = ttk.Combobox(container, width=47, state="readonly")
        self.category_cb.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        
        ttk.Label(container, text="Descripción:").grid(row=row, column=0, sticky=tk.NW, pady=2)
        self.desc_text = tk.Text(container, width=38, height=5)
        self.desc_text.grid(row=row, column=1, pady=2, sticky=tk.W)
        row += 1
        
        list_frame = ttk.Frame(container)
        list_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky=tk.W+tk.E)
        
        ttk.Label(list_frame, text="Autores:").grid(row=0, column=0, sticky=tk.W)
        self.authors_lb = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=6, exportselection=0)
        self.authors_lb.grid(row=1, column=0, padx=(0, 10))
        
        ttk.Label(list_frame, text="Géneros:").grid(row=0, column=1, sticky=tk.W)
        self.genres_lb = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, height=6, exportselection=0)
        self.genres_lb.grid(row=1, column=1)
        
        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=row+1, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.save_btn = ttk.Button(btn_frame, text="Guardar", command=self._save)
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        
    def _load_dependencies(self):
        threading.Thread(target=self._load_deps_thread, daemon=True).start()
        
    def _load_deps_thread(self):
        try:
            formats = self.api_client.get_catalog('formats').get('items', [])
            categories = self.api_client.get_catalog('categories').get('items', [])
            authors = self.api_client.get_catalog('authors').get('items', [])
            genres = self.api_client.get_catalog('genres').get('items', [])
            
            if self.book_id:
                book = self.api_client.get_book(self.book_id)
            else:
                book = None
                
            self.after(0, self._setup_ui, formats, categories, authors, genres, book)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error cargando datos: {e}"))
            self.after(0, self.destroy)
            
    def _setup_ui(self, formats, categories, authors, genres, book):
        self.catalogs['formats'] = {f['name']: f['id'] for f in formats}
        self.catalogs['categories'] = {c['name']: c['id'] for c in categories}
        self.catalogs['authors'] = authors
        self.catalogs['genres'] = genres
        
        self.format_cb['values'] = list(self.catalogs['formats'].keys())
        self.category_cb['values'] = list(self.catalogs['categories'].keys())
        
        for a in authors: self.authors_lb.insert(tk.END, a['name'])
        for g in genres: self.genres_lb.insert(tk.END, g['name'])
        
        if book:
            self.entries['isbn'].insert(0, book.get('isbn', ''))
            self.entries['title'].insert(0, book.get('title', ''))
            self.entries['publication_year'].insert(0, book.get('publication_year', ''))
            self.entries['price'].insert(0, str(book.get('price', '')))
            self.entries['stock'].insert(0, str(book.get('stock', '')))
            self.desc_text.insert(1.0, book.get('description', ''))
            
            if book.get('format'): self.format_cb.set(book['format']['name'])
            if book.get('category'): self.category_cb.set(book['category']['name'])
            
            book_authors = [a['id'] for a in book.get('authors', [])]
            for i, a in enumerate(authors):
                if a['id'] in book_authors: self.authors_lb.selection_set(i)
                
            book_genres = [g['id'] for g in book.get('genres', [])]
            for i, g in enumerate(genres):
                if g['id'] in book_genres: self.genres_lb.selection_set(i)
                
    def _save(self):
        try:
            data = {
                "isbn": self.entries['isbn'].get().strip(),
                "title": self.entries['title'].get().strip(),
                "publication_year": int(self.entries['publication_year'].get().strip() or 0),
                "price": float(self.entries['price'].get().strip() or 0),
                "stock": int(self.entries['stock'].get().strip() or 0),
                "description": self.desc_text.get(1.0, tk.END).strip()
            }
            
            fmt_name = self.format_cb.get()
            if fmt_name: data["format_id"] = self.catalogs['formats'][fmt_name]
            
            cat_name = self.category_cb.get()
            if cat_name: data["category_id"] = self.catalogs['categories'][cat_name]
            
            sel_authors = self.authors_lb.curselection()
            data["author_ids"] = [self.catalogs['authors'][i]['id'] for i in sel_authors]
            
            sel_genres = self.genres_lb.curselection()
            data["genre_ids"] = [self.catalogs['genres'][i]['id'] for i in sel_genres]
            
            self.save_btn.config(state=tk.DISABLED)
            threading.Thread(target=self._save_thread, args=(data,), daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor verifique que los campos numéricos (Año, Precio, Stock) sean válidos.")
            
    def _save_thread(self, data):
        try:
            if self.book_id:
                self.api_client.update_book(self.book_id, data)
            else:
                self.api_client.create_book(data)
            self.after(0, self._handle_success)
        except Exception as e:
            self.after(0, lambda: self.save_btn.config(state=tk.NORMAL))
            self.after(0, lambda: messagebox.showerror("Error al guardar", str(e)))
            
    def _handle_success(self):
        messagebox.showinfo("Éxito", "Libro guardado correctamente")
        if self.on_success_callback:
            self.on_success_callback()
        self.destroy()
