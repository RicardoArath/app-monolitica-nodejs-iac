import tkinter as tk
from tkinter import ttk
import threading
import session_store

class LoginView(ttk.Frame):
    def __init__(self, master, auth_client, on_login_success, on_goto_register, **kwargs):
        super().__init__(master, **kwargs)
        self.auth_client = auth_client
        self.on_login_success = on_login_success
        self.on_goto_register = on_goto_register
        
        self.pack(fill=tk.BOTH, expand=True)
        self._build_ui()
        
    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        ttk.Label(container, text="Librería en Línea — Iniciar Sesión", font=('Helvetica', 16, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        ttk.Label(container, text="Email:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.email_entry = ttk.Entry(container, width=30)
        self.email_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(container, text="Contraseña:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(container, width=30, show="*")
        self.password_entry.grid(row=2, column=1, pady=5)
        
        self.error_label = ttk.Label(container, text="", foreground="red")
        self.error_label.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.login_btn = ttk.Button(container, text="Iniciar Sesión", command=self._do_login)
        self.login_btn.grid(row=4, column=0, columnspan=2, pady=(10, 5))
        
        reg_link = ttk.Label(container, text="¿No tienes cuenta? Regístrate", foreground="blue", cursor="hand2")
        reg_link.grid(row=5, column=0, columnspan=2, pady=5)
        reg_link.bind("<Button-1>", lambda e: self.on_goto_register())
        
    def _do_login(self):
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        if not email or not password:
            self.error_label.config(text="Por favor ingrese email y contraseña")
            return
            
        self.error_label.config(text="")
        self.login_btn.config(state=tk.DISABLED)
        
        threading.Thread(target=self._login_thread, args=(email, password), daemon=True).start()
        
    def _login_thread(self, email, password):
        try:
            user_data = self.auth_client.login(email, password)
            self.after(0, self._handle_success, user_data)
        except Exception as e:
            self.after(0, self._handle_error, str(e))
            
    def _handle_success(self, user_data):
        cookies = self.auth_client.get_cookies_dict()
        session_store.save_session(user_data, cookies)
        self.on_login_success(user_data)
        
    def _handle_error(self, err_msg):
        self.login_btn.config(state=tk.NORMAL)
        self.error_label.config(text="Error de inicio de sesión. Verifique sus credenciales.")
