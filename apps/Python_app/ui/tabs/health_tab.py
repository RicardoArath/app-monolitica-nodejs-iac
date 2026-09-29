"""
ui/tabs/health_tab.py
Pestaña de Monitoreo de Estado de Microservicios (Semáforo de 3 estados).
Diferencia:
  🟢 Servicio operativo y con acceso a PostgreSQL.
  🟡 Servicio accesible, pero con base de datos no disponible o degradada.
  🔴 Servicio inaccesible, caído, sin respuesta o error de conexión.
Muestra:
  - Fecha y hora exacta de la última comprobación
  - Botón de refresco manual
  - Polling periódico automático
  - Guía integrada para la prueba de tolerancia a fallos (Casos A, B, C, D)
"""
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk

from network.auth_service import auth_service
from network.books_service import books_service
from ui.widgets.status_badge import StatusBadge, COLOR_OK, COLOR_DEGRADED, COLOR_ERROR, COLOR_UNKNOWN


class HealthTab(ttk.Frame):
    def __init__(self, parent, on_status_updated=None):
        super().__init__(parent, padding=15)
        self.on_status_updated = on_status_updated

        self.last_check_str = "Nunca"
        self.auto_poll_enabled = True
        self.poll_timer_id = None

        self._build_ui()
        self.check_all_services()
        self._schedule_next_poll()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Barra Superior de Control
        # ---------------------------------------------------------
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 15))

        self.btn_check_now = ttk.Button(top_bar, text="🔄 Comprobar Ahora", command=self.check_all_services)
        self.btn_check_now.pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_last_check = ttk.Label(top_bar, text="Última comprobación: Calculando...", font=("Segoe UI", 9), foreground="#64748b")
        self.lbl_last_check.pack(side=tk.LEFT)

        # ---------------------------------------------------------
        # Tarjetas de Estado de los Microservicios
        # ---------------------------------------------------------
        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill=tk.X, pady=(0, 15))

        # Tarjeta Microservicio de Login (5000)
        self.card_auth = ttk.LabelFrame(cards_frame, text="Microservicio de Autenticación (:5000)", padding=12)
        self.card_auth.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.badge_auth = StatusBadge(self.card_auth, "Auth Service")
        self.badge_auth.pack(anchor=tk.W, pady=(0, 8))

        self.lbl_auth_url = ttk.Label(self.card_auth, text=f"URL: {auth_service.base_url}", font=("Consolas", 8), foreground="#475569")
        self.lbl_auth_url.pack(anchor=tk.W)

        self.lbl_auth_db = ttk.Label(self.card_auth, text="Base de Datos: -", font=("Segoe UI", 9))
        self.lbl_auth_db.pack(anchor=tk.W, pady=2)

        self.lbl_auth_time = ttk.Label(self.card_auth, text="Tiempo de respuesta: -", font=("Segoe UI", 9))
        self.lbl_auth_time.pack(anchor=tk.W)

        # Tarjeta Microservicio de Libros (5001)
        self.card_books = ttk.LabelFrame(cards_frame, text="Microservicio de Libros (:5001)", padding=12)
        self.card_books.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.badge_books = StatusBadge(self.card_books, "Books Service")
        self.badge_books.pack(anchor=tk.W, pady=(0, 8))

        self.lbl_books_url = ttk.Label(self.card_books, text=f"URL: {books_service.base_url}", font=("Consolas", 8), foreground="#475569")
        self.lbl_books_url.pack(anchor=tk.W)

        self.lbl_books_db = ttk.Label(self.card_books, text="Base de Datos: -", font=("Segoe UI", 9))
        self.lbl_books_db.pack(anchor=tk.W, pady=2)

        self.lbl_books_time = ttk.Label(self.card_books, text="Tiempo de respuesta: -", font=("Segoe UI", 9))
        self.lbl_books_time.pack(anchor=tk.W)

        # ---------------------------------------------------------
        # Guía Explicativa de Tolerancia a Fallos (Requisito 6)
        # ---------------------------------------------------------
        guide_box = ttk.LabelFrame(self, text="📋 Guía de Pruebas de Tolerancia a Fallos (Requisito 6 de la Rúbrica)", padding=12)
        guide_box.pack(fill=tk.BOTH, expand=True)

        guide_text = (
            "Para cumplir con el Requisito 6, provoque las siguientes situaciones y observe que la app NO se cierra:\n\n"
            "• Caso A — Ambos microservicios disponibles:\n"
            "   Ambos semáforos se iluminan en 🟢 Verde. El catálogo y el login responden normalmente.\n\n"
            "• Caso B — Detener el microservicio de libros:\n"
            "   Ejecute en GCP: sudo systemctl stop books-microservice\n"
            "   Presione 'Comprobar Ahora': El semáforo de Libros pasa a 🔴 Rojo. La aplicación continúa funcionando\n"
            "   y al entrar al catálogo muestra un mensaje amigable sin provocar un traceback ni cerrarse.\n\n"
            "• Caso C — Restaurar el microservicio de libros:\n"
            "   Ejecute en GCP: sudo systemctl start books-microservice\n"
            "   Presione 'Comprobar Ahora': El semáforo pasa nuevamente a 🟢 Verde y el catálogo vuelve a operar.\n\n"
            "• Caso D — Intentar utilizar una URL o puerto incorrecto:\n"
            "   En la pestaña 'Configuración', coloque una dirección inválida como http://localhost:9999\n"
            "   y presione 'Probar Conexión'. La app detecta el error de red, marca 🔴 y notifica al usuario sin crashear."
        )
        txt = tk.Text(guide_box, wrap="word", font=("Segoe UI", 9), bg="#f8fafc", relief="flat")
        txt.insert("1.0", guide_text)
        txt.config(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True)

    def check_all_services(self):
        """Ejecuta la comprobación de /health en ambos microservicios en un hilo de fondo."""
        self.btn_check_now.config(state=tk.DISABLED)

        # Actualizar URLs mostradas
        self.lbl_auth_url.config(text=f"URL: {auth_service.base_url}")
        self.lbl_books_url.config(text=f"URL: {books_service.base_url}")

        def thread_task():
            # Auth health
            t0 = time.time()
            res_auth = auth_service.health()
            t_auth = int((time.time() - t0) * 1000)

            # Books health
            t1 = time.time()
            res_books = books_service.health()
            t_books = int((time.time() - t1) * 1000)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.after(0, lambda: self._apply_results(res_auth, t_auth, res_books, t_books, now_str))

        threading.Thread(target=thread_task, daemon=True).start()

    def _apply_results(self, res_auth, t_auth, res_books, t_books, now_str):
        self.btn_check_now.config(state=tk.NORMAL)
        self.last_check_str = now_str
        self.lbl_last_check.config(text=f"Última comprobación: {now_str}")

        # Procesar Auth
        auth_state = self._determine_state(res_auth)
        if auth_state == "ok":
            self.badge_auth.set_status("ok", f"{t_auth} ms")
            self.lbl_auth_db.config(text="Base de Datos: Conectada (PostgreSQL OK)", foreground="#16a34a")
            self.lbl_auth_time.config(text=f"Tiempo de respuesta: {t_auth} ms")
        elif auth_state == "degraded":
            self.badge_auth.set_status("degraded", "BD Desconectada")
            self.lbl_auth_db.config(text="Base de Datos: Degradada / Error BD", foreground="#ca8a04")
            self.lbl_auth_time.config(text=f"Tiempo de respuesta: {t_auth} ms")
        else:
            self.badge_auth.set_status("error", "Sin conexión")
            self.lbl_auth_db.config(text="Base de Datos: Inaccesible", foreground="#dc2626")
            self.lbl_auth_time.config(text="Tiempo de respuesta: N/A")

        # Procesar Books
        books_state = self._determine_state(res_books)
        if books_state == "ok":
            self.badge_books.set_status("ok", f"{t_books} ms")
            self.lbl_books_db.config(text="Base de Datos: Conectada (PostgreSQL OK)", foreground="#16a34a")
            self.lbl_books_time.config(text=f"Tiempo de respuesta: {t_books} ms")
        elif books_state == "degraded":
            self.badge_books.set_status("degraded", "BD Desconectada")
            self.lbl_books_db.config(text="Base de Datos: Degradada / Error BD", foreground="#ca8a04")
            self.lbl_books_time.config(text=f"Tiempo de respuesta: {t_books} ms")
        else:
            self.badge_books.set_status("error", "Sin conexión")
            self.lbl_books_db.config(text="Base de Datos: Inaccesible", foreground="#dc2626")
            self.lbl_books_time.config(text="Tiempo de respuesta: N/A")

        if self.on_status_updated:
            self.on_status_updated(auth_state, books_state)

    def _determine_state(self, res):
        """Determina el estado: 'ok' (verde), 'degraded' (amarillo), 'error' (rojo)."""
        if not res["success"]:
            return "error"

        data = res["data"] or {}
        status = data.get("status", "").lower()
        db = data.get("database", "").lower()

        if status == "ok" and db == "connected":
            return "ok"
        elif status == "degraded" or db != "connected":
            return "degraded"
        return "error"

    def _schedule_next_poll(self):
        """Programa la siguiente verificación automática en 30 segundos."""
        if self.auto_poll_enabled:
            self.poll_timer_id = self.after(30000, self._on_auto_poll)

    def _on_auto_poll(self):
        self.check_all_services()
        self._schedule_next_poll()
