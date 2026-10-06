"""
network/users_service.py
Cliente para el microservicio de Usuarios (:5002).
"""
from config.settings import settings
from network.api_client import http_client


class UsersService:
    @property
    def base_url(self):
        return settings.users_url

    def health(self):
        """GET /health"""
        return http_client.request("GET", f"{self.base_url}/health", timeout=(3.0, 5.0))

    check_health = health

    def list_users(self):
        """GET /users (Admin only)"""
        return http_client.request("GET", f"{self.base_url}/users")

    def get_user(self, user_id):
        """GET /users/<id>"""
        return http_client.request("GET", f"{self.base_url}/users/{user_id}")

    def create_user(self, data):
        """POST /users"""
        return http_client.request("POST", f"{self.base_url}/users", json_data=data)

    def update_user(self, user_id, data):
        """PUT /users/<id> (Admin only)"""
        return http_client.request("PUT", f"{self.base_url}/users/{user_id}", json_data=data)

    def delete_user(self, user_id):
        """DELETE /users/<id> (Admin only)"""
        return http_client.request("DELETE", f"{self.base_url}/users/{user_id}")


users_service = UsersService()
