"""
main.py
Punto de entrada de la aplicación de escritorio Python (apps/Python_app).
Ejecuta la verificación de persistencia local (session.json) y valida
contra el microservicio de autenticación antes de mostrar el panel principal.
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from session.session_manager import session_manager
from ui.auth_window import AuthWindow
from ui.main_window import MainWindow


class DesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Librería en Línea — Cliente de Escritorio")
        self.root.geometry("1100x720")

        # Configurar estilos ttk
        self._setup_styles()

        self.current_window = None

        # Ocultar root temporalmente mientras validamos sesión previa
        self.root.withdraw()

        # Iniciar verificación de sesión persistida
        self._check_initial_session()

    def _setup_styles(self):
        style = ttk.Style(self.root)
        available = style.theme_names()
        if "clam" in available:
            style.theme_use("clam")
        elif "vista" in available:
            style.theme_use("vista")

        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("TLabel", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24)

    def _check_initial_session(self):
        """
        Requisito 3 de la Rúbrica:
        Comprueba si existe sesión local previa en session.json y si sigue
        vigente en el servidor mediante GET /session.
        """
        valid, status, user_data = session_manager.validate_with_server()

        if valid and user_data:
            # Sesión activa: ir directamente al panel principal
            self.root.deiconify()
            self._show_main_window(user_data)
        else:
            # Sin sesión o sesión expirada: mostrar ventana de login
            self._show_auth_window(expired_warning=(status == "expired"))

    def _show_auth_window(self, expired_warning=False):
        """Muestra la ventana modal de autenticación (Login / Registro)."""
        if self.current_window:
            self.current_window.destroy()
            self.current_window = None

        self.root.withdraw()

        auth_win = AuthWindow(self.root, on_login_success=self._on_login_success)

        if expired_warning:
            messagebox.showwarning(
                "Sesión Expirada",
                "Su sesión previa ha expirado o ya no es válida en el servidor.\nPor favor ingrese sus credenciales nuevamente.",
                parent=auth_win
            )

        # Si el usuario cierra la ventana de login sin autenticarse, salir
        auth_win.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())

    def _on_login_success(self, user_data):
        """Callback invocado cuando el usuario se autentica exitosamente."""
        self.root.deiconify()
        self._show_main_window(user_data)

    def _show_main_window(self, user_data):
        """Construye y presenta el panel principal de la aplicación."""
        if self.current_window:
            self.current_window.destroy()

        self.current_window = MainWindow(
            self.root,
            user_data=user_data,
            on_logout_callback=self._on_logout
        )

    def _on_logout(self):
        """Callback cuando el usuario cierra sesión."""
        self._show_auth_window(expired_warning=False)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import traceback
    try:
        app = DesktopApp()
        app.run()
    except Exception as e:
        with open("crash.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
