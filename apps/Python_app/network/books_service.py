"""
network/books_service.py
Servicio de comunicación con el microservicio de libros (services/books en puerto 5001).
Soporta GET, POST, PUT, PATCH, DELETE por ISBN y filtrado de catálogo.
"""
from config.settings import settings
from network.api_client import http_client


class BooksService:
    @property
    def base_url(self):
        return settings.books_url

    def health(self):
        """Consulta el estado del microservicio de libros (GET /health)."""
        url = f"{self.base_url}/health"
        return http_client.request("GET", url, timeout=(5.0, 10.0))

    check_health = health

    def get_books(self, isbn=None, title=None, year=None, min_price=None, max_price=None, page=1):
        """
        Consulta el catálogo de libros con filtros opcionales (GET /books).
        """
        url = f"{self.base_url}/books"
        params = {"page": page}
        if isbn:
            params["isbn"] = isbn
        if title:
            params["title"] = title
        if year:
            params["year"] = year
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price

        return http_client.request("GET", url, params=params)

    def get_book_by_isbn(self, isbn):
        """Consulta el detalle completo de un libro por su ISBN (GET /books/{isbn})."""
        url = f"{self.base_url}/books/{isbn}"
        return http_client.request("GET", url)

    def create_book(self, book_data):
        """Registra un nuevo libro (POST /books)."""
        url = f"{self.base_url}/books"
        return http_client.request("POST", url, json_data=book_data)

    def put_book(self, isbn, book_data):
        """
        Actualización COMPLETA de un libro (PUT /books/{isbn}).
        Envía la totalidad de los atributos para reemplazo completo.
        """
        url = f"{self.base_url}/books/{isbn}"
        return http_client.request("PUT", url, json_data=book_data)

    def patch_book(self, isbn, partial_data):
        """
        Actualización PARCIAL de un libro (PATCH /books/{isbn}).
        Envía únicamente el o los atributos que se desean modificar.
        """
        url = f"{self.base_url}/books/{isbn}"
        return http_client.request("PATCH", url, json_data=partial_data)

    def delete_book(self, isbn):
        """Elimina un libro identificado por su ISBN (DELETE /books/{isbn})."""
        url = f"{self.base_url}/books/{isbn}"
        return http_client.request("DELETE", url)

    def get_catalog(self, catalog_name):
        """Obtiene opciones de catálogo: authors, genres, formats, categories."""
        url = f"{self.base_url}/{catalog_name}"
        return http_client.request("GET", url)


books_service = BooksService()
