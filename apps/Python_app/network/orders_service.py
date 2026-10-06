"""
network/orders_service.py
Cliente para el microservicio de Pedidos (:5004).
"""
from config.settings import settings
from network.api_client import http_client


class OrdersService:
    @property
    def base_url(self):
        return settings.orders_url

    def health(self):
        """GET /health"""
        return http_client.request("GET", f"{self.base_url}/health", timeout=(3.0, 5.0))

    def list_orders(self):
        """GET /orders"""
        return http_client.request("GET", f"{self.base_url}/orders")

    def get_order(self, order_id):
        """GET /orders/<id>"""
        return http_client.request("GET", f"{self.base_url}/orders/{order_id}")

    def create_order(self, items):
        """POST /orders -> items=[{"book_id": 1, "quantity": 2}, ...]"""
        return http_client.request("POST", f"{self.base_url}/orders", json_data={"items": items})

    def update_status(self, order_id, status):
        """PATCH /orders/<id>/status"""
        return http_client.request("PATCH", f"{self.base_url}/orders/{order_id}/status", json_data={"status": status})

    def cancel_order(self, order_id):
        """Atajo para cancelar un pedido y devolver el stock."""
        return self.update_status(order_id, "cancelled")


orders_service = OrdersService()
