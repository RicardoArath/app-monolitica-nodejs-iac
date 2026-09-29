"""
session/session_manager.py
Persistencia local de la sesión (session.json) y validación contra el servidor.
Maneja almacenamiento de cookies HTTP y datos básicos del usuario.
"""
import os
import json
from network.api_client import http_client
from network.auth_service import auth_service

SESSION_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(SESSION_DIR, "session.json")


class SessionManager:
    def __init__(self):
        self.user = None

    def save_session(self, user_data):
        """Guarda la información de sesión, cookies y token JWT en session.json."""
        self.user = user_data
        cookies = http_client.get_cookies_dict()
        jwt_token = http_client.jwt_token
        data = {
            "user": user_data,
            "cookies": cookies,
            "jwt_token": jwt_token
        }
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[SESSION-MANAGER] 💾 Sesión guardada localmente (con JWT: {'Sí' if jwt_token else 'No'})")
            return True
        except Exception as e:
            print(f"Error al guardar session.json: {e}")
            return False

    def load_cached_session(self):
        """Carga las cookies, JWT y usuario desde session.json sin validar en servidor."""
        if not os.path.exists(SESSION_FILE):
            return None
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookies = data.get("cookies", {})
                http_client.set_cookies_dict(cookies)
                jwt_token = data.get("jwt_token")
                if jwt_token:
                    http_client.set_jwt(jwt_token)
                self.user = data.get("user")
                print(f"[SESSION-MANAGER] 📂 Sesión recuperada desde caché (con JWT: {'Sí' if jwt_token else 'No'})")
                return self.user
        except Exception as e:
            print(f"Error al cargar session.json: {e}")
            return None

    def validate_with_server(self):
        """
        Verifica con el microservicio si la sesión persistida sigue siendo válida (GET /session).
        Retorna:
          - (True, "active", user): Sesión activa.
          - (True, "expiring", user): Sesión activa pero próxima a expirar.
          - (False, "expired", None): Sesión expirada o inválida (401 / 440).
          - (False, "unreachable", None): Microservicio inaccesible.
        """
        user = self.load_cached_session()
        if not user:
            return False, "no_session", None

        res = auth_service.get_session()

        if not res["success"]:
            # Si el servidor respondió 401 o 440, la sesión expiró
            if res["status_code"] in (401, 440):
                self.clear_session()
                return False, "expired", None
            # Si hubo error de conexión (servidor caído)
            return False, "unreachable", None

        data = res["data"] or {}
        status = data.get("status", "active")
        server_user = data.get("user", user)
        self.user = server_user

        if status in ("active", "expiring"):
            return True, status, server_user

        self.clear_session()
        return False, "expired", None

    def clear_session(self):
        """Elimina el archivo session.json y limpia cookies y JWT."""
        self.user = None
        http_client.clear_cookies()
        http_client.clear_jwt()
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except Exception as e:
                print(f"Error al eliminar session.json: {e}")


session_manager = SessionManager()
