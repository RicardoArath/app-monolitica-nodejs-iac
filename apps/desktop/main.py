import tkinter as tk
from tkinter import ttk, messagebox
import threading

from config import HEALTH_POLL_INTERVAL
from api_client import AuthClient, ApiClient
import session_store

from views.login_view import LoginView
from views.register_view import RegisterView
from views.catalog_view import CatalogView
from views.book_detail_view import BookDetailView
from views.book_form_view import BookFormView
from views.catalog_mgmt_view import CatalogMgmtView
from views.users_view import UsersView

from widgets.health_indicator import HealthIndicator

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Librería en Línea — Escritorio")
        self.geometry("1100x700")
        
        style = ttk.Style(self)
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        elif 'clam' in style.theme_names():
            style.theme_use('clam')
            
        self.auth_client = AuthClient()
        self.api_client = ApiClient(self.auth_client)
        self.user_data = None
        
        self.current_view = None
        
        self._build_menu()
        
        # Header frame for health indicator
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        
        self.health_ind = HealthIndicator(self.header_frame, self.auth_client, self.api_client)
        self.health_ind.pack(side=tk.RIGHT, padx=10, pady=5)
        self.health_ind.start_polling()
        
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self._init_session()
        
    def _build_menu(self):
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)
        
        self.catalog_menu = tk.Menu(self.menubar, tearoff=0)
        self.catalog_menu.add_command(label="Ver Catálogo", command=self.show_catalog)
        self.menubar.add_cascade(label="Catálogo", menu=self.catalog_menu)
        
        self.admin_menu = tk.Menu(self.menubar, tearoff=0)
        self.admin_menu.add_command(label="Libros", command=self.show_catalog)
        self.admin_menu.add_command(label="Autores/Géneros/Formatos/Categorías", command=self.show_catalog_mgmt)
        self.admin_menu.add_command(label="Usuarios", command=self.show_users)
        self.menubar.add_cascade(label="Administrar", menu=self.admin_menu)
        
        self.session_menu = tk.Menu(self.menubar, tearoff=0)
        self.session_menu.add_command(label="Cerrar Sesión", command=self.logout)
        self.menubar.add_cascade(label="Sesión", menu=self.session_menu)
        
        self._set_menu_state(tk.DISABLED)
        
    def _set_menu_state(self, state):
        self.menubar.entryconfig("Catálogo", state=state)
        self.menubar.entryconfig("Administrar", state=state)
        self.menubar.entryconfig("Sesión", state=state)
        
    def _init_session(self):
        user_data, cookies = session_store.load_session()
        if user_data and cookies:
            self.auth_client.set_cookies_dict(cookies)
            threading.Thread(target=self._check_session_thread, daemon=True).start()
        else:
            self.show_login()
            
    def _check_session_thread(self):
        try:
            res = self.auth_client.check_session()
            self.after(0, self._handle_session_valid, res)
        except Exception:
            self.after(0, self.show_login)
            
    def _handle_session_valid(self, res):
        self.user_data = session_store.load_session()[0]
        self.session_menu.entryconfig(0, label=f"Usuario: {self.user_data.get('username', '')}")
        self._set_menu_state(tk.NORMAL)
        self.show_catalog()
        
    def _switch_view(self, view_class, *args, **kwargs):
        if self.current_view:
            self.current_view.destroy()
        self.current_view = view_class(self.content_frame, *args, **kwargs)
        
    def show_login(self):
        self._set_menu_state(tk.DISABLED)
        self._switch_view(LoginView, self.auth_client, self.on_login_success, self.show_register)
        
    def show_register(self):
        self._set_menu_state(tk.DISABLED)
        self._switch_view(RegisterView, self.auth_client, self.show_login)
        
    def on_login_success(self, user_data):
        self.user_data = user_data
        self.session_menu.entryconfig(0, label=f"Usuario: {self.user_data.get('username', '')}")
        self._set_menu_state(tk.NORMAL)
        self.show_catalog()
        
    def logout(self):
        threading.Thread(target=self._logout_thread, daemon=True).start()
        
    def _logout_thread(self):
        try:
            self.auth_client.logout()
        except:
            pass
        self.after(0, self._handle_logout)
        
    def _handle_logout(self):
        session_store.clear_session()
        self.user_data = None
        self.show_login()
        
    def show_catalog(self):
        self._switch_view(CatalogView, self.api_client, self.open_book_form, self.open_book_detail)
        
    def show_catalog_mgmt(self):
        self._switch_view(CatalogMgmtView, self.api_client)
        
    def show_users(self):
        self._switch_view(UsersView, self.api_client)
        
    def open_book_detail(self, book_id):
        BookDetailView(self, self.api_client, book_id, self.open_book_form, on_close_callback=self._refresh_catalog)
        
    def open_book_form(self, book_id=None):
        BookFormView(self, self.api_client, book_id, on_success_callback=self._refresh_catalog)
        
    def _refresh_catalog(self):
        if isinstance(self.current_view, CatalogView):
            self.current_view.load_data()

if __name__ == "__main__":
    app = App()
    app.mainloop()
