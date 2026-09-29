"""
ui/tabs/admin_books_tab.py
Pestaña de Administración de Libros (CRUD y demostración de PUT vs PATCH).
Implementa:
- POST /books: Creación de libros
- PUT /books/{isbn}: Actualización completa de todos los atributos
- PATCH /books/{isbn}: Actualización parcial modificando únicamente atributos seleccionados
- DELETE /books/{isbn}: Eliminación con confirmación previa
- Visor de bitácora HTTP en tiempo real con métodos, endpoints y códigos de respuesta
"""
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.books_service import books_service


class AdminBooksTab(ttk.Frame):
    def __init__(self, parent, on_catalog_changed=None):
        super().__init__(parent, padding=12)
        self.on_catalog_changed = on_catalog_changed

        self.formats_list = []
        self.categories_list = []
        self.authors_list = []
        self.genres_list = []

        self._build_ui()
        self.refresh_table()
        self._load_catalogs()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Barra Superior de Acciones CRUD
        # ---------------------------------------------------------
        top_bar = ttk.LabelFrame(self, text="🛠️ Operaciones CRUD sobre Microservicio de Libros", padding=10)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        btn_box = ttk.Frame(top_bar)
        btn_box.pack(fill=tk.X)

        self.btn_create = ttk.Button(btn_box, text="➕ Nuevo Libro (POST)", command=self._open_create_dialog)
        self.btn_create.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_put = ttk.Button(btn_box, text="✏️ Modificación Completa (PUT)", command=self._open_put_dialog)
        self.btn_put.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_patch = ttk.Button(btn_box, text="⚡ Modificación Parcial (PATCH)", command=self._open_patch_dialog)
        self.btn_patch.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_delete = ttk.Button(btn_box, text="🗑️ Eliminar Libro (DELETE)", command=self._handle_delete)
        self.btn_delete.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_refresh = ttk.Button(btn_box, text="🔄 Recargar Lista", command=self.refresh_table)
        self.btn_refresh.pack(side=tk.RIGHT)

        # ---------------------------------------------------------
        # Tabla de Libros
        # ---------------------------------------------------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("isbn", "title", "authors", "year", "price", "stock", "format", "category")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("isbn", text="ISBN")
        self.tree.heading("title", text="Título")
        self.tree.heading("authors", text="Autor(es)")
        self.tree.heading("year", text="Año")
        self.tree.heading("price", text="Precio")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("format", text="Formato")
        self.tree.heading("category", text="Categoría")

        self.tree.column("isbn", width=120, anchor=tk.W)
        self.tree.column("title", width=240, anchor=tk.W)
        self.tree.column("authors", width=160, anchor=tk.W)
        self.tree.column("year", width=60, anchor=tk.CENTER)
        self.tree.column("price", width=80, anchor=tk.E)
        self.tree.column("stock", width=60, anchor=tk.CENTER)
        self.tree.column("format", width=120, anchor=tk.W)
        self.tree.column("category", width=110, anchor=tk.W)

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ---------------------------------------------------------
        # Visor de Peticiones y Respuestas HTTP (Auditoría Técnica)
        # ---------------------------------------------------------
        log_frame = ttk.LabelFrame(self, text="📡 Bitácora de Peticiones HTTP en Vivo (Demostración de Integración)", padding=8)
        log_frame.pack(fill=tk.X)

        self.txt_log = tk.Text(log_frame, height=5, wrap="none", font=("Consolas", 8), bg="#0f172a", fg="#38bdf8", relief="flat")
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=log_scroll.set)

        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_http("INFO", "Sistema", "Pestaña de administración de libros inicializada. Listo para llamadas REST.")

    def log_http(self, method, endpoint, message, status_code=None):
        """Registra un evento HTTP en el visor de bitácora."""
        code_str = f" [{status_code}]" if status_code is not None else ""
        entry = f"[{method}]{code_str} {endpoint} -> {message}\n"
        self.txt_log.insert(tk.END, entry)
        self.txt_log.see(tk.END)

    def _load_catalogs(self):
        """Carga en segundo plano los catálogos auxiliares (formatos, categorías, autores, géneros)."""
        def thread_task():
            res_f = books_service.get_catalog("formats")
            res_c = books_service.get_catalog("categories")
            res_a = books_service.get_catalog("authors")
            res_g = books_service.get_catalog("genres")

            if res_f["success"]:
                self.formats_list = res_f["data"].get("items", [])
            if res_c["success"]:
                self.categories_list = res_c["data"].get("items", [])
            if res_a["success"]:
                self.authors_list = res_a["data"].get("items", [])
            if res_g["success"]:
                self.genres_list = res_g["data"].get("items", [])

        threading.Thread(target=thread_task, daemon=True).start()

    def refresh_table(self):
        """Recarga la lista de libros desde el microservicio."""
        def thread_task():
            res = books_service.get_books(page=1)
            self.after(0, lambda: self._on_table_refreshed(res))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_table_refreshed(self, res):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if res["success"]:
            books = res["data"].get("books", [])
            for b in books:
                self.tree.insert("", tk.END, values=(
                    b.get("isbn", ""),
                    b.get("title", ""),
                    b.get("authors", "") or "Sin autor",
                    b.get("publication_year", "") or "N/A",
                    f"${b.get('price', 0):,.2f}",
                    b.get("stock", 0),
                    b.get("format_name", ""),
                    b.get("category_name", "")
                ))
            self.log_http("GET", "/books", f"Catálogo recargado: {len(books)} libros mostrados.", res["status_code"])
        else:
            self.log_http("GET", "/books", f"Fallo al recargar: {res['error']}", res["status_code"])

    def _get_selected_isbn(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Selección Requerida", "Seleccione un libro de la lista antes de continuar.")
            return None
        return self.tree.item(selected[0])["values"][0]

    # -------------------------------------------------------------
    # ➕ POST /books (Crear Libro)
    # -------------------------------------------------------------
    def _open_create_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Registrar Nuevo Libro — POST /books")
        dlg.geometry("500x560")
        dlg.resizable(False, False)

        frame = ttk.Frame(dlg, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="POST /books — Registro en PostgreSQL", font=("Segoe UI", 11, "bold"), foreground="#0f766e").pack(anchor=tk.W, pady=(0, 10))

        # Campos
        ttk.Label(frame, text="ISBN (Único): *").pack(anchor=tk.W)
        txt_isbn = ttk.Entry(frame)
        txt_isbn.pack(fill=tk.X, pady=(2, 6))

        ttk.Label(frame, text="Título del Libro: *").pack(anchor=tk.W)
        txt_title = ttk.Entry(frame)
        txt_title.pack(fill=tk.X, pady=(2, 6))

        row_num = ttk.Frame(frame)
        row_num.pack(fill=tk.X, pady=(0, 6))

        c1 = ttk.Frame(row_num)
        c1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Label(c1, text="Precio ($):").pack(anchor=tk.W)
        txt_price = ttk.Entry(c1)
        txt_price.pack(fill=tk.X)
        txt_price.insert(0, "299.00")

        c2 = ttk.Frame(row_num)
        c2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Label(c2, text="Stock:").pack(anchor=tk.W)
        txt_stock = ttk.Entry(c2)
        txt_stock.pack(fill=tk.X)
        txt_stock.insert(0, "10")

        c3 = ttk.Frame(row_num)
        c3.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        ttk.Label(c3, text="Año:").pack(anchor=tk.W)
        txt_year = ttk.Entry(c3)
        txt_year.pack(fill=tk.X)
        txt_year.insert(0, "2026")

        # Formato y Categoría
        ttk.Label(frame, text="Formato: *").pack(anchor=tk.W)
        cb_format = ttk.Combobox(frame, state="readonly")
        format_names = [f"{f['id']} - {f['name']}" for f in self.formats_list]
        cb_format["values"] = format_names
        if format_names:
            cb_format.current(0)
        cb_format.pack(fill=tk.X, pady=(2, 6))

        ttk.Label(frame, text="Categoría: *").pack(anchor=tk.W)
        cb_cat = ttk.Combobox(frame, state="readonly")
        cat_names = [f"{c['id']} - {c['name']}" for c in self.categories_list]
        cb_cat["values"] = cat_names
        if cat_names:
            cb_cat.current(0)
        cb_cat.pack(fill=tk.X, pady=(2, 6))

        ttk.Label(frame, text="Descripción / Sinopsis:").pack(anchor=tk.W)
        txt_desc = tk.Text(frame, height=3, font=("Segoe UI", 9))
        txt_desc.pack(fill=tk.X, pady=(2, 10))

        def submit():
            isbn = txt_isbn.get().strip()
            title = txt_title.get().strip()
            if not isbn or not title:
                messagebox.showerror("Campos Requeridos", "El ISBN y el título son obligatorios.")
                return

            try:
                price = float(txt_price.get())
                stock = int(txt_stock.get())
                year = int(txt_year.get())
                f_id = int(cb_format.get().split(" - ")[0])
                c_id = int(cb_cat.get().split(" - ")[0])
            except Exception:
                messagebox.showerror("Datos inválidos", "Verifique que precio, stock y año sean numéricos.")
                return

            payload = {
                "isbn": isbn,
                "title": title,
                "price": price,
                "stock": stock,
                "publication_year": year,
                "format_id": f_id,
                "category_id": c_id,
                "description": txt_desc.get("1.0", tk.END).strip()
            }

            def thread_task():
                res = books_service.create_book(payload)
                self.after(0, lambda: on_created(res))

            def on_created(res):
                if res["success"]:
                    self.log_http("POST", "/books", f"Libro creado exitosamente: {title}", res["status_code"])
                    messagebox.showinfo("Éxito (201 Created)", f"Libro '{title}' creado correctamente mediante POST /books.")
                    dlg.destroy()
                    self.refresh_table()
                    if self.on_catalog_changed:
                        self.on_catalog_changed()
                else:
                    code = res["status_code"]
                    msg = res["error"] or "Error al crear libro."
                    if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                        msg = res["data"]["message"]

                    self.log_http("POST", "/books", f"Fallo al crear: {msg}", code)
                    if code == 409:
                        messagebox.showerror("Conflicto (409)", f"El ISBN '{isbn}' ya existe registrado en la base de datos.")
                    elif code == 401:
                        messagebox.showerror("No Autorizado (401)", "Acceso denegado: Se requiere un token JWT válido para registrar libros.\n\nInicie sesión en la pestaña Perfil.")
                    else:
                        messagebox.showerror(f"Error ({code})", msg)

            threading.Thread(target=thread_task, daemon=True).start()

        ttk.Button(frame, text="💾 Enviar Petición POST /books", command=submit).pack(fill=tk.X, ipady=4, pady=(5, 0))

    # -------------------------------------------------------------
    # ✏️ PUT /books/{isbn} (Modificación COMPLETA)
    # -------------------------------------------------------------
    def _open_put_dialog(self):
        isbn = self._get_selected_isbn()
        if not isbn:
            return

        # Primero obtener el detalle actual
        res = books_service.get_book_by_isbn(isbn)
        if not res["success"]:
            messagebox.showerror("Error", f"No se pudo consultar el libro con ISBN {isbn}.")
            return

        book = res["data"].get("book", {})

        dlg = tk.Toplevel(self)
        dlg.title(f"Modificación Completa (PUT) — ISBN: {isbn}")
        dlg.geometry("520x580")
        dlg.resizable(False, False)

        frame = ttk.Frame(dlg, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Explicación didáctica sobre PUT
        expl = tk.Label(
            frame,
            text="ℹ️ MÉTODO PUT: Reemplazo completo de todos los atributos del libro.\nSe envían todos los campos al servidor para sobreescritura íntegra.",
            font=("Segoe UI", 8, "italic"),
            bg="#fef3c7",
            fg="#92400e",
            padx=8,
            pady=6,
            justify=tk.LEFT
        )
        expl.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text=f"ISBN: {isbn}", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        ttk.Label(frame, text="Título: *").pack(anchor=tk.W, pady=(6, 2))
        txt_title = ttk.Entry(frame)
        txt_title.pack(fill=tk.X)
        txt_title.insert(0, book.get("title", ""))

        row_num = ttk.Frame(frame)
        row_num.pack(fill=tk.X, pady=(6, 6))

        c1 = ttk.Frame(row_num)
        c1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Label(c1, text="Precio ($):").pack(anchor=tk.W)
        txt_price = ttk.Entry(c1)
        txt_price.pack(fill=tk.X)
        txt_price.insert(0, str(book.get("price", "")))

        c2 = ttk.Frame(row_num)
        c2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))
        ttk.Label(c2, text="Stock:").pack(anchor=tk.W)
        txt_stock = ttk.Entry(c2)
        txt_stock.pack(fill=tk.X)
        txt_stock.insert(0, str(book.get("stock", "")))

        c3 = ttk.Frame(row_num)
        c3.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        ttk.Label(c3, text="Año:").pack(anchor=tk.W)
        txt_year = ttk.Entry(c3)
        txt_year.pack(fill=tk.X)
        txt_year.insert(0, str(book.get("publication_year", "") or ""))

        # Formato y Categoría
        ttk.Label(frame, text="Formato: *").pack(anchor=tk.W, pady=(4, 2))
        cb_format = ttk.Combobox(frame, state="readonly")
        format_names = [f"{f['id']} - {f['name']}" for f in self.formats_list]
        cb_format["values"] = format_names
        # Buscar índice actual
        cur_fmt = book.get("format_id")
        for i, val in enumerate(format_names):
            if val.startswith(f"{cur_fmt} -"):
                cb_format.current(i)
                break
        cb_format.pack(fill=tk.X)

        ttk.Label(frame, text="Categoría: *").pack(anchor=tk.W, pady=(4, 2))
        cb_cat = ttk.Combobox(frame, state="readonly")
        cat_names = [f"{c['id']} - {c['name']}" for c in self.categories_list]
        cb_cat["values"] = cat_names
        cur_cat = book.get("category_id")
        for i, val in enumerate(cat_names):
            if val.startswith(f"{cur_cat} -"):
                cb_cat.current(i)
                break
        cb_cat.pack(fill=tk.X)

        ttk.Label(frame, text="Descripción:").pack(anchor=tk.W, pady=(4, 2))
        txt_desc = tk.Text(frame, height=3, font=("Segoe UI", 9))
        txt_desc.pack(fill=tk.X)
        txt_desc.insert(tk.END, book.get("description", "") or "")

        def submit_put():
            title = txt_title.get().strip()
            if not title:
                messagebox.showerror("Requerido", "El título es obligatorio.")
                return

            try:
                price = float(txt_price.get())
                stock = int(txt_stock.get())
                year = int(txt_year.get())
                f_id = int(cb_format.get().split(" - ")[0])
                c_id = int(cb_cat.get().split(" - ")[0])
            except Exception:
                messagebox.showerror("Error", "Revise los campos numéricos y selectores.")
                return

            payload = {
                "title": title,
                "price": price,
                "stock": stock,
                "publication_year": year,
                "format_id": f_id,
                "category_id": c_id,
                "description": txt_desc.get("1.0", tk.END).strip()
            }

            def thread_task():
                res_put = books_service.put_book(isbn, payload)
                self.after(0, lambda: on_put_done(res_put))

            def on_put_done(res_put):
                if res_put["success"]:
                    self.log_http("PUT", f"/books/{isbn}", f"Actualización completa exitosa.", res_put["status_code"])
                    messagebox.showinfo("Éxito (200 OK)", f"Libro con ISBN {isbn} actualizado completamente mediante PUT.")
                    dlg.destroy()
                    self.refresh_table()
                    if self.on_catalog_changed:
                        self.on_catalog_changed()
                else:
                    self.log_http("PUT", f"/books/{isbn}", f"Error PUT: {res_put['error']}", res_put["status_code"])
                    code = res_put["status_code"]
                    if code == 401:
                        messagebox.showerror("No Autorizado (401)", "Acceso denegado: Se requiere un token JWT válido para modificar libros.\n\nInicie sesión en la pestaña Perfil.")
                    else:
                        messagebox.showerror(f"Error ({code})", res_put['error'] or "Fallo en PUT.")

            threading.Thread(target=thread_task, daemon=True).start()

        ttk.Button(frame, text="🚀 Ejecutar Actualización Completa (PUT)", command=submit_put).pack(fill=tk.X, ipady=4, pady=(15, 0))

    # -------------------------------------------------------------
    # ⚡ PATCH /books/{isbn} (Modificación PARCIAL)
    # -------------------------------------------------------------
    def _open_patch_dialog(self):
        isbn = self._get_selected_isbn()
        if not isbn:
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Modificación Parcial (PATCH) — ISBN: {isbn}")
        dlg.geometry("520x460")
        dlg.resizable(False, False)

        frame = ttk.Frame(dlg, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Explicación didáctica sobre PATCH
        expl = tk.Label(
            frame,
            text="ℹ️ MÉTODO PATCH: Modificación parcial.\nPermite modificar UN SOLO campo sin alterar ni enviar los demás atributos.",
            font=("Segoe UI", 8, "italic"),
            bg="#e0f2fe",
            fg="#0369a1",
            padx=8,
            pady=6,
            justify=tk.LEFT
        )
        expl.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frame, text=f"ISBN Objetivo: {isbn}", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Selector de atributo a modificar
        ttk.Label(frame, text="Seleccione el atributo único a actualizar:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        cb_attr = ttk.Combobox(frame, state="readonly", values=["price (Precio)", "stock (Existencia en almacén)", "title (Título)"])
        cb_attr.current(0)
        cb_attr.pack(fill=tk.X, pady=(2, 10))

        ttk.Label(frame, text="Nuevo valor para el atributo:").pack(anchor=tk.W)
        txt_val = ttk.Entry(frame, font=("Segoe UI", 10))
        txt_val.pack(fill=tk.X, pady=(2, 10))

        # Vista previa del Payload JSON a enviar
        lbl_preview = ttk.Label(frame, text="Payload JSON que se transmitirá al microservicio:", font=("Segoe UI", 9, "bold"))
        lbl_preview.pack(anchor=tk.W, pady=(5, 2))

        txt_preview = tk.Text(frame, height=3, font=("Consolas", 9), bg="#f8fafc", relief="solid", bd=1)
        txt_preview.pack(fill=tk.X, pady=(0, 15))

        def update_preview(*args):
            attr_raw = cb_attr.get().split(" ")[0]
            val = txt_val.get().strip()
            if attr_raw == "price":
                try:
                    val = float(val) if val else 0.0
                except ValueError:
                    pass
            elif attr_raw == "stock":
                try:
                    val = int(val) if val else 0
                except ValueError:
                    pass
            txt_preview.delete("1.0", tk.END)
            txt_preview.insert(tk.END, json.dumps({attr_raw: val}, indent=2))

        txt_val.bind("<KeyRelease>", update_preview)
        cb_attr.bind("<<ComboboxSelected>>", update_preview)
        update_preview()

        def submit_patch():
            attr_raw = cb_attr.get().split(" ")[0]
            val_str = txt_val.get().strip()

            if not val_str:
                messagebox.showerror("Error", "Ingrese un valor.")
                return

            if attr_raw == "price":
                try:
                    val = float(val_str)
                except ValueError:
                    messagebox.showerror("Error", "El precio debe ser un número decimal.")
                    return
            elif attr_raw == "stock":
                try:
                    val = int(val_str)
                except ValueError:
                    messagebox.showerror("Error", "El stock debe ser un número entero.")
                    return
            else:
                val = val_str

            payload = {attr_raw: val}

            def thread_task():
                res_patch = books_service.patch_book(isbn, payload)
                self.after(0, lambda: on_patch_done(res_patch, attr_raw, val))

            def on_patch_done(res_patch, field, new_v):
                if res_patch["success"]:
                    self.log_http("PATCH", f"/books/{isbn}", f"Campo '{field}' modificado a {new_v}", res_patch["status_code"])
                    messagebox.showinfo(
                        "Éxito (200 OK)",
                        f"Actualización parcial (PATCH) exitosa en ISBN {isbn}.\n\n"
                        f"Se envió únicamente: {json.dumps(payload)}\n"
                        f"Respuesta del microservicio: {res_patch['data'].get('message')}"
                    )
                    dlg.destroy()
                    self.refresh_table()
                    if self.on_catalog_changed:
                        self.on_catalog_changed()
                else:
                    self.log_http("PATCH", f"/books/{isbn}", f"Fallo PATCH: {res_patch['error']}", res_patch["status_code"])
                    code = res_patch["status_code"]
                    if code == 401:
                        messagebox.showerror("No Autorizado (401)", "Acceso denegado: Se requiere un token JWT válido para modificar libros.\n\nInicie sesión en la pestaña Perfil.")
                    else:
                        messagebox.showerror(f"Error ({code})", res_patch['error'] or "Error en PATCH.")

            threading.Thread(target=thread_task, daemon=True).start()

        ttk.Button(frame, text="⚡ Enviar Actualización Parcial (PATCH)", command=submit_patch).pack(fill=tk.X, ipady=4)

    # -------------------------------------------------------------
    # 🗑️ DELETE /books/{isbn} (Eliminar Libro)
    # -------------------------------------------------------------
    def _handle_delete(self):
        isbn = self._get_selected_isbn()
        if not isbn:
            return

        confirm = messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar permanentemente el libro con ISBN '{isbn}'?\n\nEsta operación ejecutará un HTTP DELETE contra el microservicio remoto.",
            icon="warning"
        )
        if not confirm:
            return

        def thread_task():
            res = books_service.delete_book(isbn)
            self.after(0, lambda: on_deleted(res))

        def on_deleted(res):
            if res["success"]:
                self.log_http("DELETE", f"/books/{isbn}", f"Libro eliminado con éxito.", res["status_code"])
                messagebox.showinfo("Eliminado", f"El libro con ISBN '{isbn}' fue eliminado correctamente del sistema.")
                self.refresh_table()
                if self.on_catalog_changed:
                    self.on_catalog_changed()
            else:
                code = res["status_code"]
                msg = res["error"] or "Error al eliminar."
                if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                    msg = res["data"]["message"]

                self.log_http("DELETE", f"/books/{isbn}", f"Error al eliminar: {msg}", code)
                if code == 404:
                    messagebox.showerror("No Encontrado (404)", f"El libro con ISBN '{isbn}' no existe en el microservicio.")
                elif code == 401:
                    messagebox.showerror("No Autorizado (401)", "Acceso denegado: Se requiere un token JWT válido para eliminar libros.\n\nInicie sesión en la pestaña Perfil.")
                else:
                    messagebox.showerror(f"Error ({code})", msg)

        threading.Thread(target=thread_task, daemon=True).start()
