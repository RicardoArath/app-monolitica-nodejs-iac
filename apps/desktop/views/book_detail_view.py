import tkinter as tk
from tkinter import ttk, messagebox
import threading

class BookDetailView(tk.Toplevel):
    def __init__(self, master, api_client, book_id, open_book_form, on_close_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.api_client = api_client
        self.book_id = book_id
        self.open_book_form = open_book_form
        self.on_close_callback = on_close_callback
        
        self.title("Detalle del Libro")
        self.geometry("500x600")
        self.grab_set()
        
        self._build_ui()
        self._load_data()
        
    def _build_ui(self):
        self.container = ttk.Frame(self, padding=20)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.title_lbl = ttk.Label(self.container, text="Cargando...", font=('Helvetica', 14, 'bold'), wraplength=450)
        self.title_lbl.pack(pady=(0, 10), anchor=tk.W)
        
        self.info_text = tk.Text(self.container, wrap=tk.WORD, state=tk.DISABLED, bg=self.cget('bg'), relief=tk.FLAT)
        self.info_text.pack(fill=tk.BOTH, expand=True, pady=10)
        
        btn_frame = ttk.Frame(self.container)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Eliminar", command=self._delete).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Editar", command=self._edit).pack(side=tk.RIGHT, padx=5)
        
    def _load_data(self):
        threading.Thread(target=self._load_thread, daemon=True).start()
        
    def _load_thread(self):
        try:
            book = self.api_client.get_book(self.book_id)
            self.after(0, self._update_ui, book)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error cargando libro: {e}"))
            self.after(0, self.destroy)
            
    def _update_ui(self, book):
        self.book_data = book
        self.title_lbl.config(text=book.get('title', ''))
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        cat = book.get('category', {}).get('name', '') if book.get('category') else 'N/A'
        fmt = book.get('format', {}).get('name', '') if book.get('format') else 'N/A'
        
        details = [
            f"ISBN: {book.get('isbn', '')}",
            f"Año: {book.get('publication_year', '')}",
            f"Precio: ${book.get('price', 0):.2f}",
            f"Stock: {book.get('stock', 0)}",
            f"Categoría: {cat}",
            f"Formato: {fmt}",
            "\nDescripción:\n" + book.get('description', ''),
        ]
        
        if book.get('authors'):
            details.append("\nAutores:\n- " + "\n- ".join([a.get('name', '') for a in book['authors']]))
            
        if book.get('genres'):
            details.append("\nGéneros:\n- " + "\n- ".join([g.get('name', '') for g in book['genres']]))
            
        self.info_text.insert(tk.END, "\n".join(details))
        self.info_text.config(state=tk.DISABLED)
        
    def _edit(self):
        self.open_book_form(self.book_id)
        self.destroy()
        
    def _delete(self):
        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este libro?"):
            threading.Thread(target=self._delete_thread, daemon=True).start()
            
    def _delete_thread(self):
        try:
            self.api_client.delete_book(self.book_id)
            self.after(0, self._handle_delete_success)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error al eliminar: {e}"))
            
    def _handle_delete_success(self):
        messagebox.showinfo("Éxito", "Libro eliminado correctamente")
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
