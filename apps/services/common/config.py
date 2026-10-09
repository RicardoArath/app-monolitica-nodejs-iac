"""
common/config.py
Configuración compartida por todos los microservicios.

Orden de carga de variables de entorno:
  1. Variables ya definidas en el proceso (systemd EnvironmentFile, shell, etc.)
  2. apps/services/.env          (archivo compartido por todos los servicios)
  3. <servicio>/.env             (opcional, solo valores propios del servicio)

Los secretos (JWT_SECRET_KEY, contraseña de Redis y PostgreSQL) NUNCA se
escriben en el código: si JWT_SECRET_KEY no está definida, el servicio no arranca.
"""
import os

from dotenv import load_dotenv

SERVICES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# override=False: lo definido en el entorno real siempre tiene prioridad
load_dotenv(os.path.join(SERVICES_DIR, '.env'), override=False)
load_dotenv(os.path.join(os.getcwd(), '.env'), override=False)


def _require(name, min_length=1):
    value = os.getenv(name, '').strip()
    if len(value) < min_length:
        raise RuntimeError(
            f"Variable de entorno obligatoria '{name}' no definida o demasiado corta "
            f"(mínimo {min_length} caracteres). Configúrela en apps/services/.env "
            f"o en el EnvironmentFile de systemd."
        )
    return value


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# --- Entorno ---
APP_ENV = os.getenv('APP_ENV', 'development').strip().lower()
IS_PRODUCTION = APP_ENV == 'production'
FLASK_DEBUG = _bool('FLASK_DEBUG', False)

# --- PostgreSQL (fuente principal de datos) ---
PGHOST = os.getenv('PGHOST', 'localhost')
PGPORT = int(os.getenv('PGPORT', '5432'))
PGDATABASE = os.getenv('PGDATABASE', 'libreria_online')
PGUSER = os.getenv('PGUSER', 'libreria_app')
PGPASSWORD = os.getenv('PGPASSWORD', '')
PG_POOL_MIN = int(os.getenv('PG_POOL_MIN', '1'))
PG_POOL_MAX = int(os.getenv('PG_POOL_MAX', '10'))

# --- Redis (capa compartida: sesiones, refresh tokens, revocación, caché, locks) ---
# Formato: redis://:password@host:6379/0
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
REDIS_SOCKET_TIMEOUT = float(os.getenv('REDIS_SOCKET_TIMEOUT', '1.0'))
REDIS_CONNECT_TIMEOUT = float(os.getenv('REDIS_CONNECT_TIMEOUT', '1.0'))
REDIS_MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', '20'))
REDIS_PROTOCOL = int(os.getenv('REDIS_PROTOCOL', '2'))


# --- JWT (secreto compartido por TODOS los servicios) ---
def _require_secret(names, min_length=32):
    for name in names:
        val = (os.getenv(name) or '').strip()
        if len(val) >= min_length:
            return val
    raise RuntimeError(
        f"Variables de entorno para secreto JWT ({', '.join(names)}) no definidas o "
        f"menores a {min_length} caracteres. Configúrela en apps/services/.env."
    )

JWT_SECRET_KEY = _require_secret(['JWT_SECRET_KEY', 'JWT_SECRET'], min_length=32)
JWT_SECRET = JWT_SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_ISSUER = os.getenv('JWT_ISSUER', 'libreria-login-service')
ACCESS_TOKEN_MINUTES = int(os.getenv('ACCESS_TOKEN_MINUTES', '20'))
REFRESH_TOKEN_DAYS = int(os.getenv('REFRESH_TOKEN_DAYS', '7'))
# Umbral para indicar al cliente que debe renovar el token antes de que caduque
TOKEN_RENEW_THRESHOLD_SECONDS = int(os.getenv('TOKEN_RENEW_THRESHOLD_SECONDS', '300'))

# --- TTLs coherentes en Redis (segundos) ---
SESSION_TTL_SECONDS = int(os.getenv('SESSION_TTL_SECONDS', '7200'))            # 2 h
REFRESH_TTL_SECONDS = REFRESH_TOKEN_DAYS * 24 * 3600                          # 7 días
CACHE_TTL_BOOKS_LIST = int(os.getenv('CACHE_TTL_BOOKS_LIST', '300'))          # 5 min
CACHE_TTL_BOOK_DETAIL = int(os.getenv('CACHE_TTL_BOOK_DETAIL', '900'))        # 15 min
CACHE_TTL_CATALOGS = int(os.getenv('CACHE_TTL_CATALOGS', '600'))              # 10 min
CACHE_TTL_AUTHORS = int(os.getenv('CACHE_TTL_AUTHORS', '300'))                # 5 min
IDEMPOTENCY_TTL_SECONDS = int(os.getenv('IDEMPOTENCY_TTL_SECONDS', '86400'))  # 24 h
ORDER_PENDING_TTL_MINUTES = int(os.getenv('ORDER_PENDING_TTL_MINUTES', '30'))

# --- CORS: solo orígenes de las aplicaciones cliente ---
CORS_ORIGINS = [
    o.strip() for o in os.getenv(
        'CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000'
    ).split(',') if o.strip()
]

# --- HTTPS opcional (certificado y llave PEM) ---
SSL_CERT_FILE = os.getenv('SSL_CERT_FILE', '').strip()
SSL_KEY_FILE = os.getenv('SSL_KEY_FILE', '').strip()

# --- Roles (tabla roles) ---
ROLE_ADMIN = 1
ROLE_USER = 2
ROLE_NAMES = {ROLE_ADMIN: 'admin', ROLE_USER: 'user'}
ROLE_IDS = {v: k for k, v in ROLE_NAMES.items()}

# --- Mapeo Oficial de Puertos (Diagrama Oficial de Arquitectura) ---
DEFAULT_PORTS = {
    'LOGIN': 5000,
    'BOOKS': 5001,
    'PAGOS': 5002,
    'PEDIDOS': 5003,
    'USERS': 5004,
    'AUTHORS': 5005,
}


def service_port(env_key, default=None):
    """Puerto del servicio: <SERVICIO>_PORT (p.ej. BOOKS_PORT) o el valor por defecto oficial."""
    def_val = default if default is not None else DEFAULT_PORTS.get(env_key.upper(), 5000)
    return int(os.getenv(f'{env_key.upper()}_PORT', str(def_val)))
