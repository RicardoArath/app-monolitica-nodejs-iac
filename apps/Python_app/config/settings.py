"""
config/settings.py
Gestión de configuración y persistencia de URLs de microservicios en config.json.
Permite alternar entre el entorno Local (localhost) y Remoto (GCP 35.193.230.144).
"""
import os
import json

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Valores predeterminados para entorno local y remoto
DEFAULT_LOCAL_AUTH = "http://localhost:5000"
DEFAULT_LOCAL_BOOKS = "http://localhost:5001"

DEFAULT_REMOTE_AUTH = "http://34.171.172.238:5000"
DEFAULT_REMOTE_BOOKS = "http://34.171.172.238:5001"


class Settings:
    def __init__(self):
        # Por defecto inicializa apuntando a la nube GCP
        self.auth_url = DEFAULT_REMOTE_AUTH
        self.books_url = DEFAULT_REMOTE_BOOKS
        self.load()

    def load(self):
        """Carga la configuración guardada desde config.json si existe."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.auth_url = data.get("auth_url", self.auth_url).rstrip("/")
                    self.books_url = data.get("books_url", self.books_url).rstrip("/")
            except Exception as e:
                print(f"Error al leer config.json: {e}")

    def save(self):
        """Guarda la configuración actual en config.json."""
        data = {
            "auth_url": self.auth_url.rstrip("/"),
            "books_url": self.books_url.rstrip("/")
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error al guardar config.json: {e}")
            return False

    def set_local(self):
        """Configura los endpoints al entorno local."""
        self.auth_url = DEFAULT_LOCAL_AUTH
        self.books_url = DEFAULT_LOCAL_BOOKS

    def set_remote(self):
        """Configura los endpoints al entorno remoto GCP."""
        self.auth_url = DEFAULT_REMOTE_AUTH
        self.books_url = DEFAULT_REMOTE_BOOKS

    def reset_defaults(self):
        """Restaura los valores predeterminados (Remoto GCP)."""
        self.set_remote()
        self.save()


# Instancia única compartida
settings = Settings()
