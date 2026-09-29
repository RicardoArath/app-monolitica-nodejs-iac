"""
config.py
Configuración para el microservicio de libros (puerto 5001).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- PostgreSQL ---
PGHOST = os.getenv('PGHOST', 'localhost')
PGPORT = int(os.getenv('PGPORT', '5432'))
PGDATABASE = os.getenv('PGDATABASE', 'libreria_online')
PGUSER = os.getenv('PGUSER', 'libreria_app')
PGPASSWORD = os.getenv('PGPASSWORD', 'libreria_app_pass')

# --- Flask ---
PORT = int(os.getenv('PORT', '5001'))
BASE_URL = os.getenv('BASE_URL', f'http://localhost:{PORT}')

# --- JWT (mismo secreto que el servicio de login) ---
JWT_SECRET = os.getenv('JWT_SECRET', 'libreria-jwt-secret-2026-seguro-key-32b')
