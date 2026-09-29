"""
network/api_client.py
Cliente HTTP centralizado utilizando requests.Session.
Maneja cookies de sesion de Flask, tokens JWT, serializacion JSON,
timeouts de seguridad y captura controlada de errores para tolerancia a fallos.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApiClient:
    def __init__(self):
        self.session = requests.Session()
        # Timeout robusto para conexiones remotas a GCP: 10s connect, 30s read
        self.timeout = (10.0, 30.0)
        # Token JWT (se establece al iniciar sesion)
        self._jwt_token = None

        # Politica de reintento automatico ante caidas transitorias de conexion
        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # --- JWT ---
    @property
    def jwt_token(self):
        """Retorna el token JWT almacenado."""
        return self._jwt_token

    def set_jwt(self, token):
        """Almacena el token JWT recibido del servicio de login."""
        self._jwt_token = token
        if token:
            print(f"[JWT-CLIENT] [TOKEN] Token JWT almacenado: {token[:50]}...")
        else:
            print("[JWT-CLIENT] [TOKEN] Token JWT eliminado")

    def clear_jwt(self):
        """Elimina el token JWT almacenado."""
        self._jwt_token = None
        print("[JWT-CLIENT] [TOKEN] Token JWT limpiado")

    # --- Cookies ---
    def get_cookies_dict(self):
        """Retorna las cookies actuales de la sesion en forma de diccionario."""
        return requests.utils.dict_from_cookiejar(self.session.cookies)

    def set_cookies_dict(self, cookies_dict):
        """Restaura cookies a partir de un diccionario."""
        if cookies_dict:
            self.session.cookies.update(requests.utils.cookiejar_from_dict(cookies_dict))

    def clear_cookies(self):
        """Limpia las cookies de la sesion."""
        self.session.cookies.clear()

    def request(self, method, url, params=None, json_data=None, timeout=None):
        """
        Ejecuta una peticion HTTP con tolerancia total a fallos.
        Inyecta automaticamente el header Authorization: Bearer <token> si hay JWT.
        Garantiza que la aplicacion nunca lance una excepcion no capturada ni se cierre.
        """
        params = params or {}
        # Asegurar formato JSON en los microservicios
        if "format" not in params:
            params["format"] = "json"

        req_timeout = timeout or self.timeout

        # --- Construir headers con JWT ---
        headers = {}
        if self._jwt_token:
            headers['Authorization'] = f'Bearer {self._jwt_token}'
            print(f"[JWT-CLIENT] [SEND] {method.upper()} {url} -- Enviando JWT en header Authorization")
        else:
            print(f"[JWT-CLIENT] [SEND] {method.upper()} {url} -- Sin token JWT")

        try:
            resp = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=req_timeout
            )
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            # Log de respuesta JWT
            if resp.status_code == 401:
                print(f"[JWT-CLIENT] [401] {method.upper()} {url} -- 401 Unauthorized (token invalido o expirado)")
            elif 200 <= resp.status_code < 300:
                print(f"[JWT-CLIENT] [OK]  {method.upper()} {url} -- {resp.status_code} OK")

            return {
                "success": 200 <= resp.status_code < 300,
                "status_code": resp.status_code,
                "data": data,
                "error": None
            }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "status_code": 0,
                "data": None,
                "error": "Error de conexion: No se pudo contactar al microservicio (servicio inaccesible o apagado)."
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status_code": 408,
                "data": None,
                "error": "Tiempo de espera agotado: El microservicio tardo demasiado en responder."
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": -1,
                "data": None,
                "error": f"Error inesperado de comunicacion HTTP: {str(e)}"
            }


# Instancia compartida del cliente HTTP
http_client = ApiClient()
