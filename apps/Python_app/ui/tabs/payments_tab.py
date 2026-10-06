"""
ui/tabs/payments_tab.py
Pestaña de Pasarela de Pagos Simulada (Microservicio Pagos :5005).
Integra Idempotencia en Redis y actualización atómica del estado del pedido a 'confirmed'.
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

        ttk.Label(left_box, text="ID del Pedido:").pack(anchor=tk.W, pady=(0, 2))
        self.entry_order_id = ttk.Entry(left_box)
        self.entry_order_id.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(left_box, text="Monto a Pagar ($):").pack(anchor=tk.W, pady=(0, 2))
        self.entry_amount = ttk.Entry(left_box)
        self.entry_amount.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(left_box, text="Método de Pago:").pack(anchor=tk.W, pady=(0, 2))
        self.combo_method = ttk.Combobox(left_box, values=["tarjeta_credito", "tarjeta_debito", "transferencia", "paypal_simulado"], state="readonly")
        self.combo_method.set("tarjeta_credito")
        self.combo_method.pack(fill=tk.X, pady=(0, 15))

        self.btn_pay = ttk.Button(left_box, text="💰 Procesar Pago Idempotente", command=self._process_payment)
        self.btn_pay.pack(fill=tk.X, pady=(0, 15))

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
            messagebox.showerror("Error", "ID debe ser entero y Monto numérico.")
            return

        self.btn_pay.config(state=tk.DISABLED)
        threading.Thread(target=self._run_payment, args=(ord_int, amt_float, method), daemon=True).start()

    def _run_payment(self, ord_int, amt_float, method):
        res = payments_service.process_payment(ord_int, amt_float, method)
        self.after(0, lambda: self._handle_payment_result(res))

    def _handle_payment_result(self, res):
        self.btn_pay.config(state=tk.NORMAL)

        if not res["success"]:
            messagebox.showerror("Error en el Pago", res.get("error") or "Fallo al procesar el pago.")
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

        msg = "¡Pago procesado exitosamente! El pedido ahora está CONFIRMADO."
        if is_replay:
            msg += "\n(Aviso de Idempotencia: Este pedido ya había sido pagado; se devolvió el comprobante existente sin doble cobro)."
        messagebox.showinfo("Pago Confirmado", msg)

        # Actualizar búsqueda
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
