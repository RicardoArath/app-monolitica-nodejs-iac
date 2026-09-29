"""
config.py
Carga de variables de entorno para el microservicio API.
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
PORT = int(os.getenv('PORT', '5001'))

# --- URL base ---
BASE_URL = os.getenv('BASE_URL', f'http://localhost:{PORT}')

# --- JWT ---
JWT_SECRET = os.getenv('JWT_SECRET', 'libreria-jwt-secret-2026-seguro')
