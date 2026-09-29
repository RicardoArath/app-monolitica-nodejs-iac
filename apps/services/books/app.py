"""
app.py
Punto de entrada del microservicio de gestión de libros (services/books).
Despliega Flask en el puerto 5001.
"""
import atexit
from flask import Flask, request
from flask_cors import CORS

from config import PORT
from db import open_pool, close_pool
from routes.books import books_bp
from routes.catalogs import catalogs_bp
from routes.health import health_bp


def create_app():
    """Crea y configura la aplicación Flask para el microservicio de libros."""
    app = Flask(__name__)

    # --- CORS ---
    CORS(app, supports_credentials=True)

    # --- Pool de conexiones PostgreSQL ---
    open_pool()
    atexit.register(close_pool)

    # --- Registro de Blueprints ---
    app.register_blueprint(books_bp)
    app.register_blueprint(catalogs_bp)
    app.register_blueprint(health_bp)

    # --- Manejadores de errores HTTP ---
    @app.errorhandler(404)
    def not_found(e):
        from helpers.response import make_response_format
        return make_response_format({
            'status': 'error',
            'message': 'Recurso no encontrado en el microservicio de libros.'
        }, 404, request)

    @app.errorhandler(405)
    def method_not_allowed(e):
        from helpers.response import make_response_format
        return make_response_format({
            'status': 'error',
            'message': 'Método HTTP no permitido.'
        }, 405, request)

    @app.errorhandler(500)
    def internal_error(e):
        from helpers.response import make_response_format
        return make_response_format({
            'status': 'error',
            'message': 'Error interno del servidor en microservicio de libros.'
        }, 500, request)

    return app


if __name__ == '__main__':
    app = create_app()
    print(f"\n{'='*60}")
    print(f"  Books microservice escuchando en http://0.0.0.0:{PORT}")
    print(f"  [JWT] Guard habilitado (HS256)")
    print(f"  Rutas PROTEGIDAS: POST, PUT, PATCH, DELETE /books")
    print(f"  Rutas PUBLICAS:   GET /books, GET /books/{{isbn}}")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=PORT, debug=True)
