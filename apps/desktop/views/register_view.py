import tkinter as tk
from tkinter import ttk, messagebox
import threading

class RegisterView(ttk.Frame):
    def __init__(self, master, auth_client, on_goto_login, **kwargs):
        super().__init__(master, **kwargs)
        self.auth_client = auth_client
        self.on_goto_login = on_goto_login
        self.captcha_id = None
        
        self.pack(fill=tk.BOTH, expand=True)
        self._build_ui()
        self._get_captcha()
        
    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        ttk.Label(container, text="Registro", font=('Helvetica', 16, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        fields = [
            ("Nombre:", "nombre"),
            ("Apellido Paterno:", "ap_pat"),
            ("Apellido Materno:", "ap_mat"),
            ("Email:", "email"),
            ("Contraseña:", "password", True),
            ("Confirmar Contraseña:", "confirm", True)
        ]
        
        self.entries = {}
        for i, f in enumerate(fields):
            row = i + 1
            ttk.Label(container, text=f[0]).grid(row=row, column=0, sticky=tk.W, pady=2)
            show = "*" if len(f) > 2 else ""
            ent = ttk.Entry(container, width=30, show=show)
            ent.grid(row=row, column=1, pady=2)
            self.entries[f[1]] = ent
            
        captcha_frame = ttk.Frame(container)
        captcha_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)
        
        self.captcha_text = ttk.Label(captcha_frame, text="Cargando CAPTCHA...", font=('Courier', 12, 'bold'), foreground="blue")
        self.captcha_text.grid(row=0, column=0, padx=5)
        
        ttk.Button(captcha_frame, text="Obtener CAPTCHA", command=self._get_captcha).grid(row=0, column=1, padx=5)
        
        ttk.Label(container, text="Respuesta CAPTCHA:").grid(row=len(fields)+2, column=0, sticky=tk.W, pady=2)
        self.captcha_entry = ttk.Entry(container, width=30)
        self.captcha_entry.grid(row=len(fields)+2, column=1, pady=2)
        
        self.error_label = ttk.Label(container, text="", foreground="red")
        self.error_label.grid(row=len(fields)+3, column=0, columnspan=2, pady=5)
        
        self.reg_btn = ttk.Button(container, text="Registrarse", command=self._do_register)
        self.reg_btn.grid(row=len(fields)+4, column=0, columnspan=2, pady=5)
        
        log_link = ttk.Label(container, text="¿Ya tienes cuenta? Inicia sesión", foreground="blue", cursor="hand2")
        log_link.grid(row=len(fields)+5, column=0, columnspan=2, pady=5)
        log_link.bind("<Button-1>", lambda e: self.on_goto_login())
        
    def _get_captcha(self):
        self.captcha_text.config(text="Cargando...")
        threading.Thread(target=self._captcha_thread, daemon=True).start()
        
    def _captcha_thread(self):
        try:
            res = self.auth_client.get_captcha()
            self.after(0, self._set_captcha, res)
        except:
            self.after(0, lambda: self.captcha_text.config(text="Error CAPTCHA"))
            
    def _set_captcha(self, res):
        self.captcha_id = res.get('id')
        self.captcha_text.config(text=res.get('challenge', ''))
        
    def _do_register(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        ans = self.captcha_entry.get().strip()
        
        if not all(data.values()) or not ans:
            self.error_label.config(text="Todos los campos son requeridos")
            return
            
        if data["password"] != data["confirm"]:
            self.error_label.config(text="Las contraseñas no coinciden")
            return
            
        if not self.captcha_id:
            self.error_label.config(text="Por favor obtenga un CAPTCHA")
            return
            
        self.error_label.config(text="")
        self.reg_btn.config(state=tk.DISABLED)
        
        threading.Thread(target=self._reg_thread, args=(data, ans), daemon=True).start()
        
    def _reg_thread(self, data, ans):
        try:
            self.auth_client.register(
                data["nombre"], data["ap_pat"], data["ap_mat"], 
                data["email"], data["password"], 
                self.captcha_id, ans
            )
            self.after(0, self._handle_success)
        except Exception as e:
            self.after(0, self._handle_error, str(e))
            
    def _handle_success(self):
        messagebox.showinfo("Registro Exitoso", "Revisa tu correo para validar la cuenta.")
        self.on_goto_login()
        
    def _handle_error(self, err):
        self.reg_btn.config(state=tk.NORMAL)
        self.error_label.config(text="Error al registrar. Verifique datos y CAPTCHA.")
