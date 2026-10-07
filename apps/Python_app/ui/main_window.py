"""
ui/main_window.py
Ventana Principal de la Aplicación de Escritorio.
Implementa el Panel Principal estructurado en 5 secciones claras (Requisito 4):
  1. Catálogo de libros (CatalogTab)
  2. Administración de libros (AdminBooksTab)
  3. Sesión y perfil (ProfileTab)
  4. Estado de los servicios (HealthTab)
  5. Configuración del servidor (SettingsTab)
"""
import tkinter as tk
from tkinter import ttk, messagebox

from session.session_manager import session_manager
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
        self.tab_health.check_all_services()
        self.tab_catalog.load_books()
        self.tab_admin.refresh_table()
        if hasattr(self, 'tab_authors'):
            self.tab_authors.load_authors()
        if hasattr(self, 'tab_orders'):
            self.tab_orders.load_orders()
        if hasattr(self, 'tab_users'):
            self.tab_users.load_users()

    def _do_logout(self):
        confirm = messagebox.askyesno("Confirmar Salida", "¿Está seguro de que desea cerrar la sesión actual?\nSe revocará el JWT en Redis.")
        if confirm:
            session_manager.clear_session()
            self.on_logout_callback()
