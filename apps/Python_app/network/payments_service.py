"""
network/payments_service.py
Cliente para el microservicio de Pagos (:5005).
"""
from config.settings import settings
from network.api_client import http_client


class PaymentsService:
    @property
    def base_url(self):
        return settings.payments_url

    def health(self):
        """GET /health"""
        return http_client.request("GET", f"{self.base_url}/health", timeout=(3.0, 5.0))

    check_health = health

    def process_payment(self, order_id, amount=None, method="tarjeta_simulada"):
        """POST /payments"""
        payload = {"order_id": order_id, "method": method}
        if amount is not None:
            payload["amount"] = amount
        return http_client.request("POST", f"{self.base_url}/payments", json_data=payload)

    def get_order_payments(self, order_id):
        """GET /payments/order/<order_id>"""
        return http_client.request("GET", f"{self.base_url}/payments/order/{order_id}")


payments_service = PaymentsService()
