"""
ui/auth_window.py
Pantallas de Autenticación (Iniciar Sesión y Registro con CAPTCHA).
Detecta credenciales inválidas (401), cuentas inactivas (403) y correos duplicados (409).
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.auth_service import auth_service
from session.session_manager import session_manager


class AuthWindow(tk.Toplevel):
    def __init__(self, root, on_login_success):
        super().__init__(root)
        self.root = root
        self.on_login_success = on_login_success

        self.title("Librería en Línea — Acceso al Sistema")
        self.geometry("460x580")
        self.resizable(False, False)

        # Centrar en pantalla
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (460 // 2)
        y = (self.winfo_screenheight() // 2) - (580 // 2)
        self.geometry(f"+{x}+{y}")

        self.captcha_id = None

        self._build_ui()

        # Forzar visibilidad al frente sobre otras aplicaciones
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

    def _build_ui(self):
        # Cabecera
        header = tk.Frame(self, bg="#1e293b", height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title = tk.Label(header, text="📚 Librería en Línea", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#1e293b")
        title.pack(pady=(12, 0))
        subtitle = tk.Label(header, text="Cliente Python para Microservicios REST", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b")
        subtitle.pack()

        # Cuaderno de pestañas (Login y Registro)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        self.tab_login = ttk.Frame(self.notebook, padding=15)
        self.tab_register = ttk.Frame(self.notebook, padding=15)

        self.notebook.add(self.tab_login, text="  Iniciar Sesión  ")
        self.notebook.add(self.tab_register, text="  Registrarse  ")

        self._build_login_tab()
        self._build_register_tab()

    # -------------------------------------------------------------
    # Pestaña de Inicio de Sesión
    # -------------------------------------------------------------
    def _build_login_tab(self):
        f = self.tab_login

        ttk.Label(f, text="Correo Electrónico:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 3))
        self.txt_login_email = ttk.Entry(f, width=40, font=("Segoe UI", 10))
        self.txt_login_email.pack(fill=tk.X, pady=(0, 10))
        self.txt_login_email.insert(0, "admin@libreria.local")

        ttk.Label(f, text="Contraseña:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(5, 3))
        self.txt_login_password = ttk.Entry(f, width=40, show="•", font=("Segoe UI", 10))
        self.txt_login_password.pack(fill=tk.X, pady=(0, 15))
        self.txt_login_password.insert(0, "Passw0rd!")

        # Mensaje de estado
        self.lbl_login_status = ttk.Label(f, text="", font=("Segoe UI", 9), foreground="#ef4444", wraplength=380)
        self.lbl_login_status.pack(pady=(0, 10))

        # Botón de Login
        self.btn_login = ttk.Button(f, text="🔑 Iniciar Sesión", command=self._handle_login)
        self.btn_login.pack(fill=tk.X, ipady=5, pady=(5, 10))

        ttk.Separator(f, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        hint = ttk.Label(
            f,
            text="💡 Credenciales de prueba cargadas:\n- Admin: admin@libreria.local / Passw0rd!\n- Usuario: usuario1@correo.com / Passw0rd!",
            font=("Segoe UI", 8),
            foreground="#64748b",
            justify=tk.LEFT
        )
        hint.pack(anchor=tk.W)

    def _handle_login(self):
        email = self.txt_login_email.get().strip()
        password = self.txt_login_password.get()

        if not email or not password:
            self.lbl_login_status.config(text="Por favor ingrese correo y contraseña.")
            return

        self.btn_login.config(state=tk.DISABLED)
        self.lbl_login_status.config(text="Autenticando con el microservicio...")

        def thread_task():
            res = auth_service.login(email, password)
            self.after(0, lambda: self._on_login_result(res))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_login_result(self, res):
        self.btn_login.config(state=tk.NORMAL)

        if res["success"]:
            user_data = res["data"].get("user", {})
            session_manager.save_session(user_data)
            self.destroy()
            self.on_login_success(user_data)
        else:
            code = res["status_code"]
            msg = res["error"]
            if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                msg = res["data"]["message"]

            if code == 401:
                self.lbl_login_status.config(text="❌ Credenciales incorrectas. Verifique correo y contraseña.")
            elif code == 403:
                self.lbl_login_status.config(text="⚠️ Cuenta inactiva: El correo no ha sido verificado aún.")
            elif code == 0 or code == 503:
                self.lbl_login_status.config(text="🔌 Microservicio de login fuera de línea o inaccesible.")
            else:
                self.lbl_login_status.config(text=f"Error ({code}): {msg}")

    # -------------------------------------------------------------
    # Pestaña de Registro
    # -------------------------------------------------------------
    def _build_register_tab(self):
        f = self.tab_register

        ttk.Label(f, text="Nombre(s):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_reg_nombre = ttk.Entry(f, width=40)
        self.txt_reg_nombre.pack(fill=tk.X, pady=(2, 6))

        row_ap = ttk.Frame(f)
        row_ap.pack(fill=tk.X, pady=(0, 6))
        col1 = ttk.Frame(row_ap)
        col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Label(col1, text="Apellido Paterno:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_reg_ap_pat = ttk.Entry(col1)
        self.txt_reg_ap_pat.pack(fill=tk.X, pady=(2, 0))

        col2 = ttk.Frame(row_ap)
        col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        ttk.Label(col2, text="Apellido Materno:", font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.txt_reg_ap_mat = ttk.Entry(col2)
        self.txt_reg_ap_mat.pack(fill=tk.X, pady=(2, 0))

        ttk.Label(f, text="Correo Electrónico:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_reg_email = ttk.Entry(f, width=40)
        self.txt_reg_email.pack(fill=tk.X, pady=(2, 6))

        ttk.Label(f, text="Contraseña (mínimo 8 caracteres):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.txt_reg_password = ttk.Entry(f, width=40, show="•")
        self.txt_reg_password.pack(fill=tk.X, pady=(2, 8))

        # Sección CAPTCHA
        captcha_frame = ttk.LabelFrame(f, text="Verificación Humana (CAPTCHA)", padding=8)
        captcha_frame.pack(fill=tk.X, pady=(0, 10))

        c_row = ttk.Frame(captcha_frame)
        c_row.pack(fill=tk.X)
        self.lbl_captcha_q = ttk.Label(c_row, text="Presione 'Generar Reto'", font=("Segoe UI", 9, "italic"), foreground="#0369a1")
        self.lbl_captcha_q.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_get_captcha = ttk.Button(c_row, text="🔄 Reto", command=self._load_captcha)
        self.btn_get_captcha.pack(side=tk.RIGHT)

        ttk.Label(captcha_frame, text="Respuesta al reto:").pack(anchor=tk.W, pady=(4, 2))
        self.txt_captcha_ans = ttk.Entry(captcha_frame, width=15)
        self.txt_captcha_ans.pack(anchor=tk.W)

        # Botón Registrar
        self.btn_register = ttk.Button(f, text="📝 Crear Cuenta", command=self._handle_register)
        self.btn_register.pack(fill=tk.X, ipady=4, pady=(5, 0))

        self.lbl_reg_status = ttk.Label(f, text="", font=("Segoe UI", 8), foreground="#ef4444", wraplength=380)
        self.lbl_reg_status.pack(pady=(4, 0))

    def _load_captcha(self):
        self.btn_get_captcha.config(state=tk.DISABLED)
        self.lbl_captcha_q.config(text="Obteniendo reto...")

        def thread_task():
            res = auth_service.get_captcha()
            self.after(0, lambda: self._on_captcha_result(res))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_captcha_result(self, res):
        self.btn_get_captcha.config(state=tk.NORMAL)
        if res["success"]:
            data = res["data"]
            self.captcha_id = data.get("captcha_id")
            challenge = data.get("challenge", "Resuelva la suma")
            self.lbl_captcha_q.config(text=f"❓ {challenge}", foreground="#0f172a")
        else:
            self.lbl_captcha_q.config(text="Error al obtener CAPTCHA", foreground="#ef4444")

    def _handle_register(self):
        nombre = self.txt_reg_nombre.get().strip()
        ap_pat = self.txt_reg_ap_pat.get().strip()
        ap_mat = self.txt_reg_ap_mat.get().strip()
        email = self.txt_reg_email.get().strip()
        pwd = self.txt_reg_password.get()
        ans = self.txt_captcha_ans.get().strip()

        if not nombre or not ap_pat or not email or not pwd:
            self.lbl_reg_status.config(text="Complete todos los campos obligatorios.")
            return

        if len(pwd) < 8:
            self.lbl_reg_status.config(text="La contraseña debe tener al menos 8 caracteres.")
            return

        self.btn_register.config(state=tk.DISABLED)
        self.lbl_reg_status.config(text="Registrando usuario en PostgreSQL...")

        def thread_task():
            res = auth_service.register(
                nombre=nombre,
                apellido_paterno=ap_pat,
                apellido_materno=ap_mat,
                email=email,
                password=pwd,
                captcha_id=self.captcha_id,
                captcha_answer=ans
            )
            self.after(0, lambda: self._on_register_result(res))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_register_result(self, res):
        self.btn_register.config(state=tk.NORMAL)
        if res["success"]:
            msg = res["data"].get("message", "Usuario registrado exitosamente.")
            messagebox.showinfo("Registro Exitoso", f"{msg}\n\nPuede iniciar sesión con sus credenciales.")
            self.notebook.select(self.tab_login)
            self.txt_login_email.delete(0, tk.END)
            self.txt_login_email.insert(0, self.txt_reg_email.get().strip())
            self.txt_login_password.delete(0, tk.END)
        else:
            code = res["status_code"]
            msg = res["error"] or ""
            if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                msg = res["data"]["message"]

            if code == 409:
                self.lbl_reg_status.config(text="⚠️ El correo ya está registrado en el sistema.")
            else:
                self.lbl_reg_status.config(text=f"Error ({code}): {msg}")
            # Recargar captcha si falló
            self._load_captcha()
