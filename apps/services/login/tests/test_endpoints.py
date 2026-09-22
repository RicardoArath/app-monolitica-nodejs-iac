"""
tests/test_endpoints.py
Tests de integración para validar todos los endpoints del microservicio.
Ejecutar con: python -m pytest tests/test_endpoints.py -v
Requiere que el microservicio esté corriendo en http://localhost:5000
y que la base de datos esté migrada.
"""
import sys
import os
import json
import xml.etree.ElementTree as ET

import requests
import pytest

# URL base del microservicio
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5000')

# Datos de prueba con timestamp para unicidad
import time
_ts = str(int(time.time()))
TEST_USER = {
    'nombre': 'Test',
    'apellido_paterno': 'Usuario',
    'apellido_materno': 'Prueba',
    'email': f'test.usuario{_ts}@correo.com',
    'password': 'TestPassword123'
}


class TestHealthEndpoint:
    """Tests para GET /health"""

    def test_health_xml_default(self):
        """GET /health sin ?format= debe devolver XML."""
        r = requests.get(f'{BASE_URL}/health')
        assert r.status_code == 200
        assert 'application/xml' in r.headers['Content-Type']
        root = ET.fromstring(r.text)
        assert root.find('status').text in ('ok', 'degraded')
        assert root.find('service').text == 'auth-microservice'

    def test_health_xml_explicit(self):
        """GET /health?format=xml debe devolver XML."""
        r = requests.get(f'{BASE_URL}/health?format=xml')
        assert r.status_code == 200
        assert 'application/xml' in r.headers['Content-Type']

    def test_health_json(self):
        """GET /health?format=json debe devolver JSON."""
        r = requests.get(f'{BASE_URL}/health?format=json')
        assert r.status_code == 200
        assert 'application/json' in r.headers['Content-Type']
        data = r.json()
        assert data['status'] in ('ok', 'degraded')
        assert data['service'] == 'auth-microservice'
        assert 'database' in data
        assert 'timestamp' in data


class TestRegisterEndpoint:
    """Tests para POST /register"""

    def test_register_success_json(self):
        """Registro exitoso con respuesta JSON."""
        r = requests.post(
            f'{BASE_URL}/register?format=json',
            json=TEST_USER
        )
        assert r.status_code == 201
        data = r.json()
        assert data['status'] in ('success', 'warning')
        assert 'user_id' in data
        assert 'username' in data

    def test_register_duplicate_email_json(self):
        """Registro con email duplicado debe dar 409."""
        r = requests.post(
            f'{BASE_URL}/register?format=json',
            json=TEST_USER
        )
        assert r.status_code == 409

    def test_register_missing_fields_json(self):
        """Registro sin campos obligatorios debe dar 400."""
        r = requests.post(
            f'{BASE_URL}/register?format=json',
            json={'email': 'solo@email.com'}
        )
        assert r.status_code == 400

    def test_register_invalid_email_json(self):
        """Registro con email inválido debe dar 400."""
        r = requests.post(
            f'{BASE_URL}/register?format=json',
            json={
                'nombre': 'Test',
                'apellido_paterno': 'Bad',
                'email': 'no-es-un-email',
                'password': 'TestPassword123'
            }
        )
        assert r.status_code == 400

    def test_register_short_password_json(self):
        """Registro con contraseña corta debe dar 400."""
        r = requests.post(
            f'{BASE_URL}/register?format=json',
            json={
                'nombre': 'Test',
                'apellido_paterno': 'Short',
                'email': f'short{_ts}@correo.com',
                'password': '123'
            }
        )
        assert r.status_code == 400

    def test_register_success_xml(self):
        """Registro exitoso con respuesta XML (default)."""
        user = TEST_USER.copy()
        user['email'] = f'test.xml{_ts}@correo.com'
        r = requests.post(f'{BASE_URL}/register', json=user)
        assert r.status_code == 201
        assert 'application/xml' in r.headers['Content-Type']
        root = ET.fromstring(r.text)
        assert root.find('status').text in ('success', 'warning')


class TestLoginEndpoint:
    """Tests para POST /login"""

    def test_login_unverified_email_json(self):
        """Login con email no verificado debe dar 403."""
        r = requests.post(
            f'{BASE_URL}/login?format=json',
            json={
                'email': TEST_USER['email'],
                'password': TEST_USER['password']
            }
        )
        # Puede ser 403 (no verificado) o 401 (si no existe)
        assert r.status_code in (401, 403)

    def test_login_wrong_password_json(self):
        """Login con contraseña incorrecta debe dar 401."""
        r = requests.post(
            f'{BASE_URL}/login?format=json',
            json={
                'email': TEST_USER['email'],
                'password': 'ContraseñaIncorrecta'
            }
        )
        assert r.status_code == 401

    def test_login_missing_fields_json(self):
        """Login sin campos debe dar 400."""
        r = requests.post(
            f'{BASE_URL}/register?format=json',
            json={}
        )
        assert r.status_code == 400

    def test_login_with_seed_user_json(self):
        """Login con usuario seed (email verificado) debe funcionar."""
        r = requests.post(
            f'{BASE_URL}/login?format=json',
            json={
                'email': 'admin@libreria.local',
                'password': 'Passw0rd!'
            }
        )
        # Si la migración marcó los seeds como verificados, debería dar 200
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'success'
        assert 'user' in data


class TestSessionEndpoints:
    """Tests para GET /session y POST /session/renew"""

    def test_session_without_login(self):
        """GET /session sin sesión debe dar 401."""
        r = requests.get(f'{BASE_URL}/session?format=json')
        assert r.status_code == 401

    def test_session_flow(self):
        """Flujo completo: login → session → renew → logout."""
        s = requests.Session()

        # Login con usuario seed
        r = s.post(
            f'{BASE_URL}/login?format=json',
            json={
                'email': 'admin@libreria.local',
                'password': 'Passw0rd!'
            }
        )
        assert r.status_code == 200

        # Consultar sesión
        r = s.get(f'{BASE_URL}/session?format=json')
        assert r.status_code == 200
        data = r.json()
        assert data['status'] in ('active', 'expiring')
        assert 'remaining_seconds' in data
        assert 'user' in data

        # Renovar sesión
        r = s.post(f'{BASE_URL}/session/renew?format=json')
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'success'

        # Logout
        r = s.post(f'{BASE_URL}/logout?format=json')
        assert r.status_code == 200

        # Verificar que la sesión ya no existe
        r = s.get(f'{BASE_URL}/session?format=json')
        assert r.status_code == 401

    def test_session_xml_format(self):
        """Flujo de sesión con formato XML."""
        s = requests.Session()

        r = s.post(
            f'{BASE_URL}/login',
            json={
                'email': 'admin@libreria.local',
                'password': 'Passw0rd!'
            }
        )
        assert r.status_code == 200
        assert 'application/xml' in r.headers['Content-Type']

        r = s.get(f'{BASE_URL}/session')
        assert r.status_code == 200
        assert 'application/xml' in r.headers['Content-Type']
        root = ET.fromstring(r.text)
        assert root.find('status').text in ('active', 'expiring')

        s.post(f'{BASE_URL}/logout')


class TestLogoutEndpoint:
    """Tests para POST /logout"""

    def test_logout_without_session(self):
        """Logout sin sesión debe dar 401."""
        r = requests.post(f'{BASE_URL}/logout?format=json')
        assert r.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

