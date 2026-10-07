"""
ui/tabs/health_tab.py
Pestaña de Monitoreo de Estado de los 7 Componentes del Ecosistema:
  1. Microservicio de Login / Auth (:5000)
  2. Microservicio de Libros (:5001)
  3. Microservicio de Usuarios (:5002)
  4. Microservicio de Autores (:5003)
  5. Microservicio de Pedidos (:5004)
  6. Microservicio de Pagos (:5005)
  7. Servidor en memoria Redis (:6379)
"""
import socket
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk

from config.settings import settings
from network.auth_service import auth_service
from network.books_service import books_service
from network.users_service import users_service
from network.authors_service import authors_service
from network.orders_service import orders_service
from network.payments_service import payments_service
from ui.widgets.status_badge import StatusBadge, COLOR_OK, COLOR_DEGRADED, COLOR_ERROR, COLOR_UNKNOWN


class HealthTab(ttk.Frame):
    def __init__(self, parent, on_status_updated=None):
        super().__init__(parent, padding=12)
        self.on_status_updated = on_status_updated
        self.poll_timer_id = None

        self._build_ui()
        self.check_all_services()
        self._schedule_next_poll()

    def _build_ui(self):
        # --- Barra Superior de Control ---
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        self.btn_check_now = ttk.Button(top_bar, text="🔄 Comprobar 7 Nodos", command=self.check_all_services)
        self.btn_check_now.pack(side=tk.LEFT, padx=(0, 15))

        self.lbl_last_check = ttk.Label(top_bar, text="Última comprobación: Calculando...", font=("Segoe UI", 9), foreground="#64748b")
        self.lbl_last_check.pack(side=tk.LEFT)

        self.lbl_env_badge = ttk.Label(top_bar, text=f"Entorno: {settings.active_env.upper()}", font=("Segoe UI", 9, "bold"), foreground="#0284c7")
        self.lbl_env_badge.pack(side=tk.RIGHT)

        # --- Contenedor de Tarjetas (Grid 3 columnas) ---
        grid_frame = ttk.Frame(self)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        for col in range(3):
            grid_frame.columnconfigure(col, weight=1, uniform="health_col")

        # 1. Login (:5000)
        self.card_auth, self.badge_auth, self.lbl_auth_det, self.lbl_auth_url = self._create_card(
            grid_frame, "1. Login / Auth (:5000)", settings.auth_url, row=0, col=0
        )
        # 2. Books (:5001)
        self.card_books, self.badge_books, self.lbl_books_det, self.lbl_books_url = self._create_card(
            grid_frame, "2. Books / Catálogo (:5001)", settings.books_url, row=0, col=1
        )
        # 3. Users (:5002)
        self.card_users, self.badge_users, self.lbl_users_det, self.lbl_users_url = self._create_card(
            grid_frame, "3. Users / Perfiles (:5002)", settings.users_url, row=0, col=2
        )
        # 4. Authors (:5003)
        self.card_authors, self.badge_authors, self.lbl_authors_det, self.lbl_authors_url = self._create_card(
            grid_frame, "4. Authors (:5003)", settings.authors_url, row=1, col=0
        )
        # 5. Pedidos (:5004)
        self.card_orders, self.badge_orders, self.lbl_orders_det, self.lbl_orders_url = self._create_card(
            grid_frame, "5. Pedidos / Stock (:5004)", settings.orders_url, row=1, col=1
        )
        # 6. Pagos (:5005)
        self.card_payments, self.badge_payments, self.lbl_payments_det, self.lbl_payments_url = self._create_card(
            grid_frame, "6. Pagos Simulados (:5005)", settings.payments_url, row=1, col=2
        )
        # 7. Redis (:6379)
        self.card_redis, self.badge_redis, self.lbl_redis_det, self.lbl_redis_url = self._create_card(
            grid_frame, "7. Redis Compartido (:6379)", f"{settings.redis_host}:{settings.redis_port}", row=2, col=0, colspan=3
        )

    def _create_card(self, parent, title, url_text, row, col, colspan=1):
        card = ttk.LabelFrame(parent, text=title, padding=10)
        card.grid(row=row, column=col, columnspan=colspan, padx=6, pady=6, sticky="nsew")

        top = ttk.Frame(card)
        top.pack(fill=tk.X)

        badge = StatusBadge(top, service_name=title)
        badge.pack(side=tk.LEFT, pady=2)

        lbl_url = ttk.Label(top, text=url_text, font=("Consolas", 8), foreground="#64748b")
        lbl_url.pack(side=tk.RIGHT, pady=2)

        lbl_det = ttk.Label(card, text="Iniciando comprobación...", font=("Segoe UI", 8), foreground="#475569", wraplength=320)
        lbl_det.pack(anchor=tk.W, pady=(6, 0))

        return card, badge, lbl_det, lbl_url

    def check_all_services(self):
        """Dispara la verificación asíncrona de los 7 componentes en un hilo secundario."""
        self.btn_check_now.config(state=tk.DISABLED)
        self.lbl_last_check.config(text="Comprobando los 7 nodos en paralelo...")

        threading.Thread(target=self._run_checks_thread, daemon=True).start()

    def _run_checks_thread(self):
        results = {}

        # 1. Login (:5000)
        t0 = time.time()
        auth_res = auth_service.health()
        auth_lat = (time.time() - t0) * 1000
        results["auth"] = self._parse_http_health(auth_res, auth_lat)

        # 2. Books (:5001)
        t0 = time.time()
        books_res = books_service.health()
        books_lat = (time.time() - t0) * 1000
        results["books"] = self._parse_http_health(books_res, books_lat)

        # 3. Users (:5002)
        t0 = time.time()
        users_res = users_service.health()
        users_lat = (time.time() - t0) * 1000
        results["users"] = self._parse_http_health(users_res, users_lat)

        # 4. Authors (:5003)
        t0 = time.time()
        authors_res = authors_service.health()
        authors_lat = (time.time() - t0) * 1000
        results["authors"] = self._parse_http_health(authors_res, authors_lat)

        # 5. Pedidos (:5004)
        t0 = time.time()
        orders_res = orders_service.health()
        orders_lat = (time.time() - t0) * 1000
        results["orders"] = self._parse_http_health(orders_res, orders_lat)

        # 6. Pagos (:5005)
        t0 = time.time()
        payments_res = payments_service.health()
        payments_lat = (time.time() - t0) * 1000
        results["payments"] = self._parse_http_health(payments_res, payments_lat)

        # 7. Redis (:6379)
        results["redis"] = self._check_redis_socket(settings.redis_host, settings.redis_port)

        self.after(0, lambda: self._apply_results_ui(results))

    def _parse_http_health(self, res, latency_ms):
        if not res["success"]:
            err_msg = res.get("error") or "Servicio fuera de línea"
            return {
                "state": "error",
                "badge": f"{latency_ms:.0f} ms",
                "detail": f"Error: {err_msg}"
            }

        data = res.get("data") or {}
        st = (data.get("status") or "ok").lower()
        db_raw = data.get("database") or {}
        red_raw = data.get("redis") or {}

        # Evaluar estado de base de datos (dict o string)
        if isinstance(db_raw, dict):
            db_status = db_raw.get("status", "ok")
            db_err = db_raw.get("error")
        else:
            db_status = str(db_raw)
            db_err = None

        # Evaluar estado de Redis (dict o string)
        if isinstance(red_raw, dict):
            red_status = red_raw.get("status", "ok")
        else:
            red_status = str(red_raw)

        is_db_ok = db_status in ("connected", "ok", "healthy")
        is_red_ok = red_status in ("connected", "ok", "healthy", "active")

        if is_db_ok and is_red_ok:
            return {
                "state": "ok",
                "badge": f"{latency_ms:.0f} ms",
                "detail": f"PostgreSQL: Conectado | Redis: OK (Puerto {data.get('port', '')})"
            }
        elif is_db_ok and not is_red_ok:
            return {
                "state": "degraded",
                "badge": f"{latency_ms:.0f} ms",
                "detail": "PostgreSQL: OK | Redis: Desconectado (Fail-Safe activo)"
            }
        else:
            return {
                "state": "degraded" if st in ("ok", "healthy", "degraded") else "error",
                "badge": f"{latency_ms:.0f} ms",
                "detail": f"Base de datos no disponible ({db_err or st})"
            }

    def _check_redis_socket(self, host, port):
        t0 = time.time()
        try:
            target_host = "127.0.0.1" if host == "localhost" else host
            s = socket.create_connection((target_host, int(port)), timeout=2.0)
            s.sendall(b"*1\r\n$4\r\nPING\r\n")
            resp = s.recv(1024)
            lat = (time.time() - t0) * 1000
            s.close()
            if b"+PONG" in resp:
                return {
                    "state": "ok",
                    "badge": f"{lat:.0f} ms",
                    "detail": f"Socket RESP2 PING -> +PONG recibido. Memoria en {host}:{port}"
                }
            return {
                "state": "degraded",
                "badge": f"{lat:.0f} ms",
                "detail": f"Respuesta inesperada de Redis: {resp[:30]}"
            }
        except Exception as e:
            return {
                "state": "error",
                "badge": "Caído",
                "detail": f"No se pudo conectar a {host}:{port} -> {e}"
            }

    def _apply_results_ui(self, results):
        self.btn_check_now.config(state=tk.NORMAL)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_last_check.config(text=f"Última comprobación: {now_str}")
        self.lbl_env_badge.config(text=f"Entorno: {settings.active_env.upper()}")

        # Actualizar URLs dinámicas mostradas en cada tarjeta
        self.lbl_auth_url.config(text=settings.auth_url)
        self.lbl_books_url.config(text=settings.books_url)
        self.lbl_users_url.config(text=settings.users_url)
        self.lbl_authors_url.config(text=settings.authors_url)
        self.lbl_orders_url.config(text=settings.orders_url)
        self.lbl_payments_url.config(text=settings.payments_url)
        self.lbl_redis_url.config(text=f"{settings.redis_host}:{settings.redis_port}")

        # Actualizar cada badge y texto
        mapping = [
            ("auth", self.badge_auth, self.lbl_auth_det),
            ("books", self.badge_books, self.lbl_books_det),
            ("users", self.badge_users, self.lbl_users_det),
            ("authors", self.badge_authors, self.lbl_authors_det),
            ("orders", self.badge_orders, self.lbl_orders_det),
            ("payments", self.badge_payments, self.lbl_payments_det),
            ("redis", self.badge_redis, self.lbl_redis_det),
        ]

        for key, badge, lbl in mapping:
            info = results.get(key, {})
            badge.set_status(info.get("state", "unknown"), info.get("badge", ""))
            lbl.config(text=info.get("detail", ""))

        if self.on_status_updated:
            self.on_status_updated(results)

    def _schedule_next_poll(self):
        if self.poll_timer_id:
            self.after_cancel(self.poll_timer_id)
        # Polling automático cada 15 segundos
        self.poll_timer_id = self.after(15000, self._auto_poll)

    def _auto_poll(self):
        self.check_all_services()
        self._schedule_next_poll()
