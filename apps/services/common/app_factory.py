"""
common/app_factory.py
Fábrica de aplicaciones Flask para microservicios.
Configura automáticamente:
  - Endpoint de salud /health (inspecciona PostgreSQL y Redis)
  - Endpoint de métricas /metrics (formato Prometheus)
  - Registro de tiempos de respuesta y contadores HTTP
  - CORS homogéneo
  - Manejadores de errores duales (JSON/XML)
  - Apertura y cierre del pool de conexiones PostgreSQL
"""
import time
from datetime import datetime, timezone
from typing import List, Optional

from flask import Flask, request, Response
from flask_cors import CORS

from common import config, metrics
from common.db import check_db_health, open_pool, close_pool
from common.logging_utils import get_logger
from common.redis_client import redis_client
from common.response import make_response_format

logger = get_logger('common.factory')


def create_microservice_app(service_name: str, port: int, blueprints: Optional[List] = None) -> Flask:
    """Crea y prepara una aplicación Flask para cualquier microservicio del ecosistema."""
    app = Flask(service_name)
    app.config['ENV'] = config.APP_ENV
    app.config['DEBUG'] = config.FLASK_DEBUG

    # Configuración de CORS permisivo para clientes web y de escritorio
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # Inicializar pool de base de datos
    try:
        open_pool()
    except Exception as e:
        logger.warning(f"No se pudo inicializar pool en arranque para {service_name}: {e}")

    # --- Hooks de Métricas HTTP ---
    @app.before_request
    def before_req():
        request._start_time = time.time()

    @app.after_request
    def after_req(response):
        # Duración de la petición
        duration = time.time() - getattr(request, '_start_time', time.time())
        endpoint = request.endpoint or 'unknown'
        metrics.observe('http_request_duration_seconds', duration, endpoint=endpoint)
        metrics.inc(
            'http_requests_total',
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        )
        return response

    # --- Endpoints Base: /health y /metrics ---
    @app.route('/health', methods=['GET'])
    def health_check():
        db_ok, db_err = check_db_health()
        redis_ok, redis_err = redis_client.check_health()

        # Determinación de estado general
        if not db_ok:
            overall_status = 'unhealthy'
            http_code = 503
        elif not redis_ok:
            overall_status = 'degraded'  # Funciona en modo degradado (fail-open en caché)
            http_code = 200
        else:
            overall_status = 'healthy'
            http_code = 200

        health_data = {
            'status': overall_status,
            'service': service_name,
            'port': port,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': {
                'status': 'connected' if db_ok else 'disconnected',
                'error': db_err
            },
            'redis': {
                'status': 'connected' if redis_ok else 'disconnected',
                'fail_safe': 'active (fail-open para lectura, fail-closed para auth)',
                'error': redis_err
            }
        }
        return make_response_format(health_data, http_code, request)

    @app.route('/metrics', methods=['GET'])
    def metrics_endpoint():
        content = metrics.render(service_name)
        return Response(content, mimetype='text/plain; version=0.0.4; charset=utf-8')

    # --- Manejadores de Errores Globales ---
    @app.errorhandler(400)
    def handle_400(e):
        return make_response_format({'status': 'error', 'message': str(getattr(e, 'description', 'Petición inválida.'))}, 400, request)

    @app.errorhandler(401)
    def handle_401(e):
        return make_response_format({'status': 'error', 'message': str(getattr(e, 'description', 'No autorizado.'))}, 401, request)

    @app.errorhandler(403)
    def handle_403(e):
        return make_response_format({'status': 'error', 'message': str(getattr(e, 'description', 'Prohibido.'))}, 403, request)

    @app.errorhandler(404)
    def handle_404(e):
        return make_response_format({'status': 'error', 'message': f'Recurso no encontrado: {request.path}'}, 404, request)

    @app.errorhandler(405)
    def handle_405(e):
        return make_response_format({'status': 'error', 'message': 'Método HTTP no permitido.'}, 405, request)

    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f"Error 500 no controlado en {service_name}: {e}")
        return make_response_format({'status': 'error', 'message': 'Error interno del servidor.'}, 500, request)

    @app.errorhandler(503)
    def handle_503(e):
        return make_response_format({'status': 'error', 'message': str(getattr(e, 'description', 'Servicio no disponible.'))}, 503, request)

    # Registrar Blueprints adicionales
    if blueprints:
        for bp in blueprints:
            app.register_blueprint(bp)

    return app
