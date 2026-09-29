"""
app.py
Punto de entrada del microservicio API.
Despliega Flask en el puerto 5001.
"""
from flask import Flask, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint

from config import PORT
from db import open_pool, close_pool
from routes.books import books_bp
from routes.catalogs import catalogs_bp
from routes.users import users_bp
from routes.health import health_bp

import atexit


def create_app():
    """Crea y configura la aplicacion Flask."""
    app = Flask(__name__)

    # --- CORS ---
    CORS(app, supports_credentials=True)

    # --- Pool de conexiones ---
    open_pool()
    atexit.register(close_pool)

    # --- Blueprints (rutas) ---
    app.register_blueprint(books_bp)
    app.register_blueprint(catalogs_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(health_bp)

    # --- Swagger UI ---
    swagger_ui_bp = get_swaggerui_blueprint(
        '/docs',                           # URL donde se sirve Swagger UI
        '/swagger/swagger.yaml',           # URL del archivo OpenAPI
        config={'app_name': 'API Microservice - Libreria en Linea'}
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
        return make_response_format({
            'status': 'error',
            'message': 'Recurso no encontrado.'
        }, 404, request)

    @app.errorhandler(405)
    def method_not_allowed(e):
        from helpers.response import make_response_format
        return make_response_format({
            'status': 'error',
            'message': 'Metodo HTTP no permitido.'
        }, 405, request)

    @app.errorhandler(500)
    def internal_error(e):
        from helpers.response import make_response_format
        return make_response_format({
            'status': 'error',
            'message': 'Error interno del servidor.'
        }, 500, request)

    return app


if __name__ == '__main__':
    app = create_app()
    print(f"API microservice escuchando en http://0.0.0.0:{PORT}")
    print(f"Swagger UI disponible en http://localhost:{PORT}/docs")
    app.run(host='0.0.0.0', port=PORT, debug=True)
