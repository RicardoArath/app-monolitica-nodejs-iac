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
from ui.tabs.profile_tab import ProfileTab
from ui.tabs.health_tab import HealthTab
from ui.tabs.settings_tab import SettingsTab
from ui.widgets.status_badge import StatusBadge


class MainWindow(ttk.Frame):
    def __init__(self, root, user_data, on_logout_callback):
        super().__init__(root)
        self.root = root
        self.user_data = user_data
        self.on_logout_callback = on_logout_callback

        self.root.title("Librería en Línea — Panel de Gestión y Catálogo")
        self.root.geometry("1100x720")
        self.root.minsize(980, 640)

        # Centrar en pantalla
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1100 // 2)
        y = (self.root.winfo_screenheight() // 2) - (720 // 2)
        self.root.geometry(f"+{x}+{y}")

        self.pack(fill=tk.BOTH, expand=True)

        self._build_ui()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Barra Superior de Encabezado (Header)
        # ---------------------------------------------------------
        header = tk.Frame(self, bg="#0f172a", height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Título y logotipo
        left_box = tk.Frame(header, bg="#0f172a")
        left_box.pack(side=tk.LEFT, padx=15, fill=tk.Y)

        lbl_logo = tk.Label(left_box, text="📚 Librería en Línea", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_logo.pack(anchor=tk.W, pady=(8, 0))

        lbl_sub = tk.Label(left_box, text="Cliente Python Multi-Microservicio (REST + JSON)", font=("Segoe UI", 8), fg="#94a3b8", bg="#0f172a")
        lbl_sub.pack(anchor=tk.W)

        # Semáforos rápidos en el header (a la derecha)
        right_box = tk.Frame(header, bg="#0f172a")
        right_box.pack(side=tk.RIGHT, padx=15, fill=tk.Y)

        self.btn_header_logout = ttk.Button(right_box, text="Cerrar Sesión", command=self._do_logout)
        self.btn_header_logout.pack(side=tk.RIGHT, pady=15, padx=(10, 0))

        # Información de usuario
        username = self.user_data.get("username", "usuario")
        nombre = self.user_data.get("nombre") or username
        role = self.user_data.get("role", "user").upper()

        user_info_frame = tk.Frame(right_box, bg="#0f172a")
        user_info_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        self.lbl_user_name = tk.Label(user_info_frame, text=f"👤 {nombre}", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#0f172a")
        self.lbl_user_name.pack(anchor=tk.E)

        self.lbl_user_role = tk.Label(user_info_frame, text=f"Rol: {role} ({self.user_data.get('email', '')})", font=("Segoe UI", 8), fg="#38bdf8", bg="#0f172a")
        self.lbl_user_role.pack(anchor=tk.E)

        # ---------------------------------------------------------
        # Contenedor Principal de Pestañas (Notebook)
        # ---------------------------------------------------------
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 1. Catálogo de Libros
        self.tab_catalog = CatalogTab(self.notebook)
        self.notebook.add(self.tab_catalog, text="  📚 Catálogo de Libros  ")

        # 2. Administración de Libros (CRUD y PUT vs PATCH)
        self.tab_admin = AdminBooksTab(self.notebook, on_catalog_changed=self.tab_catalog.load_books)
        self.notebook.add(self.tab_admin, text="  🛠️ Administración de Libros  ")

        # 3. Sesión y Perfil
        self.tab_profile = ProfileTab(self.notebook, on_logout_callback=self.on_logout_callback)
        self.notebook.add(self.tab_profile, text="  👤 Sesión y Perfil  ")

        # 4. Estado de los Servicios
        self.tab_health = HealthTab(self.notebook, on_status_updated=self._on_health_status_updated)
        self.notebook.add(self.tab_health, text="  🚦 Estado de los Servicios  ")

        # 5. Configuración del Servidor
        self.tab_settings = SettingsTab(self.notebook, on_settings_saved=self._on_settings_saved)
        self.notebook.add(self.tab_settings, text="  ⚙️ Configuración del Servidor  ")

    def _on_health_status_updated(self, auth_state, books_state):
        """Callback cuando el semáforo de salud actualiza estado."""
        # Se puede actualizar indicadores visuales adicionales en la cabecera si se desea
        pass

    def _on_settings_saved(self):
        """Callback cuando se guardan nuevas URLs de microservicios."""
        self.tab_health.check_all_services()
        self.tab_catalog.load_books()
        self.tab_admin.refresh_table()

    def _do_logout(self):
        confirm = messagebox.askyesno("Confirmar Salida", "¿Está seguro de que desea cerrar la sesión actual?")
        if confirm:
            session_manager.clear_session()
            self.on_logout_callback()
