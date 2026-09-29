"""
routes/session.py
Endpoints de gestión de sesión: /session, /session/renew
"""
from datetime import datetime, timezone
from flask import Blueprint, request, session

from helpers.response import make_response_format
from config import SESSION_LIFETIME_MINUTES, SESSION_WARNING_MINUTES

session_bp = Blueprint('session', __name__)

SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_MINUTES * 60
SESSION_WARNING_SECONDS = SESSION_WARNING_MINUTES * 60


def _get_remaining_seconds():
    """Calcula los segundos restantes de la sesión."""
    last_activity = session.get('last_activity')
    if last_activity is None:
        return 0

    if isinstance(last_activity, str):
        last_activity = datetime.fromisoformat(last_activity)
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    elapsed = (now - last_activity).total_seconds()
    remaining = max(0, SESSION_LIFETIME_SECONDS - elapsed)
    return int(remaining)


# -----------------------------------------------------------------
# GET /session
# -----------------------------------------------------------------
@session_bp.route('/session', methods=['GET'])
def get_session():
    """Consultar si existe una sesión autenticada y su estado."""
    if 'user_id' not in session:
        return make_response_format({
            'status': 'no_session',
            'message': 'No hay sesión activa. Inicie sesión.'
        }, 401, request)

    remaining = _get_remaining_seconds()

    # Determinar estado
    if remaining <= 0:
        session.clear()
        return make_response_format({
            'status': 'session_expired',
            'message': (
                'Su sesión ha expirado por inactividad. '
                'Inicie sesión nuevamente.'
            )
        }, 440, request)

    if remaining <= SESSION_WARNING_SECONDS:
        status = 'expiring'
        message = 'Su sesión expirará pronto. ¿Desea continuar?'
    else:
        status = 'active'
        message = 'Sesión activa.'

    return make_response_format({
        'status': status,
        'message': message,
        'remaining_seconds': remaining,
        'session_lifetime_minutes': SESSION_LIFETIME_MINUTES,
        'user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'email': session.get('email'),
            'nombre': session.get('nombre'),
            'role': session.get('role')
        }
    }, 200, request)


# -----------------------------------------------------------------
# POST /session/renew and POST /session/extend
# -----------------------------------------------------------------
@session_bp.route('/session/renew', methods=['POST'])
@session_bp.route('/session/extend', methods=['POST'])
def renew_session():
    """Renovar la sesión (el usuario confirma que desea continuar)."""
    if 'user_id' not in session:
        return make_response_format({
            'status': 'no_session',
            'message': 'No hay sesión activa para renovar.'
        }, 401, request)

    # Resetear el timer
    session['last_activity'] = datetime.now(timezone.utc).isoformat()

    return make_response_format({
        'status': 'success',
        'message': 'Sesión renovada exitosamente.',
        'remaining_seconds': SESSION_LIFETIME_SECONDS,
        'session_lifetime_minutes': SESSION_LIFETIME_MINUTES
    }, 200, request)

