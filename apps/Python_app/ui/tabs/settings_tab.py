"""
ui/tabs/settings_tab.py
Pestaña de Configuración del Servidor y Entornos (Requisitos 13 y 14 de la Rúbrica).
Permite:
- Alternar entre Entorno Local (localhost) y Entorno Remoto (GCP) sin tocar código fuente
- Modificar manualmente las URLs de los microservicios
- Probar la conectividad de los endpoints antes de guardar
- Guardar la configuración en config.json para que persista entre reinicios
- Restaurar valores predeterminados
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import (
    settings,
    DEFAULT_LOCAL_AUTH,
    DEFAULT_LOCAL_BOOKS,
    DEFAULT_REMOTE_AUTH,
    DEFAULT_REMOTE_BOOKS
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
        preset_box = ttk.LabelFrame(self, text="⚡ Selección Rápida de Entorno (Requisito 14)", padding=12)
        preset_box.pack(fill=tk.X, pady=(0, 15))

        btn_row = ttk.Frame(preset_box)
        btn_row.pack(fill=tk.X)

        self.btn_preset_remote = ttk.Button(btn_row, text="☁️ Modo Remoto (Nube GCP 35.193.230.144)", command=self._apply_remote_preset)
        self.btn_preset_remote.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        self.btn_preset_local = ttk.Button(btn_row, text="🏠 Modo Local (localhost:5000 / 5001)", command=self._apply_local_preset)
        self.btn_preset_local.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---------------------------------------------------------
        # Entradas de URLs Personalizadas
        # ---------------------------------------------------------
        url_box = ttk.LabelFrame(self, text="🌐 Direcciones de los Microservicios (Requisito 13)", padding=15)
        url_box.pack(fill=tk.X, pady=(0, 15))

        # Auth URL
        ttk.Label(url_box, text="URL Microservicio de Autenticación (Login, Sesiones, Registro):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_auth_url = ttk.Entry(url_box, font=("Segoe UI", 10))
        self.txt_auth_url.pack(fill=tk.X, pady=(2, 10))
        self.txt_auth_url.insert(0, settings.auth_url)

        # Books URL
        ttk.Label(url_box, text="URL Microservicio de Libros (Catálogo, CRUD, Búsquedas):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_books_url = ttk.Entry(url_box, font=("Segoe UI", 10))
        self.txt_books_url.pack(fill=tk.X, pady=(2, 12))
        self.txt_books_url.insert(0, settings.books_url)

        # ---------------------------------------------------------
        # Panel de Pruebas de Conectividad
        # ---------------------------------------------------------
        test_box = ttk.LabelFrame(self, text="🔍 Diagnóstico de Conexión en Vivo", padding=12)
        test_box.pack(fill=tk.X, pady=(0, 15))

        self.lbl_auth_test = ttk.Label(test_box, text="• Autenticación (:5000): Pendiente de prueba", font=("Segoe UI", 9))
        self.lbl_auth_test.pack(anchor=tk.W, pady=2)

        self.lbl_books_test = ttk.Label(test_box, text="• Libros (:5001): Pendiente de prueba", font=("Segoe UI", 9))
        self.lbl_books_test.pack(anchor=tk.W, pady=2)

        self.btn_test_conn = ttk.Button(test_box, text="🧪 Probar Conexión con Estas URLs", command=self._test_connection)
        self.btn_test_conn.pack(anchor=tk.W, pady=(8, 0))

        # ---------------------------------------------------------
        # Botones de Acción (Guardar y Restaurar)
        # ---------------------------------------------------------
        actions_row = ttk.Frame(self)
        actions_row.pack(fill=tk.X)

        self.btn_save = ttk.Button(actions_row, text="💾 Guardar y Aplicar Configuración", command=self._save_settings)
        self.btn_save.pack(side=tk.LEFT, padx=(0, 10), ipady=3)

        self.btn_reset = ttk.Button(actions_row, text="↺ Restaurar Valores Predeterminados", command=self._reset_defaults)
        self.btn_reset.pack(side=tk.LEFT)

    def _apply_remote_preset(self):
        """Aplica el preset de la nube GCP."""
        self.txt_auth_url.delete(0, tk.END)
        self.txt_auth_url.insert(0, DEFAULT_REMOTE_AUTH)
        self.txt_books_url.delete(0, tk.END)
        self.txt_books_url.insert(0, DEFAULT_REMOTE_BOOKS)
        self._test_connection()

    def _apply_local_preset(self):
        """Aplica el preset local."""
        self.txt_auth_url.delete(0, tk.END)
        self.txt_auth_url.insert(0, DEFAULT_LOCAL_AUTH)
        self.txt_books_url.delete(0, tk.END)
        self.txt_books_url.insert(0, DEFAULT_LOCAL_BOOKS)
        self._test_connection()

    def _test_connection(self):
        """Prueba ambos endpoints en segundo plano."""
        auth_url = self.txt_auth_url.get().strip().rstrip("/")
        books_url = self.txt_books_url.get().strip().rstrip("/")

        self.btn_test_conn.config(state=tk.DISABLED)
        self.lbl_auth_test.config(text="• Autenticación: Comprobando conexión...", foreground="#0284c7")
        self.lbl_books_test.config(text="• Libros: Comprobando conexión...", foreground="#0284c7")

        def thread_task():
            res_auth = http_client.request("GET", f"{auth_url}/health", timeout=(2.0, 3.0))
            res_books = http_client.request("GET", f"{books_url}/health", timeout=(2.0, 3.0))

            self.after(0, lambda: self._on_test_done(res_auth, res_books))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_test_done(self, res_auth, res_books):
        self.btn_test_conn.config(state=tk.NORMAL)

        if res_auth["success"]:
            db = res_auth["data"].get("database", "ok") if res_auth["data"] else "ok"
            self.lbl_auth_test.config(text=f"• Autenticación (5000): 🟢 Conexión Exitosa (DB: {db})", foreground="#16a34a")
        else:
            self.lbl_auth_test.config(text=f"• Autenticación (5000): 🔴 Falló conexión ({res_auth['error']})", foreground="#dc2626")

        if res_books["success"]:
            db = res_books["data"].get("database", "ok") if res_books["data"] else "ok"
            self.lbl_books_test.config(text=f"• Libros (5001): 🟢 Conexión Exitosa (DB: {db})", foreground="#16a34a")
        else:
            self.lbl_books_test.config(text=f"• Libros (5001): 🔴 Falló conexión ({res_books['error']})", foreground="#dc2626")

    def _save_settings(self):
        """Guarda y hace persistente la configuración en config.json."""
        auth_url = self.txt_auth_url.get().strip().rstrip("/")
        books_url = self.txt_books_url.get().strip().rstrip("/")

        if not auth_url or not books_url:
            messagebox.showerror("Error", "Ambas URLs son obligatorias.")
            return

        settings.auth_url = auth_url
        settings.books_url = books_url
        ok = settings.save()

        if ok:
            messagebox.showinfo("Configuración Guardada", "Las direcciones de los microservicios han sido guardadas exitosamente y persistirán al reiniciar la aplicación.")
            if self.on_settings_saved:
                self.on_settings_saved()
        else:
            messagebox.showerror("Error", "No se pudo escribir en el archivo config.json.")

    def _reset_defaults(self):
        """Restaura los valores por defecto (Remoto GCP)."""
        settings.reset_defaults()
        self.txt_auth_url.delete(0, tk.END)
        self.txt_auth_url.insert(0, settings.auth_url)
        self.txt_books_url.delete(0, tk.END)
        self.txt_books_url.insert(0, settings.books_url)
        messagebox.showinfo("Restaurado", "Se han restaurado los valores predeterminados (Nube GCP).")
        if self.on_settings_saved:
            self.on_settings_saved()
