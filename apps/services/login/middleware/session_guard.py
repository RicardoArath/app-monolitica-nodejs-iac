"""
middleware/session_guard.py
Middleware que verifica la expiración de sesiones en cada request autenticado.
Implementa sliding window: cada request válido renueva last_activity.
Si la sesión expira, responde HTTP 440 y limpia la sesión.
"""
from datetime import datetime, timezone
from flask import session, request
from helpers.response import make_response_format
from config import SESSION_LIFETIME_MINUTES

SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_MINUTES * 60

# Rutas que no requieren verificación de sesión
PUBLIC_PATHS = frozenset([
    '/register',
    '/login',
    '/verify-email',
    '/captcha',
    '/health',
    '/docs',
    '/swagger',
    '/static',
])


def is_public_path(path):
    """Verifica si la ruta es pública (no requiere sesión)."""
    for public in PUBLIC_PATHS:
        if path == public or path.startswith(public + '/'):
            return True
    # Swagger static assets
    if '/swaggerui/' in path or '/swagger/' in path:
        return True
    return False


def register_session_guard(app):
    """Registra el middleware before_request en la app Flask."""

    @app.before_request
    def check_session_expiration():
        # No verificar rutas públicas ni preflight CORS
        if is_public_path(request.path) or request.method == 'OPTIONS':
            return None

        # Si no hay sesión activa, cada endpoint decide si es requerida
        if 'user_id' not in session:
            return None

        last_activity = session.get('last_activity')
        if last_activity is None:
            # Sesión corrupta: limpiar
            session.clear()
            return None

        # Calcular tiempo transcurrido
        now = datetime.now(timezone.utc)
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        elapsed = (now - last_activity).total_seconds()

        if elapsed > SESSION_LIFETIME_SECONDS:
            # Sesión expirada
            session.clear()
            return make_response_format({
                'status': 'session_expired',
                'message': (
                    'Su sesión ha expirado por inactividad. '
                    'Inicie sesión nuevamente.'
                )
            }, 440, request)

        # Sliding window: renovar actividad
        session['last_activity'] = now.isoformat()

        return None

