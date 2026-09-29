import tkinter as tk
from tkinter import ttk
import threading
from config import HEALTH_POLL_INTERVAL

class HealthIndicator(ttk.Frame):
    def __init__(self, master, auth_client, api_client, **kwargs):
        super().__init__(master, **kwargs)
        self.auth_client = auth_client
        self.api_client = api_client

        self.auth_label = ttk.Label(self, text="Auth")
        self.auth_label.pack(side=tk.LEFT, padx=(0, 2))
        self.auth_canvas = tk.Canvas(self, width=12, height=12, highlightthickness=0)
        self.auth_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self.auth_circle = self.auth_canvas.create_oval(1, 1, 11, 11, fill="#9ca3af")

        self.api_label = ttk.Label(self, text="API")
        self.api_label.pack(side=tk.LEFT, padx=(0, 2))
        self.api_canvas = tk.Canvas(self, width=12, height=12, highlightthickness=0)
        self.api_canvas.pack(side=tk.LEFT)
        self.api_circle = self.api_canvas.create_oval(1, 1, 11, 11, fill="#9ca3af")

    def update_status(self, auth_ok, api_ok):
        self.auth_canvas.itemconfig(self.auth_circle, fill="#22c55e" if auth_ok else "#ef4444")
        self.api_canvas.itemconfig(self.api_circle, fill="#22c55e" if api_ok else "#ef4444")

    def _poll(self):
        auth_ok = self.auth_client.health()
        api_ok = self.api_client.health()
        self.after(0, self.update_status, auth_ok, api_ok)
        self.after(HEALTH_POLL_INTERVAL, self._start_thread)

    def _start_thread(self):
        threading.Thread(target=self._poll, daemon=True).start()

    def start_polling(self):
        self._start_thread()
