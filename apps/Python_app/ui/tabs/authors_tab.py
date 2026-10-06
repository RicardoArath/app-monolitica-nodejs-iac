"""
ui/tabs/authors_tab.py
Pestaña de Gestión de Autores y Asignación de Libros (Microservicio Authors :5003).
Integra invalidación de caché cruzada con books:* en Redis.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.authors_service import authors_service
from network.books_service import books_service


class AuthorsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.authors = []
        self.selected_author = None
        self._build_ui()
        self.load_authors()

    def _build_ui(self):
        # Panel dividido: Izquierda (Autores), Derecha (Libros del autor)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------------
        # Panel Izquierdo: Lista de Autores
        # -------------------------------------------------------------
        left_frame = ttk.LabelFrame(paned, text="✍️ Autores Registrados", padding=10)
        paned.add(left_frame, weight=1)

        btn_bar = ttk.Frame(left_frame)
        btn_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(btn_bar, text="🔄", width=3, command=self.load_authors).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="➕ Nuevo", command=self._show_create_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="✏️ Editar", command=self._show_edit_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="🗑️ Eliminar", command=self._delete_author).pack(side=tk.LEFT, padx=2)

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree_authors = ttk.Treeview(tree_frame, columns=("id", "name", "count"), show="headings", selectmode="browse")
        self.tree_authors.heading("id", text="ID")
        self.tree_authors.heading("name", text="Nombre del Autor")
        self.tree_authors.heading("count", text="Libros")

        self.tree_authors.column("id", width=45, anchor=tk.CENTER)
        self.tree_authors.column("name", width=180)
        self.tree_authors.column("count", width=60, anchor=tk.CENTER)

        sb_auth = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_authors.yview)
        self.tree_authors.configure(yscrollcommand=sb_auth.set)

        self.tree_authors.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_auth.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_authors.bind("<<TreeviewSelect>>", self._on_author_selected)

        # -------------------------------------------------------------
        # Panel Derecho: Libros asociados al Autor seleccionado
        # -------------------------------------------------------------
        right_frame = ttk.LabelFrame(paned, text="📖 Libros Asociados al Autor", padding=10)
        paned.add(right_frame, weight=2)

        link_bar = ttk.Frame(right_frame)
        link_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(link_bar, text="ID Libro:").pack(side=tk.LEFT, padx=(0, 4))
        self.entry_book_id = ttk.Entry(link_bar, width=8)
        self.entry_book_id.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(link_bar, text="🔗 Vincular Libro", command=self._link_book).pack(side=tk.LEFT, padx=2)
        ttk.Button(link_bar, text="❌ Desvincular Libro", command=self._unlink_book).pack(side=tk.LEFT, padx=2)

        self.lbl_selected_author_name = ttk.Label(link_bar, text="Seleccione un autor", font=("Segoe UI", 9, "italic"), foreground="#64748b")
        self.lbl_selected_author_name.pack(side=tk.RIGHT)

        tree_b_frame = ttk.Frame(right_frame)
        tree_b_frame.pack(fill=tk.BOTH, expand=True)

        self.tree_books = ttk.Treeview(tree_b_frame, columns=("id", "isbn", "title", "price", "stock"), show="headings", selectmode="browse")
        self.tree_books.heading("id", text="ID")
        self.tree_books.heading("isbn", text="ISBN")
        self.tree_books.heading("title", text="Título")
        self.tree_books.heading("price", text="Precio")
        self.tree_books.heading("stock", text="Stock")

        self.tree_books.column("id", width=45, anchor=tk.CENTER)
        self.tree_books.column("isbn", width=120)
        self.tree_books.column("title", width=220)
        self.tree_books.column("price", width=70, anchor=tk.E)
        self.tree_books.column("stock", width=60, anchor=tk.CENTER)

        sb_b = ttk.Scrollbar(tree_b_frame, orient=tk.VERTICAL, command=self.tree_books.yview)
        self.tree_books.configure(yscrollcommand=sb_b.set)

        self.tree_books.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_b.pack(side=tk.RIGHT, fill=tk.Y)

    def load_authors(self):
        threading.Thread(target=self._fetch_authors, daemon=True).start()

    def _fetch_authors(self):
        res = authors_service.list_authors()
        self.after(0, lambda: self._render_authors(res))

    def _render_authors(self, res):
        for item in self.tree_authors.get_children():
            self.tree_authors.delete(item)

        if not res["success"]:
            return

        data = res.get("data") or {}
        self.authors = data.get("authors", [])
        for a in self.authors:
            self.tree_authors.insert("", tk.END, values=(
                a.get("id"),
                a.get("name"),
                a.get("books_count", 0)
            ))

    def _on_author_selected(self, event):
        sel = self.tree_authors.selection()
        if not sel:
            return
        item = self.tree_authors.item(sel[0])
        author_id = item["values"][0]
        self.selected_author = author_id
        author_name = item["values"][1]
        self.lbl_selected_author_name.config(text=f"Autor: {author_name} (ID {author_id})")

        threading.Thread(target=self._fetch_author_detail, args=(author_id,), daemon=True).start()

    def _fetch_author_detail(self, author_id):
        res = authors_service.get_author(author_id)
        self.after(0, lambda: self._render_author_books(res))

    def _render_author_books(self, res):
        for item in self.tree_books.get_children():
            self.tree_books.delete(item)

        if not res["success"]:
            return

        data = res.get("data") or {}
        author = data.get("author") or {}
        books = author.get("books", [])
        for b in books:
            self.tree_books.insert("", tk.END, values=(
                b.get("id"),
                b.get("isbn"),
                b.get("title"),
                f"${b.get('price', 0):.2f}",
                b.get("stock", 0)
            ))

    def _show_create_dialog(self):
        win = tk.Toplevel(self)
        win.title("Nuevo Autor")
        win.geometry("320x150")
        win.resizable(False, False)

        ttk.Label(win, text="Nombre del Autor:").pack(anchor=tk.W, padx=20, pady=(15, 2))
        entry = ttk.Entry(win)
        entry.pack(fill=tk.X, padx=20)
        entry.focus()

        def save():
            name = entry.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre es obligatorio.")
                return
            res = authors_service.create_author(name)
            if res["success"]:
                messagebox.showinfo("Éxito", "Autor creado exitosamente.")
                win.destroy()
                self.load_authors()
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo crear el autor.")

        ttk.Button(win, text="Guardar", command=save).pack(pady=15)

    def _show_edit_dialog(self):
        if not self.selected_author:
            messagebox.showwarning("Atención", "Seleccione un autor.")
            return

        win = tk.Toplevel(self)
        win.title("Editar Autor")
        win.geometry("320x150")
        win.resizable(False, False)

        ttk.Label(win, text="Nuevo Nombre:").pack(anchor=tk.W, padx=20, pady=(15, 2))
        entry = ttk.Entry(win)
        entry.pack(fill=tk.X, padx=20)

        def save():
            name = entry.get().strip()
            if not name:
                return
            res = authors_service.update_author(self.selected_author, name)
            if res["success"]:
                messagebox.showinfo("Éxito", "Autor actualizado.")
                win.destroy()
                self.load_authors()
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo actualizar.")

        ttk.Button(win, text="Guardar", command=save).pack(pady=15)

    def _delete_author(self):
        if not self.selected_author:
            messagebox.showwarning("Atención", "Seleccione un autor.")
            return

        confirm = messagebox.askyesno("Confirmar", f"¿Eliminar autor ID {self.selected_author}?")
        if confirm:
            res = authors_service.delete_author(self.selected_author)
            if res["success"]:
                messagebox.showinfo("Éxito", "Autor eliminado.")
                self.selected_author = None
                self.load_authors()
                for item in self.tree_books.get_children():
                    self.tree_books.delete(item)
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo eliminar.")

    def _link_book(self):
        if not self.selected_author:
            messagebox.showwarning("Atención", "Seleccione un autor primero.")
            return
        b_id = self.entry_book_id.get().strip()
        if not b_id:
            messagebox.showwarning("Atención", "Ingrese el ID del libro a vincular.")
            return

        res = authors_service.link_book(self.selected_author, b_id)
        if res["success"]:
            messagebox.showinfo("Éxito", "Libro vinculado al autor (caché invalidada).")
            self.entry_book_id.delete(0, tk.END)
            self._fetch_author_detail(self.selected_author)
            self.load_authors()
        else:
            messagebox.showerror("Error", res.get("error") or "No se pudo vincular el libro.")

    def _unlink_book(self):
        if not self.selected_author:
            return
        sel = self.tree_books.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un libro de la lista para desvincular.")
            return
        item = self.tree_books.item(sel[0])
        book_id = item["values"][0]

        res = authors_service.unlink_book(self.selected_author, book_id)
        if res["success"]:
            messagebox.showinfo("Éxito", "Libro desvinculado (caché invalidada).")
            self._fetch_author_detail(self.selected_author)
            self.load_authors()
        else:
            messagebox.showerror("Error", res.get("error") or "No se pudo desvincular el libro.")
