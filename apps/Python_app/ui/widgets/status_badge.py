"""
ui/widgets/status_badge.py
Componente gráfico de semáforo de 3 estados (🟢 Verde, 🟡 Amarillo, 🔴 Rojo)
con indicador de nombre del servicio, estado y marca de tiempo.
"""
import tkinter as tk
from tkinter import ttk

# Colores del semáforo
COLOR_OK = "#22c55e"        # 🟢 Verde: Operativo y BD conectada
COLOR_DEGRADED = "#eab308"  # 🟡 Amarillo: Accesible pero BD degradada/desconectada
COLOR_ERROR = "#ef4444"     # 🔴 Rojo: Inaccesible, apagado o error de conexión
COLOR_UNKNOWN = "#9ca3af"   # Gris: Sin comprobar


class StatusBadge(ttk.Frame):
    def __init__(self, parent, service_name="Servicio"):
        super().__init__(parent)
        self.service_name = service_name

        # Contenedor horizontal
        self.canvas = tk.Canvas(self, width=18, height=18, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=(0, 6))

        # Círculo del semáforo
        self.circle = self.canvas.create_oval(2, 2, 16, 16, fill=COLOR_UNKNOWN, outline="#64748b", width=1)

        # Etiquetas de texto
        self.info_frame = ttk.Frame(self)
        self.info_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.title_label = ttk.Label(self.info_frame, text=self.service_name, font=("Segoe UI", 9, "bold"))
        self.title_label.pack(anchor=tk.W)

        self.status_label = ttk.Label(self.info_frame, text="Comprobando...", font=("Segoe UI", 8), foreground="#64748b")
        self.status_label.pack(anchor=tk.W)

    def set_status(self, state, detail_text=""):
        """
        Actualiza el estado visual del semáforo.
        state: 'ok' (verde), 'degraded' (amarillo), 'error' (rojo)
        """
        if state == "ok":
            color = COLOR_OK
            text = "🟢 En línea (BD OK)"
            outline = "#15803d"
        elif state == "degraded":
            color = COLOR_DEGRADED
            text = "🟡 Degradado (Sin BD)"
            outline = "#a16207"
        elif state == "error":
            color = COLOR_ERROR
            text = "🔴 Fuera de línea"
            outline = "#b91c1c"
        else:
            color = COLOR_UNKNOWN
            text = "⚪ Desconocido"
            outline = "#64748b"

        if detail_text:
            text = f"{text} — {detail_text}"

        self.canvas.itemconfig(self.circle, fill=color, outline=outline)
        self.status_label.config(text=text)
