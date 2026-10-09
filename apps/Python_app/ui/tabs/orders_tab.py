"""
ui/tabs/orders_tab.py
Pestaña de Gestión de Pedidos y Stock (Microservicio Pedidos :5003).
Permite crear pedidos a partir de libros, ver items y cancelar pedidos con restitución atómica de stock.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.orders_service import orders_service
from network.books_service import books_service


class OrdersTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.orders = []
        self.selected_order_id = None
        self._build_ui()
        self.load_orders()

    def _build_ui(self):
        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------------
        # Panel Superior: Lista de Pedidos
        # -------------------------------------------------------------
        top_frame = ttk.LabelFrame(paned, text="📦 Historial de Pedidos", padding=10)
        paned.add(top_frame, weight=3)

        btn_bar = ttk.Frame(top_frame)
        btn_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(btn_bar, text="🔄 Recargar", command=self.load_orders).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="➕ Crear Nuevo Pedido", command=self._show_create_order_dialog).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_bar, text="❌ Cancelar Pedido (Restituir Stock)", command=self._cancel_order).pack(side=tk.LEFT, padx=3)

        self.lbl_orders_count = ttk.Label(btn_bar, text="", foreground="#64748b")
        self.lbl_orders_count.pack(side=tk.RIGHT)

        tree_frame = ttk.Frame(top_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "user", "status", "total", "date")
        self.tree_orders = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        self.tree_orders.heading("id", text="ID Pedido")
        self.tree_orders.heading("user", text="Usuario / ID")
        self.tree_orders.heading("status", text="Estado")
        self.tree_orders.heading("total", text="Total")
        self.tree_orders.heading("date", text="Fecha de Creación")

        self.tree_orders.column("id", width=70, anchor=tk.CENTER)
        self.tree_orders.column("user", width=120)
        self.tree_orders.column("status", width=100, anchor=tk.CENTER)
        self.tree_orders.column("total", width=90, anchor=tk.E)
        self.tree_orders.column("date", width=170)

        sb_o = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_orders.yview)
        self.tree_orders.configure(yscrollcommand=sb_o.set)

        self.tree_orders.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_o.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_orders.bind("<<TreeviewSelect>>", self._on_order_selected)

        # -------------------------------------------------------------
        # Panel Inferior: Líneas del Pedido Seleccionado (order_items)
        # -------------------------------------------------------------
        bottom_frame = ttk.LabelFrame(paned, text="📑 Detalles y Líneas del Pedido (Items)", padding=10)
        paned.add(bottom_frame, weight=2)

        tree_i_frame = ttk.Frame(bottom_frame)
        tree_i_frame.pack(fill=tk.BOTH, expand=True)

        i_cols = ("id", "book_id", "title", "unit_price", "qty", "total")
        self.tree_items = ttk.Treeview(tree_i_frame, columns=i_cols, show="headings")

        self.tree_items.heading("id", text="ID Línea")
        self.tree_items.heading("book_id", text="ID Libro")
        self.tree_items.heading("title", text="Título del Libro")
        self.tree_items.heading("unit_price", text="Precio Unitario")
        self.tree_items.heading("qty", text="Cantidad")
        self.tree_items.heading("total", text="Subtotal Línea")

        self.tree_items.column("id", width=60, anchor=tk.CENTER)
        self.tree_items.column("book_id", width=60, anchor=tk.CENTER)
        self.tree_items.column("title", width=260)
        self.tree_items.column("unit_price", width=90, anchor=tk.E)
        self.tree_items.column("qty", width=70, anchor=tk.CENTER)
        self.tree_items.column("total", width=90, anchor=tk.E)

        sb_i = ttk.Scrollbar(tree_i_frame, orient=tk.VERTICAL, command=self.tree_items.yview)
        self.tree_items.configure(yscrollcommand=sb_i.set)

        self.tree_items.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_i.pack(side=tk.RIGHT, fill=tk.Y)

    def load_orders(self):
        threading.Thread(target=self._fetch_orders, daemon=True).start()

    def _fetch_orders(self):
        res = orders_service.list_orders()
        self.after(0, lambda: self._render_orders(res))

    def _render_orders(self, res):
        for item in self.tree_orders.get_children():
            self.tree_orders.delete(item)

        if not res["success"]:
            return

        data = res.get("data") or {}
        self.orders = data.get("orders", [])
        for o in self.orders:
            st = o.get("status", "").upper()
            self.tree_orders.insert("", tk.END, values=(
                o.get("id"),
                o.get("username") or f"User #{o.get('user_id')}",
                st,
                f"${float(o.get('total', 0)):.2f}",
                str(o.get("created_at"))[:19]
            ))

        self.lbl_orders_count.config(text=f"Total: {len(self.orders)} pedidos")

    def _on_order_selected(self, event):
        sel = self.tree_orders.selection()
        if not sel:
            return
        item = self.tree_orders.item(sel[0])
        order_id = item["values"][0]
        self.selected_order_id = order_id
        threading.Thread(target=self._fetch_order_items, args=(order_id,), daemon=True).start()

    def _fetch_order_items(self, order_id):
        res = orders_service.get_order(order_id)
        self.after(0, lambda: self._render_order_items(res))

    def _render_order_items(self, res):
        for item in self.tree_items.get_children():
            self.tree_items.delete(item)

        if not res["success"]:
            return

        data = res.get("data") or {}
        order = data.get("order") or {}
        items = order.get("items", [])
        for i in items:
            self.tree_items.insert("", tk.END, values=(
                i.get("id"),
                i.get("book_id"),
                i.get("title_snapshot"),
                f"${float(i.get('unit_price', 0)):.2f}",
                i.get("quantity"),
                f"${float(i.get('line_total', 0)):.2f}"
            ))

    def _cancel_order(self):
        if not self.selected_order_id:
            messagebox.showwarning("Atención", "Seleccione un pedido para cancelar.")
            return

        confirm = messagebox.askyesno(
            "Confirmar Cancelación",
            f"¿Desea cancelar el pedido #{self.selected_order_id}?\n"
            "El stock de los libros reservados se restaurará automáticamente y se invalidará la caché."
        )
        if confirm:
            res = orders_service.cancel_order(self.selected_order_id)
            if res["success"]:
                messagebox.showinfo("Éxito", "Pedido cancelado y stock restituido exitosamente.")
                self.load_orders()
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo cancelar el pedido.")

    def _show_create_order_dialog(self):
        win = tk.Toplevel(self)
        win.title("Crear Nuevo Pedido")
        win.geometry("520x440")
        win.minsize(480, 400)

        # Panel para agregar items
        add_frame = ttk.LabelFrame(win, text="Agregar Libro al Pedido", padding=10)
        add_frame.pack(fill=tk.X, padx=15, pady=10)

        ttk.Label(add_frame, text="ID Libro:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        e_book_id = ttk.Entry(add_frame, width=8)
        e_book_id.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(add_frame, text="Cantidad:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        e_qty = ttk.Spinbox(add_frame, from_=1, to=20, width=5)
        e_qty.set(1)
        e_qty.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        cart_items = []

        def add_item():
            b_id = e_book_id.get().strip()
            qty = e_qty.get().strip()
            if not b_id or not qty:
                return
            try:
                b_int = int(b_id)
                q_int = int(qty)
            except ValueError:
                messagebox.showerror("Error", "ID y Cantidad deben ser enteros.")
                return

            cart_items.append({"book_id": b_int, "quantity": q_int})
            tree_cart.insert("", tk.END, values=(b_int, q_int))
            e_book_id.delete(0, tk.END)

        ttk.Button(add_frame, text="➕ Agregar", command=add_item).grid(row=0, column=4, padx=8, pady=5)

        # Lista de items a pedir
        tree_cart = ttk.Treeview(win, columns=("book_id", "qty"), show="headings", height=6)
        tree_cart.heading("book_id", text="ID Libro")
        tree_cart.heading("qty", text="Cantidad Solicitada")
        tree_cart.column("book_id", width=120, anchor=tk.CENTER)
        tree_cart.column("qty", width=120, anchor=tk.CENTER)
        tree_cart.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        def submit():
            if not cart_items:
                messagebox.showwarning("Atención", "Agregue al menos un libro al pedido.")
                return

            res = orders_service.create_order(cart_items)
            if res["success"]:
                data = res.get("data") or {}
                ord_info = data.get("order") or {}
                messagebox.showinfo(
                    "Pedido Creado",
                    f"¡Pedido #{ord_info.get('id')} creado exitosamente!\n"
                    f"Total: ${ord_info.get('total', 0):.2f}\n"
                    "El stock se ha reservado atómicamente y la caché de libros fue invalidada."
                )
                win.destroy()
                self.load_orders()
            else:
                messagebox.showerror("Error", res.get("error") or "Fallo al crear el pedido.")

        ttk.Button(win, text="🛒 Confirmar y Crear Pedido", command=submit).pack(pady=12)
