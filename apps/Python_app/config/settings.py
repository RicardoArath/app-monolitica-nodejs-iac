"""
config/settings.py
Gestión de configuración y persistencia de URLs de los 6 microservicios y Redis.
Permite alternar entre el entorno Local (localhost) y Remoto (GCP VM).
"""
import os
import json

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Entorno Local
DEFAULT_LOCAL_AUTH = "http://localhost:5000"
DEFAULT_LOCAL_BOOKS = "http://localhost:5001"
DEFAULT_LOCAL_PAYMENTS_URL = "http://localhost:5002"
DEFAULT_LOCAL_ORDERS_URL = "http://localhost:5003"
DEFAULT_LOCAL_USERS_URL = "http://localhost:5004"
DEFAULT_LOCAL_AUTHORS_URL = "http://localhost:5005"
DEFAULT_LOCAL_REDIS_HOST = "localhost"
DEFAULT_LOCAL_REDIS_PORT = 6379

# Aliases para compatibilidad con código existente
DEFAULT_LOCAL_PAYMENTS = DEFAULT_LOCAL_PAYMENTS_URL
DEFAULT_LOCAL_ORDERS = DEFAULT_LOCAL_ORDERS_URL
DEFAULT_LOCAL_USERS = DEFAULT_LOCAL_USERS_URL
DEFAULT_LOCAL_AUTHORS = DEFAULT_LOCAL_AUTHORS_URL

# Entorno Remoto GCP (IP estática fija reservada en GCP: 35.226.206.203)
DEFAULT_REMOTE_HOST = "http://35.226.206.203"
DEFAULT_REMOTE_AUTH = f"{DEFAULT_REMOTE_HOST}:5000"
DEFAULT_REMOTE_BOOKS = f"{DEFAULT_REMOTE_HOST}:5001"
DEFAULT_REMOTE_PAYMENTS_URL = "http://35.226.206.203:5002"
DEFAULT_REMOTE_ORDERS_URL = "http://35.226.206.203:5003"
DEFAULT_REMOTE_USERS_URL = "http://35.226.206.203:5004"
DEFAULT_REMOTE_AUTHORS_URL = "http://35.226.206.203:5005"
DEFAULT_REMOTE_REDIS_HOST = "35.226.206.203"
DEFAULT_REMOTE_REDIS_PORT = 6379

# Aliases remotos para compatibilidad
DEFAULT_REMOTE_PAYMENTS = DEFAULT_REMOTE_PAYMENTS_URL
DEFAULT_REMOTE_ORDERS = DEFAULT_REMOTE_ORDERS_URL
DEFAULT_REMOTE_USERS = DEFAULT_REMOTE_USERS_URL
DEFAULT_REMOTE_AUTHORS = DEFAULT_REMOTE_AUTHORS_URL


class Settings:
    def __init__(self):
        self.auth_url = DEFAULT_LOCAL_AUTH
        self.books_url = DEFAULT_LOCAL_BOOKS
        self.payments_url = DEFAULT_LOCAL_PAYMENTS_URL
        self.orders_url = DEFAULT_LOCAL_ORDERS_URL
        self.users_url = DEFAULT_LOCAL_USERS_URL
        self.authors_url = DEFAULT_LOCAL_AUTHORS_URL
        self.redis_host = DEFAULT_LOCAL_REDIS_HOST
        self.redis_port = DEFAULT_LOCAL_REDIS_PORT
        self.active_env = "local"
        self.load()

    def load(self):
        """Carga la configuración guardada desde config.json si existe."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.auth_url = data.get("auth_url", self.auth_url).rstrip("/")
                    self.books_url = data.get("books_url", self.books_url).rstrip("/")
                    self.payments_url = data.get("payments_url", self.payments_url).rstrip("/")
                    self.orders_url = data.get("orders_url", self.orders_url).rstrip("/")
                    self.users_url = data.get("users_url", self.users_url).rstrip("/")
                    self.authors_url = data.get("authors_url", self.authors_url).rstrip("/")
                    self.redis_host = data.get("redis_host", self.redis_host)
                    self.redis_port = int(data.get("redis_port", self.redis_port))
                    self.active_env = data.get("active_env", self.active_env)
            except Exception as e:
                print(f"Error al leer config.json: {e}")

    def save(self):
        """Guarda la configuración actual en config.json."""
        data = {
            "active_env": self.active_env,
            "auth_url": self.auth_url.rstrip("/"),
            "books_url": self.books_url.rstrip("/"),
            "payments_url": self.payments_url.rstrip("/"),
            "orders_url": self.orders_url.rstrip("/"),
            "users_url": self.users_url.rstrip("/"),
            "authors_url": self.authors_url.rstrip("/"),
            "redis_host": self.redis_host,
            "redis_port": self.redis_port
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
        self.active_env = "local"
        self.auth_url = DEFAULT_LOCAL_AUTH
        self.books_url = DEFAULT_LOCAL_BOOKS
        self.payments_url = DEFAULT_LOCAL_PAYMENTS_URL
        self.orders_url = DEFAULT_LOCAL_ORDERS_URL
        self.users_url = DEFAULT_LOCAL_USERS_URL
        self.authors_url = DEFAULT_LOCAL_AUTHORS_URL
        self.redis_host = DEFAULT_LOCAL_REDIS_HOST
        self.redis_port = DEFAULT_LOCAL_REDIS_PORT

    def set_remote(self, host=DEFAULT_REMOTE_HOST):
        """Configura los endpoints al entorno remoto GCP."""
        self.active_env = "remote"
        h = host.rstrip("/")
        self.auth_url = f"{h}:5000"
        self.books_url = f"{h}:5001"
        self.payments_url = f"{h}:5002"
        self.orders_url = f"{h}:5003"
        self.users_url = f"{h}:5004"
        self.authors_url = f"{h}:5005"
        self.redis_host = h.replace("http://", "").replace("https://", "").split(":")[0]
        self.redis_port = DEFAULT_REMOTE_REDIS_PORT


settings = Settings()
