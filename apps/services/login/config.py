"""
config.py
Carga de variables de entorno para el microservicio de autenticación.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- PostgreSQL ---
PGHOST = os.getenv('PGHOST', 'localhost')
PGPORT = int(os.getenv('PGPORT', '5432'))
PGDATABASE = os.getenv('PGDATABASE', 'libreria_online')
PGUSER = os.getenv('PGUSER', 'libreria_app')
PGPASSWORD = os.getenv('PGPASSWORD', '')

# --- Flask ---
PORT = int(os.getenv('PORT', '5000'))
SESSION_SECRET = os.getenv('SESSION_SECRET', 'dev-secret-cambiar')

# --- Sesiones (minutos) ---
SESSION_LIFETIME_MINUTES = int(os.getenv('SESSION_LIFETIME_MINUTES', '30'))
SESSION_WARNING_MINUTES = int(os.getenv('SESSION_WARNING_MINUTES', '5'))

# --- Correo (Postfix local) ---
MAIL_FROM = os.getenv('MAIL_FROM', 'noreply@libreria.local')
MAIL_SMTP_HOST = os.getenv('MAIL_SMTP_HOST', 'localhost')
MAIL_SMTP_PORT = int(os.getenv('MAIL_SMTP_PORT', '25'))

# --- URL base ---
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

# --- JWT ---
JWT_SECRET = os.getenv('JWT_SECRET', 'libreria-jwt-secret-2026-seguro-key-32b')
JWT_EXPIRY_MINUTES = int(os.getenv('JWT_EXPIRY_MINUTES', '60'))
