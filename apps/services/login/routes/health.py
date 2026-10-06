"""
routes/health.py
Endpoints de salud y métricas para el microservicio de Login / Auth.
GET /health  -- Verifica conectividad con PostgreSQL y Redis.
GET /metrics -- Expone métricas en formato Prometheus.
"""
import sys, os
_SERVICES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)

from datetime import datetime, timezone
from flask import Blueprint, request, Response

from common import check_db_health, redis_client, metrics, make_response_format


health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """Verifica estado de PostgreSQL y Redis."""
    db_ok, db_err = check_db_health()
    redis_ok, redis_err = redis_client.check_health()

    status = 'healthy' if (db_ok and redis_ok) else ('degraded' if db_ok else 'unhealthy')
    http_code = 200 if db_ok else 503

    data = {
        'status': status,
        'service': 'login-service',
        'port': 5000,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'database': {
            'status': 'connected' if db_ok else 'disconnected',
            'error': db_err
        },
        'redis': {
            'status': 'connected' if redis_ok else 'disconnected',
            'error': redis_err
        }
    }

    return make_response_format(data, http_code, request)


@health_bp.route('/metrics', methods=['GET'])
def metrics_view():
    """Expone métricas en texto Prometheus."""
    content = metrics.render('login-service')
    return Response(content, mimetype='text/plain; version=0.0.4; charset=utf-8')
