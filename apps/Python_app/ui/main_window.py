"""
ui/main_window.py
Ventana Principal de la Aplicación de Escritorio.
Implementa el Panel Principal estructurado en secciones:
  1. Catálogo de libros (CatalogTab)
  2. Administración de libros (AdminBooksTab)
  3. Autores y relaciones (AuthorsTab)
  4. Pedidos y stock atómico (OrdersTab)
  5. Pasarela de pagos simulada (PaymentsTab)
  6. Usuarios y roles [Admin] (UsersTab)
  7. Sesión y perfil (ProfileTab)
  8. Semáforo de salud de los 7 nodos (HealthTab)
  9. Configuración del servidor y Redis (SettingsTab)
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from session.session_manager import session_manager
from network.auth_service import auth_service
from ui.tabs.catalog_tab import CatalogTab
from ui.tabs.admin_books_tab import AdminBooksTab
from ui.tabs.authors_tab import AuthorsTab
from ui.tabs.orders_tab import OrdersTab
from ui.tabs.payments_tab import PaymentsTab
from ui.tabs.users_tab import UsersTab
from ui.tabs.profile_tab import ProfileTab
from ui.tabs.health_tab import HealthTab
from ui.tabs.settings_tab import SettingsTab
from ui.widgets.status_badge import StatusBadge


class MainWindow(ttk.Frame):
    def __init__(self, root, user_data, on_logout_callback):
        super().__init__(root)
        self.root = root
        self.user_data = user_data or {}
        self.on_logout_callback = on_logout_callback

        self._jwt_timer_id = None
        self._jwt_refreshing = False

        self.root.title("Librería en Línea — Ecosistema de Microservicios & Redis")
        self.root.geometry("1180x760")
        self.root.minsize(1040, 680)

        # Centrar en pantalla
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1180 // 2)
        y = (self.root.winfo_screenheight() // 2) - (760 // 2)
        self.root.geometry(f"+{x}+{y}")

        self.pack(fill=tk.BOTH, expand=True)

        self._build_ui()

        # Iniciar ciclo de chequeo periódico de expiración de JWT cada 30 segundos
        self._jwt_timer_id = self.after(30000, self._check_jwt_expiration)

        # Forzar visibilidad al frente de la pantalla
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        self.root.focus_force()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Barra Superior de Encabezado (Header)
        # ---------------------------------------------------------
        header = tk.Frame(self, bg="#0f172a", height=65)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Título y logotipo
        left_box = tk.Frame(header, bg="#0f172a")
        left_box.pack(side=tk.LEFT, padx=15, fill=tk.Y)

        lbl_logo = tk.Label(left_box, text="📚 Librería en Línea", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_logo.pack(anchor=tk.W, pady=(8, 0))

        lbl_sub = tk.Label(left_box, text="Capa Compartida Redis (Caché + Sesiones + JWT + Stock + Pagos)", font=("Segoe UI", 8), fg="#38bdf8", bg="#0f172a")
        lbl_sub.pack(anchor=tk.W)

        # Semáforos rápidos en el header (a la derecha)
        right_box = tk.Frame(header, bg="#0f172a")
        right_box.pack(side=tk.RIGHT, padx=15, fill=tk.Y)

        self.btn_header_logout = ttk.Button(right_box, text="Cerrar Sesión", command=self._do_logout)
        self.btn_header_logout.pack(side=tk.RIGHT, pady=16, padx=(10, 0))

        # Información de usuario
        username = self.user_data.get("username", "usuario")
        nombre = self.user_data.get("nombre") or username
        role = (self.user_data.get("role") or "user").upper()

        user_info_frame = tk.Frame(right_box, bg="#0f172a")
        user_info_frame.pack(side=tk.RIGHT, padx=12, pady=12)

        self.lbl_user_name = tk.Label(user_info_frame, text=f"👤 {nombre}", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a")
        self.lbl_user_name.pack(anchor=tk.E)

        self.lbl_user_role = tk.Label(user_info_frame, text=f"Rol: {role} ({self.user_data.get('email', '')})", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a")
        self.lbl_user_role.pack(anchor=tk.E)

        # ---------------------------------------------------------
        # Contenedor Principal de Pestañas (Notebook)
        # ---------------------------------------------------------
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 1. Catálogo de Libros (Cache-Aside en Redis)
        self.tab_catalog = CatalogTab(self.notebook)
        self.notebook.add(self.tab_catalog, text="  📚 Catálogo  ")

        # 2. Administración de Libros (CRUD y Cache Invalidation)
        self.tab_admin = AdminBooksTab(self.notebook, on_catalog_changed=self.tab_catalog.load_books)
        self.notebook.add(self.tab_admin, text="  🛠️ Admin Libros  ")

        # 3. Autores y Relaciones
        self.tab_authors = AuthorsTab(self.notebook)
        self.notebook.add(self.tab_authors, text="  ✍️ Autores  ")

        # 4. Pedidos y Stock Atómico
        self.tab_orders = OrdersTab(self.notebook)
        self.notebook.add(self.tab_orders, text="  📦 Pedidos & Stock  ")

        # 5. Pasarela de Pagos Simulada
        self.tab_payments = PaymentsTab(self.notebook)
        self.notebook.add(self.tab_payments, text="  💳 Pagos  ")

        # 6. Usuarios y Roles (Admin)
        if role == "ADMIN":
            self.tab_users = UsersTab(self.notebook)
            self.notebook.add(self.tab_users, text="  👥 Usuarios & Roles  ")

        # 7. Sesión y Perfil
        self.tab_profile = ProfileTab(self.notebook, on_logout_callback=self.on_logout_callback)
        self.notebook.add(self.tab_profile, text="  👤 Mi Perfil  ")

        # 8. Estado de los 7 Componentes (Semáforo)
        self.tab_health = HealthTab(self.notebook, on_status_updated=self._on_health_status_updated)
        self.notebook.add(self.tab_health, text="  🚦 Semáforo de Salud (7 Nodos)  ")

        # 9. Configuración del Servidor
        self.tab_settings = SettingsTab(self.notebook, on_settings_saved=self._on_settings_saved)
        self.notebook.add(self.tab_settings, text="  ⚙️ Configuración  ")

    def _on_health_status_updated(self, *args, **kwargs):
        """Callback cuando el semáforo de salud actualiza estado."""
        pass

    def _on_settings_saved(self):
        """Callback cuando se guardan nuevas URLs de microservicios."""
        if hasattr(self.tab_health, 'update_urls'):
            self.tab_health.update_urls()
        self.tab_health.check_all_services()
        self.tab_catalog.load_books()
        self.tab_admin.refresh_table()
        if hasattr(self, 'tab_authors'):
            self.tab_authors.load_authors()
        if hasattr(self, 'tab_orders'):
            self.tab_orders.load_orders()
        if hasattr(self, 'tab_users'):
            self.tab_users.load_users()

    def _check_jwt_expiration(self):
        """
        Temporizador de renovación automática de JWT:
        Verifica la expiración localmente cada 30 segundos (self.after(30000, self._check_jwt_expiration)).
        Si al token le quedan menos de 5 minutos (300 segundos) de vigencia y el usuario está autenticado,
        llama automáticamente en segundo plano a auth_service.refresh_token().
        Al recibir el nuevo token, actualiza la sesión y registra en consola:
        [JWT-WATCHDOG] Token renovado automáticamente con éxito (vigencia extendida a 20 min)
        """
        try:
            user = session_manager.get_user() or self.user_data
            if user and not self._jwt_refreshing:
                rem_sec = session_manager.get_jwt_remaining_seconds()
                if rem_sec is not None:
                    if rem_sec < 300:
                        print(f"[JWT-WATCHDOG] Token por expirar en {int(rem_sec)}s (< 300s). Solicitando renovación automática...")
                        self._jwt_refreshing = True
                        threading.Thread(target=self._run_token_refresh_thread, daemon=True).start()
        except Exception as e:
            print(f"[JWT-WATCHDOG] Error al verificar expiración de JWT: {e}")
        finally:
            self._jwt_timer_id = self.after(30000, self._check_jwt_expiration)

    def _run_token_refresh_thread(self):
        """Ejecuta la renovación del token en segundo plano y actualiza la sesión persistida."""
        try:
            res = auth_service.refresh_token()
            if res.get("success") and res.get("data"):
                new_token = res["data"].get("token")
                if new_token:
                    user = session_manager.get_user() or self.user_data
                    session_manager.save_session(user)
                    print("[JWT-WATCHDOG] Token renovado automáticamente con éxito (vigencia extendida a 20 min)")
            else:
                err_msg = res.get("error") or (res.get("data") or {}).get("message") or "Respuesta no exitosa"
                print(f"[JWT-WATCHDOG] Advertencia al renovar token: {err_msg}")
        except Exception as err:
            print(f"[JWT-WATCHDOG] Excepción durante la renovación automática de JWT: {err}")
        finally:
            self._jwt_refreshing = False

    def _do_logout(self):
        """
        Cierre de sesión seguro con revocación en servidor y Redis:
        Revoca el JTI en Redis (jwt:revoked:<jti>) vía auth_service.logout(),
        limpia la sesión local en session_manager y regresa a la pantalla de login.
        """
        confirm = messagebox.askyesno(
            "Confirmar Salida",
            "¿Está seguro de que desea cerrar la sesión actual?\nSe revocará el JWT en Redis."
        )
        if not confirm:
            return

        # Cancelar el watchdog de renovación de JWT si está activo
        if self._jwt_timer_id:
            try:
                self.after_cancel(self._jwt_timer_id)
            except Exception:
                pass
            self._jwt_timer_id = None

        def logout_thread():
            try:
                auth_service.logout()
            except Exception as e:
                print(f"[AUTH-LOGOUT] Advertencia al revocar sesión en servidor: {e}")
            finally:
                session_manager.clear_session()
                self.after(0, self.on_logout_callback)

        threading.Thread(target=logout_thread, daemon=True).start()

    def destroy(self):
        """Detiene timers pendientes al destruir el frame."""
        if self._jwt_timer_id:
            try:
                self.after_cancel(self._jwt_timer_id)
            except Exception:
                pass
            self._jwt_timer_id = None
        super().destroy()
