"""
common/logging_utils.py
Logging con redacción automática de secretos.

Regla de seguridad: nunca escribir contraseñas, JWT, refresh tokens ni la
contraseña de Redis en los logs. El filtro RedactingFilter enmascara esos
valores aunque un desarrollador los incluya por error en un mensaje.
"""
import logging
import re
import sys

_PATTERNS = [
    # Encabezado Authorization: Bearer <token>
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-_.=]+', re.IGNORECASE), r'\1[REDACTED]'),
    # Cualquier JWT (header.payload.signature)
    (re.compile(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+'), '[JWT-REDACTED]'),
    # Campos sensibles en JSON / query strings
    (re.compile(r'("?(password|password_hash|refresh_token|access_token|token|card_number)"?\s*[:=]\s*"?)[^",&\s]+',
                re.IGNORECASE), r'\1[REDACTED]'),
    # Contraseña dentro de REDIS_URL
    (re.compile(r'(redis(?:s)?://[^:/@]*:)[^@]+(@)'), r'\1****\2'),
]


def redact(text):
    text = str(text)
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record):
        try:
            record.msg = redact(record.getMessage())
            record.args = ()
        except Exception:
            pass
        return True


_configured = False


def _configure_root():
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S'
    ))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # werkzeug registra las líneas de acceso HTTP: también pasan por el filtro
    logging.getLogger('werkzeug').addFilter(RedactingFilter())
    _configured = True


def get_logger(name):
    _configure_root()
    return logging.getLogger(name)
