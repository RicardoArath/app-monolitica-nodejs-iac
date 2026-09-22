"""
routes/health.py
Endpoint de salud: /health
Verifica el estado del microservicio y la conectividad a PostgreSQL.
"""
from datetime import datetime, timezone
from flask import Blueprint, request

from db import health_check
from helpers.response import make_response_format

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """Verificar el estado del microservicio y PostgreSQL."""
    db_ok = health_check()

    data = {
        'status': 'ok' if db_ok else 'degraded',
        'service': 'auth-microservice',
        'database': 'connected' if db_ok else 'disconnected',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    status_code = 200 if db_ok else 503

    return make_response_format(data, status_code, request)

