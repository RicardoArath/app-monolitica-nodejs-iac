"""
ui/tabs/profile_tab.py
Pestaña de Perfil de Usuario y Gestión de Sesión.
Permite:
- Consultar información de la sesión activa (GET /profile y GET /session)
- Modificar nombre, apellidos, correo y contraseña mediante PATCH /profile
- Comprobar tiempo restante de sesión
- Extender la sesión mediante POST /session/extend
- Cerrar sesión mediante POST /logout
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.auth_service import auth_service
from session.session_manager import session_manager


class ProfileTab(ttk.Frame):
    def __init__(self, parent, on_logout_callback):
        super().__init__(parent, padding=15)
        self.on_logout_callback = on_logout_callback

        self._build_ui()
        self.load_profile_data()

    def _build_ui(self):
        # ---------------------------------------------------------
        # Información de la Sesión y Tiempo de Vida
        # ---------------------------------------------------------
        session_box = ttk.LabelFrame(self, text="⏱️ Estado de la Sesión Activa", padding=12)
        session_box.pack(fill=tk.X, pady=(0, 15))

        top_s_row = ttk.Frame(session_box)
        top_s_row.pack(fill=tk.X)

        self.lbl_session_status = ttk.Label(top_s_row, text="Estado: Consultando...", font=("Segoe UI", 10, "bold"), foreground="#0284c7")
        self.lbl_session_status.pack(side=tk.LEFT)

        self.btn_extend = ttk.Button(top_s_row, text="⏳ Extender Sesión (POST /session/extend)", command=self._handle_extend_session)
        self.btn_extend.pack(side=tk.RIGHT)

        self.lbl_remaining = ttk.Label(session_box, text="Tiempo restante: Calculando...", font=("Segoe UI", 9), foreground="#64748b")
        self.lbl_remaining.pack(anchor=tk.W, pady=(4, 0))

        # ---------------------------------------------------------
        # Formulario de Edición de Perfil (PATCH /profile)
        # ---------------------------------------------------------
        profile_box = ttk.LabelFrame(self, text="👤 Información del Perfil (PATCH /profile)", padding=15)
        profile_box.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Metadatos no editables
        r_info = ttk.Frame(profile_box)
        r_info.pack(fill=tk.X, pady=(0, 10))

        self.lbl_user_id = ttk.Label(r_info, text="ID de Usuario: -", font=("Segoe UI", 9, "bold"))
        self.lbl_user_id.pack(side=tk.LEFT, padx=(0, 25))

        self.lbl_username = ttk.Label(r_info, text="Usuario: -", font=("Segoe UI", 9, "bold"))
        self.lbl_username.pack(side=tk.LEFT, padx=(0, 25))

        self.lbl_role = ttk.Label(r_info, text="Rol: -", font=("Segoe UI", 9, "bold"), foreground="#0369a1")
        self.lbl_role.pack(side=tk.LEFT)

        ttk.Separator(profile_box, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # Campos editables
        ttk.Label(profile_box, text="Nombre:").pack(anchor=tk.W, pady=(4, 2))
        self.txt_nombre = ttk.Entry(profile_box, width=45)
        self.txt_nombre.pack(fill=tk.X)

        row_ap = ttk.Frame(profile_box)
        row_ap.pack(fill=tk.X, pady=(6, 0))

        c1 = ttk.Frame(row_ap)
        c1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Label(c1, text="Apellido Paterno:").pack(anchor=tk.W)
        self.txt_ap_pat = ttk.Entry(c1)
        self.txt_ap_pat.pack(fill=tk.X)

        c2 = ttk.Frame(row_ap)
        c2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Label(c2, text="Apellido Materno:").pack(anchor=tk.W)
        self.txt_ap_mat = ttk.Entry(c2)
        self.txt_ap_mat.pack(fill=tk.X)

        ttk.Label(profile_box, text="Correo Electrónico:").pack(anchor=tk.W, pady=(8, 2))
        self.txt_email = ttk.Entry(profile_box, width=45)
        self.txt_email.pack(fill=tk.X)

        ttk.Label(profile_box, text="Nueva Contraseña (dejar en blanco si no desea cambiarla):").pack(anchor=tk.W, pady=(8, 2))
        self.txt_new_pwd = ttk.Entry(profile_box, width=45, show="•")
        self.txt_new_pwd.pack(fill=tk.X)

        # Botón Guardar Cambios
        self.btn_save_profile = ttk.Button(profile_box, text="💾 Guardar Cambios (PATCH /profile)", command=self._handle_save_profile)
        self.btn_save_profile.pack(fill=tk.X, ipady=4, pady=(15, 0))

        # ---------------------------------------------------------
        # Botón de Cerrar Sesión
        # ---------------------------------------------------------
        bot_frame = ttk.Frame(self)
        bot_frame.pack(fill=tk.X)

        self.btn_logout = ttk.Button(bot_frame, text="🚪 Cerrar Sesión (POST /logout)", command=self._handle_logout)
        self.btn_logout.pack(side=tk.RIGHT)

    def load_profile_data(self):
        """Carga el perfil y estado de sesión en segundo plano."""
        def thread_task():
            res_prof = auth_service.get_profile()
            res_sess = auth_service.get_session()
            self.after(0, lambda: self._on_profile_loaded(res_prof, res_sess))

        threading.Thread(target=thread_task, daemon=True).start()

    def _on_profile_loaded(self, res_prof, res_sess):
        if res_prof["success"]:
            u = res_prof["data"].get("user", {})
            self.lbl_user_id.config(text=f"ID de Usuario: {u.get('id')}")
            self.lbl_username.config(text=f"Usuario: {u.get('username')}")
            self.lbl_role.config(text=f"Rol: {u.get('role', 'user').upper()}")

            self.txt_nombre.delete(0, tk.END)
            self.txt_nombre.insert(0, u.get("nombre") or "")

            self.txt_ap_pat.delete(0, tk.END)
            self.txt_ap_pat.insert(0, u.get("apellido_paterno") or "")

            self.txt_ap_mat.delete(0, tk.END)
            self.txt_ap_mat.insert(0, u.get("apellido_materno") or "")

            self.txt_email.delete(0, tk.END)
            self.txt_email.insert(0, u.get("email") or "")

        if res_sess["success"]:
            s_data = res_sess["data"] or {}
            status = s_data.get("status", "active")
            remaining = s_data.get("remaining_seconds", 0)
            mins = remaining // 60
            secs = remaining % 60

            if status == "expiring":
                self.lbl_session_status.config(text="⚠️ Sesión próxima a expirar", foreground="#eab308")
                self.lbl_remaining.config(text=f"Quedan {mins}m {secs}s. Presione 'Extender Sesión' para continuar activo.", foreground="#b45309")
            else:
                self.lbl_session_status.config(text="🟢 Sesión Activa", foreground="#16a34a")
                self.lbl_remaining.config(text=f"Tiempo restante antes de inactividad: {mins} minutos y {secs} segundos.", foreground="#64748b")
        else:
            self.lbl_session_status.config(text="🔴 No se pudo consultar la sesión", foreground="#ef4444")

    def _handle_save_profile(self):
        nombre = self.txt_nombre.get().strip()
        ap_pat = self.txt_ap_pat.get().strip()
        ap_mat = self.txt_ap_mat.get().strip()
        email = self.txt_email.get().strip()
        new_pwd = self.txt_new_pwd.get()

        if not email:
            messagebox.showerror("Error", "El correo electrónico no puede estar vacío.")
            return

        payload = {
            "nombre": nombre,
            "apellido_paterno": ap_pat,
            "apellido_materno": ap_mat,
            "email": email
        }
        if new_pwd:
            if len(new_pwd) < 8:
                messagebox.showerror("Error", "La nueva contraseña debe tener al menos 8 caracteres.")
                return
            payload["password"] = new_pwd

        self.btn_save_profile.config(state=tk.DISABLED)

        def thread_task():
            res = auth_service.patch_profile(payload)
            self.after(0, lambda: on_saved(res))

        def on_saved(res):
            self.btn_save_profile.config(state=tk.NORMAL)
            if res["success"]:
                updated_user = res["data"].get("user", {})
                session_manager.user = updated_user
                messagebox.showinfo("Perfil Actualizado", "Los cambios han sido guardados correctamente en el servidor mediante PATCH /profile.")
                self.txt_new_pwd.delete(0, tk.END)
                self.load_profile_data()
            else:
                msg = res["error"] or "Error al actualizar perfil."
                if res["data"] and isinstance(res["data"], dict) and "message" in res["data"]:
                    msg = res["data"]["message"]
                messagebox.showerror(f"Error ({res['status_code']})", msg)

        threading.Thread(target=thread_task, daemon=True).start()

    def _handle_extend_session(self):
        def thread_task():
            res = auth_service.extend_session()
            self.after(0, lambda: on_extended(res))

        def on_extended(res):
            if res["success"]:
                messagebox.showinfo("Sesión Extendida", "La sesión fue renovada exitosamente por 30 minutos más (POST /session/extend).")
                self.load_profile_data()
            else:
                messagebox.showwarning("Aviso", "No se pudo extender la sesión.")

        threading.Thread(target=thread_task, daemon=True).start()

    def _handle_logout(self):
        confirm = messagebox.askyesno("Cerrar Sesión", "¿Desea cerrar la sesión actual?")
        if not confirm:
            return

        def thread_task():
            auth_service.logout()
            session_manager.clear_session()
            self.after(0, self.on_logout_callback)

        threading.Thread(target=thread_task, daemon=True).start()
