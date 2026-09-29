import requests
from config import AUTH_BASE_URL, API_BASE_URL

class AuthClient:
    def __init__(self):
        self.session = requests.Session()
    
    def _url(self, path):
        sep = "&" if "?" in path else "?"
        return f"{AUTH_BASE_URL}{path}{sep}format=json"

    def login(self, email, password):
        resp = self.session.post(self._url("/login"), json={"email": email, "password": password}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def register(self, nombre, apellido_paterno, apellido_materno, email, password, captcha_id, captcha_answer):
        data = {
            "nombre": nombre, "apellido_paterno": apellido_paterno, "apellido_materno": apellido_materno,
            "email": email, "password": password, "captcha_id": captcha_id, "captcha_answer": captcha_answer
        }
        resp = self.session.post(self._url("/register"), json=data, timeout=5)
        resp.raise_for_status()
        return resp.json()
        
    def get_captcha(self):
        resp = self.session.get(self._url("/captcha"), timeout=5)
        resp.raise_for_status()
        return resp.json()
        
    def logout(self):
        resp = self.session.post(self._url("/logout"), timeout=5)
        return resp.json() if resp.ok else {}
        
    def check_session(self):
        resp = self.session.get(self._url("/session"), timeout=5)
        resp.raise_for_status()
        return resp.json()
        
    def renew_session(self):
        resp = self.session.post(self._url("/session/renew"), timeout=5)
        resp.raise_for_status()
        return resp.json()
        
    def health(self):
        try:
            resp = self.session.get(self._url("/health"), timeout=3)
            return resp.ok
        except:
            return False
            
    def get_cookies_dict(self):
        return requests.utils.dict_from_cookiejar(self.session.cookies)
        
    def set_cookies_dict(self, cookies_dict):
        self.session.cookies = requests.utils.cookiejar_from_dict(cookies_dict)

class ApiClient:
    def __init__(self, auth_client):
        self.auth_client = auth_client
        self.session = auth_client.session

    def _url(self, path, query_str=""):
        sep = "&" if "?" in path or query_str else ""
        q = f"?format=json{sep}{query_str}"
        return f"{API_BASE_URL}{path}{q}"

    def get_books(self, page=1, q=''):
        query_str = f"page={page}"
        if q:
            query_str += f"&q={q}"
        resp = self.session.get(self._url("/api/books", query_str), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_book(self, id):
        resp = self.session.get(self._url(f"/api/books/{id}"), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def create_book(self, data):
        resp = self.session.post(self._url("/api/books"), json=data, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def update_book(self, id, data):
        resp = self.session.put(self._url(f"/api/books/{id}"), json=data, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def delete_book(self, id):
        resp = self.session.delete(self._url(f"/api/books/{id}"), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_catalog(self, table):
        resp = self.session.get(self._url(f"/api/{table}"), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def create_catalog(self, table, name):
        resp = self.session.post(self._url(f"/api/{table}"), json={"name": name}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def update_catalog(self, table, id, name):
        resp = self.session.put(self._url(f"/api/{table}/{id}"), json={"name": name}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def delete_catalog(self, table, id):
        resp = self.session.delete(self._url(f"/api/{table}/{id}"), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_users(self):
        resp = self.session.get(self._url("/api/users"), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def health(self):
        try:
            resp = self.session.get(self._url("/health"), timeout=3)
            return resp.ok
        except:
            return False
