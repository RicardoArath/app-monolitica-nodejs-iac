"""
pagos/app.py
Punto de entrada del microservicio de Pagos (puerto 5005).
"""
import os
import sys

_curr = os.path.abspath(__file__)
for _ in range(4):
    _curr = os.path.dirname(_curr)
    _cand = os.path.join(_curr, 'apps', 'services')
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
    if os.path.isdir(os.path.join(_curr, 'common')) and _curr not in sys.path:
        sys.path.insert(0, _curr)

from common import create_microservice_app, config
from routes import payments_bp

app = create_microservice_app(
    service_name='pagos-service',
    port=config.service_port('PAGOS', 5005),
    blueprints=[payments_bp]
)

if __name__ == '__main__':
    port = config.service_port('PAGOS', 5005)
    print(f"\n{'='*60}")
    print(f"  Pagos Microservice escuchando en http://0.0.0.0:{port}")
    print(f"  Endpoints: POST /payments, GET /payments/order/<order_id>")
    print(f"  Health & Metrics: GET /health, GET /metrics")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=config.FLASK_DEBUG)
