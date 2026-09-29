import tkinter as tk
from tkinter import ttk, messagebox
import threading

class UsersView(ttk.Frame):
    def __init__(self, master, api_client, **kwargs):
        super().__init__(master, **kwargs)
        self.api_client = api_client
        self.pack(fill=tk.BOTH, expand=True)
        self._build_ui()
        self.load_data()
        
    def _build_ui(self):
        ttk.Label(self, text="Usuarios del Sistema", font=('Helvetica', 14, 'bold')).pack(pady=10, anchor=tk.W, padx=10)
        
        cols = ("id", "username", "email", "rol", "nombre", "fecha")
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=50, stretch=tk.NO)
        self.tree.heading("username", text="Username")
        self.tree.heading("email", text="Email")
        self.tree.heading("rol", text="Rol")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("fecha", text="Fecha Registro")
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
    def load_data(self):
        threading.Thread(target=self._load_thread, daemon=True).start()
        
    def _load_thread(self):
        try:
            res = self.api_client.get_users()
            self.after(0, self._update_ui, res.get('items', []))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error al cargar usuarios: {e}"))
            
    def _update_ui(self, users):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for u in users:
            nombre_completo = f"{u.get('nombre', '')} {u.get('apellido_paterno', '')} {u.get('apellido_materno', '')}".strip()
            self.tree.insert("", tk.END, iid=u.get('id'), values=(
                u.get('id'), u.get('username'), u.get('email'), 
                u.get('rol', {}).get('nombre', ''), nombre_completo, 
                u.get('fecha_registro', '')
            ))
