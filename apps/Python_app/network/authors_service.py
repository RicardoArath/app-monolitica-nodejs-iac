"""
network/authors_service.py
Cliente para el microservicio de Autores (:5003).
"""
from config.settings import settings
from network.api_client import http_client


class AuthorsService:
    @property
    def base_url(self):
        return settings.authors_url

    def health(self):
        """GET /health"""
        return http_client.request("GET", f"{self.base_url}/health", timeout=(3.0, 5.0))

    check_health = health

    def list_authors(self):
        """GET /authors"""
        return http_client.request("GET", f"{self.base_url}/authors")

    def get_author(self, author_id):
        """GET /authors/<id>"""
        return http_client.request("GET", f"{self.base_url}/authors/{author_id}")

    def create_author(self, name):
        """POST /authors (Admin only)"""
        return http_client.request("POST", f"{self.base_url}/authors", json_data={"name": name})

    def update_author(self, author_id, name):
        """PUT /authors/<id> (Admin only)"""
        return http_client.request("PUT", f"{self.base_url}/authors/{author_id}", json_data={"name": name})

    def delete_author(self, author_id):
        """DELETE /authors/<id> (Admin only)"""
        return http_client.request("DELETE", f"{self.base_url}/authors/{author_id}")

    def link_book(self, author_id, book_id):
        """POST /authors/<id>/books (Admin only)"""
        return http_client.request("POST", f"{self.base_url}/authors/{author_id}/books", json_data={"book_id": book_id})

    def unlink_book(self, author_id, book_id):
        """DELETE /authors/<id>/books/<book_id> (Admin only)"""
        return http_client.request("DELETE", f"{self.base_url}/authors/{author_id}/books/{book_id}")


authors_service = AuthorsService()
