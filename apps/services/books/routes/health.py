"""
routes/health.py
Endpoint /health y /metrics para el microservicio de libros.
Verifica conectividad con PostgreSQL y Redis.
"""
import sys, os
_curr = os.path.abspath(__file__)
for _ in range(4):
    _curr = os.path.dirname(_curr)
    _cand = os.path.join(_curr, 'apps', 'services')
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
    if os.path.isdir(os.path.join(_curr, 'common')) and _curr not in sys.path:
        sys.path.insert(0, _curr)


from datetime import datetime, timezone
from flask import Blueprint, request, Response

from common import check_db_health, redis_client, metrics, make_response_format

health_bp = Blueprint('health', __name__)



@health_bp.route('/health', methods=['GET'])
def check_health():
    """Verificar estado de PostgreSQL y Redis para libros."""
    db_ok, db_err = check_db_health()
    redis_ok, redis_err = redis_client.check_health()
    now_iso = datetime.now(timezone.utc).isoformat()

    status = 'healthy' if (db_ok and redis_ok) else ('degraded' if db_ok else 'unhealthy')
    http_code = 200 if db_ok else 503

    return make_response_format({
        'status': status,
        'service': 'books-microservice',
        'port': 5001,
        'database': {
            'status': 'connected' if db_ok else 'disconnected',
            'error': db_err
        },
        'redis': {
            'status': 'connected' if redis_ok else 'disconnected',
            'fail_safe': 'active (Fail-Open catálogo, Fail-Closed seguridad)',
            'error': redis_err
        },
        'timestamp': now_iso
    }, http_code, request)


@health_bp.route('/metrics', methods=['GET'])
def metrics_view():
    """Expone métricas en formato texto de Prometheus."""
    content = metrics.render('books-microservice')
    return Response(content, mimetype='text/plain; version=0.0.4; charset=utf-8')
