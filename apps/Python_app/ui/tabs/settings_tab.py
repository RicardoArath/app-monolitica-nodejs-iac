"""
ui/tabs/settings_tab.py
Pestaña de Configuración del Servidor y Entornos.
Permite:
- Alternar entre Entorno Local (localhost) y Entorno Remoto (GCP)
- Modificar manualmente las URLs de los 6 microservicios y host/puerto de Redis
- Probar la conectividad de los endpoints antes de guardar
- Guardar la configuración en config.json para que persista entre reinicios
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import (
    settings,
    DEFAULT_LOCAL_AUTH,
    DEFAULT_LOCAL_BOOKS,
    DEFAULT_LOCAL_USERS,
    DEFAULT_LOCAL_AUTHORS,
    DEFAULT_LOCAL_ORDERS,
    DEFAULT_LOCAL_PAYMENTS,
    DEFAULT_LOCAL_REDIS_HOST,
    DEFAULT_LOCAL_REDIS_PORT,
    DEFAULT_REMOTE_HOST
)
from network.api_client import http_client


class SettingsTab(ttk.Frame):
    def __init__(self, parent, on_settings_saved=None):
        super().__init__(parent, padding=15)
        self.on_settings_saved = on_settings_saved

        self._build_ui()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Selector Rápido de Entornos (Presets)
        # ---------------------------------------------------------
        preset_box = ttk.LabelFrame(self, text="⚡ Selección Rápida de Entorno", padding=12)
        preset_box.pack(fill=tk.X, pady=(0, 12))

        btn_row = ttk.Frame(preset_box)
        btn_row.pack(fill=tk.X)

        self.btn_preset_local = ttk.Button(
            btn_row, text="🏠 Modo Local (localhost:5000 - 5005 + Redis:6379)", command=self._apply_local_preset
        )
        self.btn_preset_local.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        self.btn_preset_remote = ttk.Button(
            btn_row, text="☁️ Modo Remoto (Nube GCP 34.171.172.238)", command=self._apply_remote_preset
        )
        self.btn_preset_remote.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---------------------------------------------------------
        # Entradas de URLs de los 6 Microservicios
        # ---------------------------------------------------------
        canvas_container = ttk.LabelFrame(self, text="🌐 Direcciones de los 6 Microservicios y Redis", padding=12)
        canvas_container.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        grid = ttk.Frame(canvas_container)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.columnconfigure(1, weight=1)

        # 1. Login
        ttk.Label(grid, text="1. Login / Auth (:5000):", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.txt_auth = ttk.Entry(grid, font=("Consolas", 9))
        self.txt_auth.grid(row=0, column=1, sticky="ew", pady=4, padx=5)
        self.txt_auth.insert(0, settings.auth_url)

        # 2. Books
        ttk.Label(grid, text="2. Books / Catálogo (:5001):", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.txt_books = ttk.Entry(grid, font=("Consolas", 9))
        self.txt_books.grid(row=1, column=1, sticky="ew", pady=4, padx=5)
        self.txt_books.insert(0, settings.books_url)

        # 3. Users
        ttk.Label(grid, text="3. Users / Perfiles (:5002):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=4, padx=5)
        self.txt_users = ttk.Entry(grid, font=("Consolas", 9))
        self.txt_users.grid(row=2, column=1, sticky="ew", pady=4, padx=5)
        self.txt_users.insert(0, settings.users_url)

        # 4. Authors
        ttk.Label(grid, text="4. Authors (:5003):", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=4, padx=5)
        self.txt_authors = ttk.Entry(grid, font=("Consolas", 9))
        self.txt_authors.grid(row=3, column=1, sticky="ew", pady=4, padx=5)
        self.txt_authors.insert(0, settings.authors_url)

        # 5. Orders
        ttk.Label(grid, text="5. Pedidos / Stock (:5004):", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=4, padx=5)
        self.txt_orders = ttk.Entry(grid, font=("Consolas", 9))
        self.txt_orders.grid(row=4, column=1, sticky="ew", pady=4, padx=5)
        self.txt_orders.insert(0, settings.orders_url)

        # 6. Payments
        ttk.Label(grid, text="6. Pagos (:5005):", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=4, padx=5)
        self.txt_payments = ttk.Entry(grid, font=("Consolas", 9))
        self.txt_payments.grid(row=5, column=1, sticky="ew", pady=4, padx=5)
        self.txt_payments.insert(0, settings.payments_url)

        # 7. Redis
        ttk.Label(grid, text="7. Redis Host & Puerto (:6379):", font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="w", pady=4, padx=5)
        redis_row = ttk.Frame(grid)
        redis_row.grid(row=6, column=1, sticky="ew", pady=4, padx=5)
        redis_row.columnconfigure(0, weight=3)
        redis_row.columnconfigure(1, weight=1)

        self.txt_redis_host = ttk.Entry(redis_row, font=("Consolas", 9))
        self.txt_redis_host.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.txt_redis_host.insert(0, settings.redis_host)

        self.txt_redis_port = ttk.Entry(redis_row, font=("Consolas", 9), width=8)
        self.txt_redis_port.grid(row=0, column=1, sticky="ew")
        self.txt_redis_port.insert(0, str(settings.redis_port))

        # ---------------------------------------------------------
        # Botones de Acción
        # ---------------------------------------------------------
        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=(0, 5))

        self.btn_save = ttk.Button(actions, text="💾 Guardar Cambios y Reconectar", command=self._save_settings)
        self.btn_save.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_status = ttk.Label(actions, text="", font=("Segoe UI", 9))
        self.lbl_status.pack(side=tk.LEFT)

    def _apply_local_preset(self):
        settings.set_local()
        settings.save()
        self._refresh_fields_from_settings()
        self.lbl_status.config(text="Modo Local (localhost) aplicado y guardado exitosamente.", foreground="#16a34a")
        if self.on_settings_saved:
            self.on_settings_saved()

    def _apply_remote_preset(self):
        settings.set_remote(DEFAULT_REMOTE_HOST)
        settings.save()
        self._refresh_fields_from_settings()
        self.lbl_status.config(text="Modo Remoto (GCP) aplicado y guardado exitosamente.", foreground="#0284c7")
        if self.on_settings_saved:
            self.on_settings_saved()

    def _refresh_fields_from_settings(self):
        self.txt_auth.delete(0, tk.END)
        self.txt_auth.insert(0, settings.auth_url)

        self.txt_books.delete(0, tk.END)
        self.txt_books.insert(0, settings.books_url)

        self.txt_users.delete(0, tk.END)
        self.txt_users.insert(0, settings.users_url)

        self.txt_authors.delete(0, tk.END)
        self.txt_authors.insert(0, settings.authors_url)

        self.txt_orders.delete(0, tk.END)
        self.txt_orders.insert(0, settings.orders_url)

        self.txt_payments.delete(0, tk.END)
        self.txt_payments.insert(0, settings.payments_url)

        self.txt_redis_host.delete(0, tk.END)
        self.txt_redis_host.insert(0, settings.redis_host)

        self.txt_redis_port.delete(0, tk.END)
        self.txt_redis_port.insert(0, str(settings.redis_port))

    def _save_settings(self):
        settings.auth_url = self.txt_auth.get().strip().rstrip("/")
        settings.books_url = self.txt_books.get().strip().rstrip("/")
        settings.users_url = self.txt_users.get().strip().rstrip("/")
        settings.authors_url = self.txt_authors.get().strip().rstrip("/")
        settings.orders_url = self.txt_orders.get().strip().rstrip("/")
        settings.payments_url = self.txt_payments.get().strip().rstrip("/")
        settings.redis_host = self.txt_redis_host.get().strip()
        try:
            settings.redis_port = int(self.txt_redis_port.get().strip())
        except ValueError:
            settings.redis_port = 6379

        if "localhost" in settings.auth_url or "127.0.0.1" in settings.auth_url:
            settings.active_env = "local"
        else:
            settings.active_env = "remote"

        ok = settings.save()
        if ok:
            messagebox.showinfo("Configuración Guardada", "Las direcciones de los 6 microservicios y Redis han sido actualizadas exitosamente.")
            self.lbl_status.config(text="Configuración guardada correctamente.", foreground="#16a34a")
            if self.on_settings_saved:
                self.on_settings_saved()
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración en config.json.")
