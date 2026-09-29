import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading

class CatalogMgmtView(ttk.Frame):
    def __init__(self, master, api_client, **kwargs):
        super().__init__(master, **kwargs)
        self.api_client = api_client
        self.pack(fill=tk.BOTH, expand=True)
        self._build_ui()
        
    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tabs = {
            'authors': self._create_tab('authors', 'Autores'),
            'genres': self._create_tab('genres', 'Géneros'),
            'formats': self._create_tab('formats', 'Formatos'),
            'categories': self._create_tab('categories', 'Categorías')
        }
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        
    def _create_tab(self, table, title):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        entry = ttk.Entry(top_frame, width=30)
        entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(top_frame, text="Agregar", command=lambda: self._add(table, entry)).pack(side=tk.LEFT)
        
        tree = ttk.Treeview(frame, columns=("id", "name"), show='headings')
        tree.heading("id", text="ID")
        tree.column("id", width=50, stretch=tk.NO)
        tree.heading("name", text="Nombre")
        tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Eliminar", command=lambda: self._delete(table, tree)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Editar", command=lambda: self._edit(table, tree)).pack(side=tk.RIGHT, padx=5)
        
        return {'frame': frame, 'tree': tree, 'entry': entry, 'loaded': False}
        
    def _on_tab_change(self, event):
        tab_id = self.notebook.index(self.notebook.select())
        table = list(self.tabs.keys())[tab_id]
        if not self.tabs[table]['loaded']:
            self.load_data(table)
            
    def load_data(self, table):
        threading.Thread(target=self._load_thread, args=(table,), daemon=True).start()
        
    def _load_thread(self, table):
        try:
            res = self.api_client.get_catalog(table)
            self.after(0, self._update_tree, table, res.get('items', []))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Error al cargar {table}: {e}"))
            
    def _update_tree(self, table, items):
        tree = self.tabs[table]['tree']
        for item in tree.get_children():
            tree.delete(item)
        for i in items:
            tree.insert("", tk.END, iid=i['id'], values=(i['id'], i['name']))
        self.tabs[table]['loaded'] = True
        
    def _add(self, table, entry):
        name = entry.get().strip()
        if not name: return
        entry.delete(0, tk.END)
        threading.Thread(target=self._action_thread, args=(table, 'add', None, name), daemon=True).start()
        
    def _edit(self, table, tree):
        sel = tree.selection()
        if not sel: return
        item_id = sel[0]
        current_name = tree.item(item_id, 'values')[1]
        
        new_name = simpledialog.askstring("Editar", "Nuevo nombre:", initialvalue=current_name)
        if new_name and new_name.strip() != current_name:
            threading.Thread(target=self._action_thread, args=(table, 'edit', item_id, new_name.strip()), daemon=True).start()
            
    def _delete(self, table, tree):
        sel = tree.selection()
        if not sel: return
        item_id = sel[0]
        
        if messagebox.askyesno("Confirmar", "¿Seguro que desea eliminar este registro?"):
            threading.Thread(target=self._action_thread, args=(table, 'delete', item_id, None), daemon=True).start()
            
    def _action_thread(self, table, action, item_id, name):
        try:
            if action == 'add':
                self.api_client.create_catalog(table, name)
            elif action == 'edit':
                self.api_client.update_catalog(table, item_id, name)
            elif action == 'delete':
                self.api_client.delete_catalog(table, item_id)
            self.after(0, self.load_data, table)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Operación fallida: {e}"))
