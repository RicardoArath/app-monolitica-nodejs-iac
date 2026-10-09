"""
ui/tabs/payments_tab.py
Pestaña de Pasarela de Pagos Simulada (Microservicio Pagos :5002).
Integra Idempotencia en Redis, consulta inteligente de pedidos y actualización
atómica del estado del pedido a 'confirmed'.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.payments_service import payments_service
from network.orders_service import orders_service


class PaymentsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=15)
        self._build_ui()

    def _build_ui(self):
        # -------------------------------------------------------------
        # Sección Izquierda: Procesar Pago
        # -------------------------------------------------------------
        left_box = ttk.LabelFrame(self, text="💳 Registrar Pago de Pedido", padding=15)
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # ID del Pedido con botón para consultar estado y total
        ttk.Label(left_box, text="ID del Pedido:").pack(anchor=tk.W, pady=(0, 2))
        order_row = ttk.Frame(left_box)
        order_row.pack(fill=tk.X, pady=(0, 3))
        self.entry_order_id = ttk.Entry(order_row)
        self.entry_order_id.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_load_order = ttk.Button(order_row, text="🔍 Consultar Total", command=self._fetch_order_info)
        self.btn_load_order.pack(side=tk.RIGHT)

        # Etiqueta de estado del pedido consultado
        self.lbl_order_hint = ttk.Label(
            left_box,
            text="Ingrese el ID de un pedido pendiente para autocompletar el monto.",
            font=("Segoe UI", 8),
            foreground="#64748b"
        )
        self.lbl_order_hint.pack(anchor=tk.W, pady=(0, 10))

        # Monto a pagar
        ttk.Label(left_box, text="Monto a Pagar ($):").pack(anchor=tk.W, pady=(0, 2))
        self.entry_amount = ttk.Entry(left_box)
        self.entry_amount.pack(fill=tk.X, pady=(0, 10))

        # Método de pago
        ttk.Label(left_box, text="Método de Pago:").pack(anchor=tk.W, pady=(0, 2))
        self.combo_method = ttk.Combobox(
            left_box,
            values=["tarjeta_credito", "tarjeta_debito", "transferencia", "paypal_simulado"],
            state="readonly"
        )
        self.combo_method.set("tarjeta_credito")
        self.combo_method.pack(fill=tk.X, pady=(0, 15))

        # Botones de acción: Procesar Pago y Asistentes de Pedidos
        btn_box = ttk.Frame(left_box)
        btn_box.pack(fill=tk.X, pady=(0, 15))

        self.btn_pay = ttk.Button(btn_box, text="💰 Procesar Pago Idempotente", command=self._process_payment)
        self.btn_pay.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.btn_quick_pending = ttk.Button(btn_box, text="📋 Cargar Pendiente", command=self._load_pending_order)
        self.btn_quick_pending.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_create_test = ttk.Button(btn_box, text="➕ Nuevo Pedido", command=self._create_test_order)
        self.btn_create_test.pack(side=tk.RIGHT)

        # Caja de Comprobante
        self.receipt_box = ttk.LabelFrame(left_box, text="Comprobante de Transacción", padding=10)
        self.receipt_box.pack(fill=tk.BOTH, expand=True)

        self.txt_receipt = tk.Text(self.receipt_box, height=8, font=("Consolas", 9), wrap=tk.WORD, bg="#f8fafc")
        self.txt_receipt.pack(fill=tk.BOTH, expand=True)
        self.txt_receipt.insert(tk.END, "Ingrese los datos del pedido y procese el pago para generar el comprobante.\n")
        self.txt_receipt.config(state=tk.DISABLED)

        # -------------------------------------------------------------
        # Sección Derecha: Historial / Consulta de Pagos de un Pedido
        # -------------------------------------------------------------
        right_box = ttk.LabelFrame(self, text="🔍 Consultar Pagos por Pedido", padding=15)
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        search_bar = ttk.Frame(right_box)
        search_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_bar, text="ID Pedido:").pack(side=tk.LEFT, padx=(0, 6))
        self.entry_search_order = ttk.Entry(search_bar, width=12)
        self.entry_search_order.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(search_bar, text="🔍 Buscar", command=self._search_payments).pack(side=tk.LEFT)

        tree_frame = ttk.Frame(right_box)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "amount", "method", "status", "date")
        self.tree_payments = ttk.Treeview(tree_frame, columns=cols, show="headings")

        self.tree_payments.heading("id", text="ID Pago")
        self.tree_payments.heading("amount", text="Monto")
        self.tree_payments.heading("method", text="Método")
        self.tree_payments.heading("status", text="Estado")
        self.tree_payments.heading("date", text="Fecha de Procesamiento")

        self.tree_payments.column("id", width=60, anchor=tk.CENTER)
        self.tree_payments.column("amount", width=80, anchor=tk.E)
        self.tree_payments.column("method", width=110)
        self.tree_payments.column("status", width=90, anchor=tk.CENTER)
        self.tree_payments.column("date", width=150)

        sb_p = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_payments.yview)
        self.tree_payments.configure(yscrollcommand=sb_p.set)

        self.tree_payments.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_p.pack(side=tk.RIGHT, fill=tk.Y)

    # -----------------------------------------------------------------
    # Asistente: Consultar Estado y Monto del Pedido Ingresado
    # -----------------------------------------------------------------
    def _fetch_order_info(self):
        ord_id = self.entry_order_id.get().strip()
        if not ord_id:
            messagebox.showwarning("Atención", "Ingrese el ID del pedido a consultar.")
            return

        try:
            ord_int = int(ord_id)
        except ValueError:
            messagebox.showerror("Error", "El ID del pedido debe ser un número entero.")
            return

        self.lbl_order_hint.config(text=f"Consultando pedido #{ord_int}...", foreground="#64748b")
        threading.Thread(target=self._run_fetch_order, args=(ord_int,), daemon=True).start()

    def _run_fetch_order(self, ord_int):
        res = orders_service.get_order(ord_int)
        self.after(0, lambda: self._apply_order_info(ord_int, res))

    def _apply_order_info(self, ord_int, res):
        if not res["success"]:
            err = res.get("error") or "No se pudo consultar el pedido."
            self.lbl_order_hint.config(text=f"✖ {err}", foreground="#ef4444")
            return

        data = res.get("data") or {}
        order = data.get("order") or {}
        status = (order.get("status") or "").lower()
        total = float(order.get("total") or 0.0)

        # Autocompletar el campo de monto exacto
        self.entry_amount.delete(0, tk.END)
        self.entry_amount.insert(0, f"{total:.2f}")

        if status == "pending":
            self.lbl_order_hint.config(
                text=f"✔ Pedido #{ord_int} en estado PENDING — Total a cobrar: ${total:.2f}",
                foreground="#15803d"
            )
        elif status == "confirmed":
            self.lbl_order_hint.config(
                text=f"ℹ Pedido #{ord_int} ya está CONFIRMADO (Pagado previamente por ${total:.2f}).",
                foreground="#0284c7"
            )
        elif status == "cancelled":
            self.lbl_order_hint.config(
                text=f"✖ Pedido #{ord_int} está CANCELADO y no admite pagos.",
                foreground="#ef4444"
            )
        else:
            self.lbl_order_hint.config(
                text=f"Estado del pedido: {status.upper()} | Total: ${total:.2f}",
                foreground="#334155"
            )

    # -----------------------------------------------------------------
    # Asistente: Cargar el Primer Pedido Pendiente Disponible
    # -----------------------------------------------------------------
    def _load_pending_order(self):
        self.lbl_order_hint.config(text="Buscando pedidos pendientes en el sistema...", foreground="#64748b")
        threading.Thread(target=self._run_load_pending, daemon=True).start()

    def _run_load_pending(self):
        res = orders_service.list_orders()
        self.after(0, lambda: self._apply_loaded_pending(res))

    def _apply_loaded_pending(self, res):
        if not res["success"]:
            messagebox.showerror("Error", res.get("error") or "No se pudo consultar la lista de pedidos.")
            return

        data = res.get("data") or {}
        orders = data.get("orders") or []
        pending_list = [o for o in orders if (o.get("status") or "").lower() == "pending"]

        if not pending_list:
            resp = messagebox.askyesno(
                "Sin Pedidos Pendientes",
                "No hay pedidos pendientes de pago actualmente (todos ya fueron pagados o cancelados).\n\n"
                "¿Desea crear un nuevo pedido de prueba automáticamente para pagarlo ahora?"
            )
            if resp:
                self._create_test_order()
            return

        # Seleccionar el pedido pendiente más reciente
        target = pending_list[0]
        ord_id = target.get("id")
        total = float(target.get("total") or 0.0)

        self.entry_order_id.delete(0, tk.END)
        self.entry_order_id.insert(0, str(ord_id))

        self.entry_amount.delete(0, tk.END)
        self.entry_amount.insert(0, f"{total:.2f}")

        self.lbl_order_hint.config(
            text=f"✔ Pedido #{ord_id} cargado (Estado: PENDING | Total: ${total:.2f}). ¡Listo para pagar!",
            foreground="#15803d"
        )

    # -----------------------------------------------------------------
    # Asistente: Crear un Pedido de Prueba Rápido
    # -----------------------------------------------------------------
    def _create_test_order(self):
        self.lbl_order_hint.config(text="Creando nuevo pedido de prueba en GCP...", foreground="#64748b")
        threading.Thread(target=self._run_create_order, daemon=True).start()

    def _run_create_order(self):
        # Crear un pedido con el libro ID 1 (o ID 2)
        items = [{"book_id": 1, "quantity": 1}]
        res = orders_service.create_order(items)
        self.after(0, lambda: self._apply_created_order(res))

    def _apply_created_order(self, res):
        if not res["success"]:
            messagebox.showerror("Error", res.get("error") or "No se pudo crear el pedido de prueba.")
            return

        data = res.get("data") or {}
        order = data.get("order") or {}
        ord_id = order.get("id")
        total = float(order.get("total") or 0.0)

        self.entry_order_id.delete(0, tk.END)
        self.entry_order_id.insert(0, str(ord_id))

        self.entry_amount.delete(0, tk.END)
        self.entry_amount.insert(0, f"{total:.2f}")

        self.lbl_order_hint.config(
            text=f"🎉 ¡Pedido #{ord_id} creado con éxito! Estado: PENDING | Total: ${total:.2f}",
            foreground="#15803d"
        )
        messagebox.showinfo(
            "Pedido Creado",
            f"Se creó exitosamente el pedido #{ord_id} con stock reservado.\n"
            f"El formulario ha sido autocompletado con el monto exacto (${total:.2f}).\n"
            f"Haga clic en '💰 Procesar Pago Idempotente' para finalizar el cobro."
        )

    # -----------------------------------------------------------------
    # Procesamiento del Pago
    # -----------------------------------------------------------------
    def _process_payment(self):
        ord_id = self.entry_order_id.get().strip()
        amt_str = self.entry_amount.get().strip()
        method = self.combo_method.get()

        if not ord_id:
            messagebox.showwarning("Atención", "Ingrese el ID del pedido a pagar.")
            return

        try:
            ord_int = int(ord_id)
            amt_float = float(amt_str) if amt_str else None
        except ValueError:
            messagebox.showerror("Error", "El ID debe ser un entero y el Monto debe ser numérico.")
            return

        self.btn_pay.config(state=tk.DISABLED)
        threading.Thread(target=self._run_payment, args=(ord_int, amt_float, method), daemon=True).start()

    def _run_payment(self, ord_int, amt_float, method):
        res = payments_service.process_payment(ord_int, amt_float, method)
        self.after(0, lambda: self._handle_payment_result(res))

    def _handle_payment_result(self, res):
        self.btn_pay.config(state=tk.NORMAL)

        if not res["success"]:
            err_msg = res.get("error")
            if not err_msg and isinstance(res.get("data"), dict):
                err_msg = res["data"].get("message")
            if not err_msg:
                err_msg = "Fallo al procesar el pago."
            messagebox.showerror("Error en el Pago", err_msg)
            return

        data = res.get("data") or {}
        pay_info = data.get("payment") or {}
        is_replay = data.get("idempotent_replay", False)

        receipt_text = (
            f"=== COMPROBANTE DE PAGO SIMULADO ===\n"
            f"ID Transacción: #{pay_info.get('id')}\n"
            f"ID Pedido:      #{pay_info.get('order_id')}\n"
            f"Monto Pagado:   ${float(pay_info.get('amount', 0)):.2f}\n"
            f"Método:         {pay_info.get('method')}\n"
            f"Estado:         {pay_info.get('status', 'approved').upper()}\n"
            f"Fecha / Hora:   {pay_info.get('processed_at')}\n"
            f"Idempotencia:   {'REPETICIÓN CACHEADA (REDIS)' if is_replay else 'TRANSACCIÓN NUEVA'}\n"
            f"Estado Pedido:  CONFIRMED\n"
            f"====================================\n"
        )

        self.txt_receipt.config(state=tk.NORMAL)
        self.txt_receipt.delete("1.0", tk.END)
        self.txt_receipt.insert(tk.END, receipt_text)
        self.txt_receipt.config(state=tk.DISABLED)

        if is_replay:
            msg = (
                f"Aviso de Idempotencia: El pedido #{pay_info.get('order_id')} ya había sido pagado previamente.\n"
                f"Gracias a la idempotencia de Redis, se recuperó su comprobante original sin duplicar el cobro."
            )
            messagebox.showinfo("Comprobante Recuperado (Idempotente)", msg)
        else:
            msg = (
                f"¡Pago de ${float(pay_info.get('amount', 0)):.2f} procesado exitosamente!\n"
                f"El pedido #{pay_info.get('order_id')} ahora se encuentra en estado CONFIRMED."
            )
            messagebox.showinfo("Pago Confirmado", msg)

        # Actualizar automáticamente la búsqueda y tabla derecha
        self.entry_search_order.delete(0, tk.END)
        self.entry_search_order.insert(0, str(pay_info.get('order_id')))
        self._search_payments()

    def _search_payments(self):
        ord_id = self.entry_search_order.get().strip()
        if not ord_id:
            return
        try:
            ord_int = int(ord_id)
        except ValueError:
            return

        threading.Thread(target=self._run_search, args=(ord_int,), daemon=True).start()

    def _run_search(self, ord_int):
        res = payments_service.get_order_payments(ord_int)
        self.after(0, lambda: self._render_payments(res))

    def _render_payments(self, res):
        for item in self.tree_payments.get_children():
            self.tree_payments.delete(item)

        if not res["success"]:
            return

        data = res.get("data") or {}
        payments = data.get("payments", [])
        for p in payments:
            self.tree_payments.insert("", tk.END, values=(
                p.get("id"),
                f"${float(p.get('amount', 0)):.2f}",
                p.get("method"),
                p.get("status", "").upper(),
                str(p.get("processed_at"))[:19]
            ))
