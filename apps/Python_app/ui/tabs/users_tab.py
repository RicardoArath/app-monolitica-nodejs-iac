"""
ui/tabs/users_tab.py
Pestaña de Gestión de Usuarios y Roles (Microservicio Users :5004).
Exclusiva para Administradores.
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from network.users_service import users_service
from session.session_manager import session_manager


class UsersTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=12)
        self.users = []
        self._build_ui()
        self.load_users()

    def _build_ui(self):
        # Barra Superior
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        lbl_title = ttk.Label(top_bar, text="👥 Administración de Usuarios y Roles", font=("Segoe UI", 11, "bold"))
        lbl_title.pack(side=tk.LEFT)

        self.btn_refresh = ttk.Button(top_bar, text="🔄 Recargar", command=self.load_users)
        self.btn_refresh.pack(side=tk.RIGHT, padx=4)

        self.btn_create = ttk.Button(top_bar, text="➕ Nuevo Usuario", command=self._show_create_dialog)
        self.btn_create.pack(side=tk.RIGHT, padx=4)

        # Tabla de Usuarios
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "username", "email", "role", "nombre", "apellido", "verified")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("username", text="Usuario")
        self.tree.heading("email", text="Email")
        self.tree.heading("role", text="Rol")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("apellido", text="Apellido Paterno")
        self.tree.heading("verified", text="Verificado")

        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("username", width=120)
        self.tree.column("email", width=180)
        self.tree.column("role", width=80, anchor=tk.CENTER)
        self.tree.column("nombre", width=130)
        self.tree.column("apellido", width=130)
        self.tree.column("verified", width=80, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Barra de Acciones Inferior
        bottom_bar = ttk.Frame(self)
        bottom_bar.pack(fill=tk.X, pady=(10, 0))

        self.btn_edit = ttk.Button(bottom_bar, text="✏️ Cambiar Rol / Datos", command=self._show_edit_dialog)
        self.btn_edit.pack(side=tk.LEFT, padx=4)

        self.btn_delete = ttk.Button(bottom_bar, text="🗑️ Eliminar Usuario", command=self._delete_user)
        self.btn_delete.pack(side=tk.LEFT, padx=4)

        self.lbl_status = ttk.Label(bottom_bar, text="", foreground="#64748b")
        self.lbl_status.pack(side=tk.RIGHT)

    def load_users(self):
        """Carga la lista de usuarios en un hilo secundario."""
        self.lbl_status.config(text="Cargando usuarios...")
        threading.Thread(target=self._fetch_users, daemon=True).start()

    def _fetch_users(self):
        res = users_service.list_users()
        self.after(0, lambda: self._render_users(res))

    def _render_users(self, res):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not res["success"]:
            err = res.get("error") or "Error al consultar usuarios (¿Tiene rol admin?)"
            self.lbl_status.config(text=f"Error: {err}", foreground="#ef4444")
            return

        data = res.get("data") or {}
        self.users = data.get("users", [])
        for u in self.users:
            self.tree.insert("", tk.END, values=(
                u.get("id"),
                u.get("username"),
                u.get("email"),
                (u.get("role") or "").upper(),
                u.get("nombre") or "",
                u.get("apellido_paterno") or "",
                "✓" if u.get("email_verified") else "✗"
            ))

        self.lbl_status.config(text=f"Total: {len(self.users)} usuarios", foreground="#15803d")

    def _get_selected_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un usuario de la lista.")
            return None
        item = self.tree.item(sel[0])
        user_id = item["values"][0]
        for u in self.users:
            if u["id"] == user_id:
                return u
        return None

    def _show_create_dialog(self):
        win = tk.Toplevel(self)
        win.title("Nuevo Usuario")
        win.geometry("380x380")
        win.resizable(False, False)

        ttk.Label(win, text="Nombre:").pack(anchor=tk.W, padx=20, pady=(15, 2))
        e_nom = ttk.Entry(win)
        e_nom.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Apellido Paterno:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        e_pat = ttk.Entry(win)
        e_pat.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Usuario:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        e_user = ttk.Entry(win)
        e_user.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Email:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        e_mail = ttk.Entry(win)
        e_mail.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Contraseña:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        e_pass = ttk.Entry(win, show="*")
        e_pass.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Rol:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        c_role = ttk.Combobox(win, values=["user", "admin"], state="readonly")
        c_role.set("user")
        c_role.pack(fill=tk.X, padx=20)

        def save():
            payload = {
                "nombre": e_nom.get().strip(),
                "apellido_paterno": e_pat.get().strip(),
                "username": e_user.get().strip(),
                "email": e_mail.get().strip(),
                "password": e_pass.get(),
                "role": c_role.get()
            }
            if not payload["username"] or not payload["email"] or not payload["password"]:
                messagebox.showerror("Error", "Todos los campos principales son obligatorios.")
                return

            res = users_service.create_user(payload)
            if res["success"]:
                messagebox.showinfo("Éxito", "Usuario creado correctamente.")
                win.destroy()
                self.load_users()
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo crear el usuario.")

        ttk.Button(win, text="Guardar Usuario", command=save).pack(pady=20)

    def _show_edit_dialog(self):
        user = self._get_selected_user()
        if not user:
            return

        win = tk.Toplevel(self)
        win.title(f"Editar Usuario #{user['id']} — {user['username']}")
        win.geometry("360x300")
        win.resizable(False, False)

        ttk.Label(win, text="Nombre:").pack(anchor=tk.W, padx=20, pady=(15, 2))
        e_nom = ttk.Entry(win)
        e_nom.insert(0, user.get("nombre") or "")
        e_nom.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Apellido Paterno:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        e_pat = ttk.Entry(win)
        e_pat.insert(0, user.get("apellido_paterno") or "")
        e_pat.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Email:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        e_mail = ttk.Entry(win)
        e_mail.insert(0, user.get("email") or "")
        e_mail.pack(fill=tk.X, padx=20)

        ttk.Label(win, text="Rol:").pack(anchor=tk.W, padx=20, pady=(8, 2))
        c_role = ttk.Combobox(win, values=["user", "admin"], state="readonly")
        c_role.set(user.get("role", "user").lower())
        c_role.pack(fill=tk.X, padx=20)

        def save():
            payload = {
                "nombre": e_nom.get().strip(),
                "apellido_paterno": e_pat.get().strip(),
                "email": e_mail.get().strip(),
                "role": c_role.get()
            }
            res = users_service.update_user(user["id"], payload)
            if res["success"]:
                messagebox.showinfo("Éxito", "Usuario actualizado (sesión revocada si cambió el rol).")
                win.destroy()
                self.load_users()
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo actualizar.")

        ttk.Button(win, text="Guardar Cambios", command=save).pack(pady=20)

    def _delete_user(self):
        user = self._get_selected_user()
        if not user:
            return

        confirm = messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Desea eliminar al usuario '{user['username']}' (ID {user['id']})?\n"
            "Se invalidarán inmediatamente todas sus sesiones activas en Redis."
        )
        if confirm:
            res = users_service.delete_user(user["id"])
            if res["success"]:
                messagebox.showinfo("Éxito", "Usuario eliminado exitosamente.")
                self.load_users()
            else:
                messagebox.showerror("Error", res.get("error") or "No se pudo eliminar el usuario.")
