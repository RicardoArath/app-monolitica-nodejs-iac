"""
routes/health.py
Endpoint /health para verificar estado del microservicio de libros y PostgreSQL.
"""
from datetime import datetime, timezone
from flask import Blueprint, request
from db import health_check
from helpers.response import make_response_format

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def check_health():
    """Verificar estado del microservicio de libros."""
    db_ok = health_check()
    now_iso = datetime.now(timezone.utc).isoformat()

    if db_ok:
        return make_response_format({
            'status': 'ok',
            'service': 'books-microservice',
            'database': 'connected',
            'timestamp': now_iso
        }, 200, request)
    else:
        return make_response_format({
            'status': 'degraded',
            'service': 'books-microservice',
            'database': 'disconnected',
            'timestamp': now_iso
        }, 503, request)
