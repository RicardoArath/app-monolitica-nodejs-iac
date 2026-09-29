"""
network/auth_service.py
Servicio de comunicacion con el microservicio de autenticacion (services/login en puerto 5000).
Maneja JWT: al hacer login exitoso, extrae y almacena el token JWT.
"""
from config.settings import settings
from network.api_client import http_client


class AuthService:
    @property
    def base_url(self):
        return settings.auth_url

    def health(self):
        """Consulta el estado del microservicio de login (GET /health)."""
        url = f"{self.base_url}/health"
        return http_client.request("GET", url, timeout=(5.0, 10.0))

    def get_captcha(self):
        """Obtiene un desafio matematico para verificacion humana (GET /captcha)."""
        url = f"{self.base_url}/captcha"
        return http_client.request("GET", url)

    def register(self, nombre, apellido_paterno, apellido_materno, email, password, captcha_id=None, captcha_answer=None):
        """Registra un nuevo usuario (POST /register)."""
        url = f"{self.base_url}/register"
        payload = {
            "nombre": nombre,
            "apellido_paterno": apellido_paterno,
            "apellido_materno": apellido_materno,
            "email": email,
            "password": password
        }
        if captcha_id and captcha_answer:
            payload["captcha_id"] = captcha_id
            payload["captcha_answer"] = captcha_answer

        return http_client.request("POST", url, json_data=payload)

    def login(self, email, password):
        """
        Inicia sesion y obtiene la cookie de Flask + JWT (POST /login).
        Extrae y almacena el token JWT del response para uso en operaciones protegidas.
        """
        url = f"{self.base_url}/login"
        payload = {
            "email": email,
            "password": password
        }
        res = http_client.request("POST", url, json_data=payload)

        # --- Extraer y almacenar JWT ---
        if res["success"] and res["data"]:
            token = res["data"].get("token")
            if token:
                http_client.set_jwt(token)
                print("[AUTH-SERVICE] [OK] JWT recibido y almacenado tras login exitoso")
                print(f"[AUTH-SERVICE]      token_type: {res['data'].get('token_type', 'Bearer')}")
                print(f"[AUTH-SERVICE]      expires_in: {res['data'].get('expires_in', '?')} segundos")
            else:
                print("[AUTH-SERVICE] [WARN] Login exitoso pero no se recibio token JWT")

        return res

    def logout(self):
        """Cierra la sesion del usuario y limpia el JWT (POST /logout)."""
        url = f"{self.base_url}/logout"
        res = http_client.request("POST", url)
        http_client.clear_cookies()
        http_client.clear_jwt()
        print("[AUTH-SERVICE] [LOGOUT] Sesion cerrada y JWT limpiado")
        return res

    def get_session(self):
        """Consulta si la sesion actual sigue vigente (GET /session)."""
        url = f"{self.base_url}/session"
        return http_client.request("GET", url)

    def extend_session(self):
        """Extiende la sesion activa reseteando el temporizador (POST /session/extend)."""
        url = f"{self.base_url}/session/extend"
        return http_client.request("POST", url)

    def get_profile(self):
        """Consulta el perfil completo del usuario autenticado (GET /profile)."""
        url = f"{self.base_url}/profile"
        return http_client.request("GET", url)

    def patch_profile(self, data):
        """Actualiza parcialmente los datos del perfil (PATCH /profile)."""
        url = f"{self.base_url}/profile"
        return http_client.request("PATCH", url, json_data=data)

    def verify_token(self, token=None):
        """Verifica la validez de un JWT (POST /token/verify)."""
        url = f"{self.base_url}/token/verify"
        t = token or http_client.jwt_token
        if not t:
            return {"success": False, "status_code": 0, "data": None, "error": "No hay token JWT disponible."}
        return http_client.request("POST", url, json_data={"token": t})

    def refresh_token(self, token=None):
        """Renueva el JWT obteniendo uno nuevo (POST /token/refresh)."""
        url = f"{self.base_url}/token/refresh"
        t = token or http_client.jwt_token
        if not t:
            return {"success": False, "status_code": 0, "data": None, "error": "No hay token JWT disponible."}
        res = http_client.request("POST", url, json_data={"token": t})
        if res["success"] and res["data"]:
            new_token = res["data"].get("token")
            if new_token:
                http_client.set_jwt(new_token)
                print("[AUTH-SERVICE] [RENEW] Token JWT renovado exitosamente")
        return res


auth_service = AuthService()
