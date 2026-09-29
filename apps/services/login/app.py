"""
app.py
Punto de entrada del microservicio de autenticación.
Despliega Flask en el puerto 5000.
"""
from flask import Flask
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from config import PORT, SESSION_SECRET, SESSION_LIFETIME_MINUTES, JWT_SECRET, JWT_EXPIRY_MINUTES
from db import open_pool, close_pool
from middleware.session_guard import register_session_guard
from routes.auth import auth_bp
from routes.session import session_bp
from routes.health import health_bp
from routes.token import token_bp

import atexit


def create_app():
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)

    # --- Configuración de Flask ---
    app.secret_key = SESSION_SECRET
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = SESSION_LIFETIME_MINUTES * 60

    # --- CORS ---
    CORS(app, supports_credentials=True)

    # --- Pool de conexiones ---
    open_pool()
    atexit.register(close_pool)

    # --- Middleware de sesión ---
    register_session_guard(app)

    # --- Blueprints (rutas) ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(token_bp)

    # --- Swagger UI ---
    swagger_ui_bp = get_swaggerui_blueprint(
        '/docs',                           # URL donde se sirve Swagger UI
        '/swagger/swagger.yaml',           # URL del archivo OpenAPI
        config={'app_name': 'Auth Microservice — Librería en Línea'}
    )
    app.register_blueprint(swagger_ui_bp, url_prefix='/docs')

    # --- Servir el archivo swagger.yaml ---
    @app.route('/swagger/swagger.yaml')
    def swagger_yaml():
        import os
        swagger_path = os.path.join(
            os.path.dirname(__file__), 'swagger', 'swagger.yaml'
        )
        with open(swagger_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/yaml; charset=utf-8'}

    # --- Manejo de errores ---
    @app.errorhandler(404)
    def not_found(e):
        from helpers.response import make_response_format
        from flask import request
        return make_response_format({
            'status': 'error',
            'message': 'Recurso no encontrado.'
        }, 404, request)

    @app.errorhandler(405)
    def method_not_allowed(e):
        from helpers.response import make_response_format
        from flask import request
        return make_response_format({
            'status': 'error',
            'message': 'Método HTTP no permitido.'
        }, 405, request)

    @app.errorhandler(500)
    def internal_error(e):
        from helpers.response import make_response_format
        from flask import request
        return make_response_format({
            'status': 'error',
            'message': 'Error interno del servidor.'
        }, 500, request)

    return app


if __name__ == '__main__':
    app = create_app()
    print(f"\n{'='*60}")
    print(f"  Auth microservice escuchando en http://0.0.0.0:{PORT}")
    print(f"  Swagger UI disponible en http://localhost:{PORT}/docs")
    print(f"  [JWT] Habilitado: HS256 | Expiracion: {JWT_EXPIRY_MINUTES} min")
    print(f"  [JWT] Endpoints: POST /token/verify, POST /token/refresh")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=PORT, debug=True)

