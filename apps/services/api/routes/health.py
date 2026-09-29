from flask import Blueprint, request
import datetime
from db import health_check
from helpers.response import make_response_format

health_bp = Blueprint('health_bp', __name__)

@health_bp.route('/health', methods=['GET'])
def health():
    db_ok = health_check()
    data = {
        'service': 'api-service',
        'status': 'ok' if db_ok else 'error',
        'database': 'connected' if db_ok else 'disconnected',
        'timestamp': datetime.datetime.now().isoformat()
    }
    return make_response_format(data, 200 if db_ok else 503)
