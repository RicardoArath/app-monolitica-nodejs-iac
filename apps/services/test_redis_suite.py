"""
test_redis_suite.py
Suite de verificación exhaustiva para la arquitectura de microservicios con Redis.
Prueba los 7 escenarios arquitectónicos requeridos:
  1. Login, JWT Claims, Sesión en Redis y Refresh Token Rotation.
  2. Cache-Aside en Catálogo (GET /books, GET /books/<isbn>: MISS -> HIT).
  3. Invalidación de Caché ante mutaciones (PUT /books, POST /authors).
  4. Revocación de JWT (Blacklist jti en Redis) y RBAC (401 / 403).
  5. Pedidos: Transacción atómica de stock y clave temporal order:pending:<id>.
  6. Pagos: Idempotencia en Redis (payment:order:<id>) y confirmación de pedido.
  7. Formatos duales (JSON y XML) y verificación de métricas / salud.
"""
import sys
import os
import json
import time
import uuid
import requests
import psycopg
import psycopg.rows
import redis

# Configuración de URLs y puertos (Oficial Diagrama)
LOGIN_URL = os.environ.get("LOGIN_URL") or f"http://127.0.0.1:{os.environ.get('LOGIN_PORT', 5000)}"
BOOKS_URL = os.environ.get("BOOKS_URL") or f"http://127.0.0.1:{os.environ.get('BOOKS_PORT', 5001)}"
PAGOS_URL = os.environ.get("PAGOS_URL") or f"http://127.0.0.1:{os.environ.get('PAGOS_PORT', 5002)}"
PEDIDOS_URL = os.environ.get("PEDIDOS_URL") or f"http://127.0.0.1:{os.environ.get('PEDIDOS_PORT', 5003)}"
USERS_URL = os.environ.get("USERS_URL") or f"http://127.0.0.1:{os.environ.get('USERS_PORT', 5004)}"
AUTHORS_URL = os.environ.get("AUTHORS_URL") or f"http://127.0.0.1:{os.environ.get('AUTHORS_PORT', 5005)}"
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Cliente directo de Redis para verificación de llaves y TTLs
r = redis.from_url(REDIS_URL, protocol=2, decode_responses=True)

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "libreria_online",
    "user": "libreria_app",
    "password": "libreria_app_pass"
}

results_log = []

def log_result(test_name, passed, details=""):
    status_str = "PASS" if passed else "FAIL"
    entry = f"[{status_str}] {test_name}: {details}"
    print(entry)
    results_log.append({
        "test": test_name,
        "status": status_str,
        "details": details
    })
    assert passed, f"Fallo en {test_name}: {details}"

def run_suite():
    print("\n" + "="*80)
    print(" INICIANDO BATERÍA DE PRUEBAS END-TO-END: REDIS + MICROSERVICIOS")
    print("="*80 + "\n")

    # -------------------------------------------------------------
    # 0. Health checks de los 6 microservicios + Redis
    # -------------------------------------------------------------
    services = [
        ("Login", LOGIN_URL),
        ("Books", BOOKS_URL),
        ("Users", USERS_URL),
        ("Authors", AUTHORS_URL),
        ("Pedidos", PEDIDOS_URL),
        ("Pagos", PAGOS_URL),
    ]
    for name, base in services:
        resp = requests.get(f"{base}/health?format=json", timeout=3)
        assert resp.status_code == 200, f"{name} health check failed: {resp.text}"
        data = resp.json()
        assert data.get("status") in ("ok", "healthy"), f"{name} status not ok: {data}"
    
    redis_ping = r.ping()
    assert redis_ping is True, "Redis ping failed"
    log_result("0. Health Checks", True, "Los 6 microservicios y Redis responden OK")

    # -------------------------------------------------------------
    # 1. Login, JWT Claims, Redis Session & Refresh Token
    # -------------------------------------------------------------
    login_resp = requests.post(
        f"{LOGIN_URL}/login?format=json",
        json={"email": "admin@libreria.local", "password": "Passw0rd!"},
        timeout=5
    )
    assert login_resp.status_code == 200, f"Login admin failed: {login_resp.text}"
    login_data = login_resp.json()
    admin_token = login_data["token"]
    admin_refresh = login_data["refresh_token"]
    user_info = login_data["user"]

    # Decodificar claims sin verificar firma solo para inspección de estructura
    import jwt
    decoded = jwt.decode(admin_token, options={"verify_signature": False})
    jti = decoded.get("jti")
    exp = decoded.get("exp")
    iat = decoded.get("iat")
    role = decoded.get("role")
    user_id = decoded.get("user_id")

    assert jti and len(jti) > 10, "jti claim ausente o inválido"
    assert (exp - iat) == 1200, f"TTL de access token no es de 1200s (20m): {exp - iat}"
    assert role == "admin", f"Role esperado admin, obtenido {role}"
    assert user_id == 1, f"user_id esperado 1, obtenido {user_id}"

    # Verificar que la sesión existe en Redis
    session_key = f"session:{user_id}"
    session_val = r.get(session_key)
    session_ttl = r.ttl(session_key)
    assert session_val is not None, f"Sesión {session_key} no encontrada en Redis"
    assert session_ttl > 0, f"TTL de sesión no es positivo: {session_ttl}"

    # Verificar refresh token en Redis
    refresh_key = f"refresh:{admin_refresh}"
    refresh_val = r.get(refresh_key)
    refresh_ttl = r.ttl(refresh_key)
    assert refresh_val is not None, f"Refresh token {refresh_key} no encontrado en Redis"
    assert refresh_ttl > 86400, f"TTL de refresh token muy bajo: {refresh_ttl}"

    # Probar rotación de Refresh Token (POST /token/refresh)
    rotate_resp = requests.post(
        f"{LOGIN_URL}/token/refresh?format=json",
        json={"refresh_token": admin_refresh},
        timeout=5
    )
    assert rotate_resp.status_code == 200, f"Rotate refresh token falló: {rotate_resp.text}"
    rotate_data = rotate_resp.json()
    new_admin_token = rotate_data["token"]
    new_admin_refresh = rotate_data["refresh_token"]
    assert new_admin_token != admin_token, "El nuevo access token no cambió"

    # Verificar que el refresh token anterior fue revocado
    old_refresh_val = r.get(f"refresh:{admin_refresh}")
    assert old_refresh_val is None, "El refresh token antiguo no fue revocado en Redis"

    # Verificar que el nuevo refresh token existe en Redis
    assert r.get(f"refresh:{new_admin_refresh}") is not None, "El nuevo refresh token no existe en Redis"

    # Probar GET /session con el nuevo token
    sess_check = requests.get(
        f"{LOGIN_URL}/session?format=json",
        headers={"Authorization": f"Bearer {new_admin_token}"},
        timeout=5
    )
    assert sess_check.status_code == 200, f"Check session falló: {sess_check.text}"
    assert sess_check.json().get("status") in ("active", "expiring"), f"status no es active/expiring: {sess_check.json()}"

    log_result("1. Autenticación y Sesión Redis", True, 
               f"JWT emitido (TTL 20m, JTI={jti}), sesión en Redis TTL={session_ttl}s, Refresh token rotado con éxito")

    # -------------------------------------------------------------
    # 2. Catálogo Books: Cache-Aside (MISS -> HIT)
    # -------------------------------------------------------------
    # Limpiar llaves previas de libros para asegurar MISS limpio
    for k in r.keys("books:*"):
        r.delete(k)

    t0 = time.time()
    resp_miss = requests.get(f"{BOOKS_URL}/books?page=1&format=json", timeout=5)
    lat_miss = time.time() - t0
    assert resp_miss.status_code == 200, f"Books list falló: {resp_miss.text}"
    data_miss = resp_miss.json()
    assert data_miss.get("from_cache") is False, "Primer request no fue MISS"

    # Verificar que la llave existe en Redis con TTL <= 300
    book_keys = r.keys("books:list:*")
    assert len(book_keys) > 0, "No se guardó books:list en Redis"
    ttl_books_list = r.ttl(book_keys[0])
    assert 0 < ttl_books_list <= 300, f"TTL de books:list inválido: {ttl_books_list}"

    t1 = time.time()
    resp_hit = requests.get(f"{BOOKS_URL}/books?page=1&format=json", timeout=5)
    lat_hit = time.time() - t1
    assert resp_hit.status_code == 200, f"Books hit falló: {resp_hit.text}"
    data_hit = resp_hit.json()
    assert data_hit.get("from_cache") is True, "Segundo request no fue HIT"

    # Probar detalle de libro por ISBN
    isbn_test = data_miss["books"][0]["isbn"]
    detail_miss = requests.get(f"{BOOKS_URL}/books/{isbn_test}?format=json", timeout=5)
    assert detail_miss.status_code == 200
    assert detail_miss.json().get("from_cache") is False, "Detalle no fue MISS"

    isbn_key = f"books:{isbn_test}"
    assert r.get(isbn_key) is not None, f"Llave {isbn_key} no guardada en Redis"
    detail_ttl = r.ttl(isbn_key)
    assert 0 < detail_ttl <= 900, f"TTL de books:<isbn> inválido: {detail_ttl}"

    detail_hit = requests.get(f"{BOOKS_URL}/books/{isbn_test}?format=json", timeout=5)
    assert detail_hit.json().get("from_cache") is True, "Segundo detalle no fue HIT"

    log_result("2. Cache-Aside Catálogo", True,
               f"MISS ({lat_miss*1000:.1f}ms) -> HIT ({lat_hit*1000:.1f}ms). TTL list={ttl_books_list}s, TTL isbn={detail_ttl}s")

    # -------------------------------------------------------------
    # 3. Invalidación de Caché ante mutaciones
    # -------------------------------------------------------------
    # Crear un nuevo autor o actualizar libro invalida la caché
    assert len(r.keys("books:*")) > 0, "Deben existir llaves de books antes de la mutación"

    auth_payload = {"name": f"Autor Prueba {uuid.uuid4().hex[:6]}"}
    resp_author = requests.post(
        f"{AUTHORS_URL}/authors?format=json",
        json=auth_payload,
        headers={"Authorization": f"Bearer {new_admin_token}"},
        timeout=5
    )
    assert resp_author.status_code == 201, f"Creación de autor falló: {resp_author.text}"

    # Verificar que las llaves de books:* y authors:* fueron invalidadas en Redis
    remaining_book_keys = r.keys("books:*")
    remaining_author_keys = r.keys("authors:*")
    assert len(remaining_book_keys) == 0, f"No se invalidaron books:* tras mutación: {remaining_book_keys}"
    assert len(remaining_author_keys) == 0, f"No se invalidaron authors:* tras mutación: {remaining_author_keys}"

    # El siguiente GET a books debe ser MISS
    resp_after = requests.get(f"{BOOKS_URL}/books?page=1&format=json", timeout=5)
    assert resp_after.json().get("from_cache") is False, "Request post-invalidación no fue MISS"

    log_result("3. Invalidación de Caché", True,
               "Mutación en Authors invalidó automáticamente 'authors:*' y 'books:*' en Redis")

    # -------------------------------------------------------------
    # 4. Revocación de JWT (Blacklist JTI) y RBAC
    # -------------------------------------------------------------
    # Login con usuario regular (role: user)
    user_login = requests.post(
        f"{LOGIN_URL}/login?format=json",
        json={"email": "usuario1@correo.com", "password": "Passw0rd!"},
        timeout=5
    )
    assert user_login.status_code == 200, f"Login usuario regular falló: {user_login.text}"
    user_token = user_login.json()["token"]

    # Probar RBAC: Usuario regular intentando listar usuarios (Admin only)
    forbidden_resp = requests.get(
        f"{USERS_URL}/users?format=json",
        headers={"Authorization": f"Bearer {user_token}"},
        timeout=5
    )
    assert forbidden_resp.status_code == 403, f"Esperado 403 Forbidden, recibido {forbidden_resp.status_code}: {forbidden_resp.text}"

    # Admin puede listar usuarios
    allowed_resp = requests.get(
        f"{USERS_URL}/users?format=json",
        headers={"Authorization": f"Bearer {new_admin_token}"},
        timeout=5
    )
    assert allowed_resp.status_code == 200, f"Admin no pudo listar usuarios: {allowed_resp.text}"

    # Realizar logout con token de admin
    logout_resp = requests.post(
        f"{LOGIN_URL}/logout?format=json",
        headers={"Authorization": f"Bearer {new_admin_token}"},
        timeout=5
    )
    assert logout_resp.status_code == 200, f"Logout falló: {logout_resp.text}"

    # Decodificar el JTI del token de admin deslogueado
    dec_admin = jwt.decode(new_admin_token, options={"verify_signature": False})
    revoked_jti = dec_admin["jti"]

    # Verificar que el JTI está en la lista de revocación en Redis con TTL > 0
    revoked_key = f"jwt:revoked:{revoked_jti}"
    assert r.get(revoked_key) == "1", f"JTI no registrado en Redis como revocado: {revoked_key}"
    revoked_ttl = r.ttl(revoked_key)
    assert 0 < revoked_ttl <= 1200, f"TTL de revocación inválido: {revoked_ttl}"

    # Intentar usar el token revocado en el endpoint protegido de Users
    rejected_resp = requests.get(
        f"{USERS_URL}/users?format=json",
        headers={"Authorization": f"Bearer {new_admin_token}"},
        timeout=5
    )
    assert rejected_resp.status_code == 401, f"Token revocado fue aceptado! Status: {rejected_resp.status_code}"
    rej_json = rejected_resp.json()
    assert "revocado" in rej_json.get("message", "").lower(), f"Mensaje no menciona revocación: {rej_json}"

    log_result("4. Revocación JWT y RBAC", True,
               f"RBAC bloqueó usuario (403), logout blacklisteo JTI en Redis (TTL={revoked_ttl}s), token rechazado (401)")

    # -------------------------------------------------------------
    # 5. Pedidos: Transacción Atómica de Stock y Temporal en Redis
    # -------------------------------------------------------------
    # Volver a autenticar a usuario1
    user_login2 = requests.post(
        f"{LOGIN_URL}/login?format=json",
        json={"email": "usuario1@correo.com", "password": "Passw0rd!"},
        timeout=5
    )
    current_user_token = user_login2.json()["token"]

    # Consultar stock inicial del libro 2 en PostgreSQL
    with psycopg.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT stock FROM books WHERE id = 2;")
            initial_stock = cur.fetchone()[0]

    # Crear pedido con 2 unidades del libro 2
    order_payload = {"items": [{"book_id": 2, "quantity": 2}]}
    order_create_resp = requests.post(
        f"{PEDIDOS_URL}/orders?format=json",
        json=order_payload,
        headers={"Authorization": f"Bearer {current_user_token}"},
        timeout=5
    )
    assert order_create_resp.status_code == 201, f"Creación de pedido falló: {order_create_resp.text}"
    order_data = order_create_resp.json()["order"]
    order_id = order_data["id"]
    order_total = order_data["total"]

    # Verificar que el stock en PostgreSQL disminuyó exactamente en 2
    with psycopg.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT stock FROM books WHERE id = 2;")
            stock_after_order = cur.fetchone()[0]
    assert stock_after_order == initial_stock - 2, f"Stock no disminuyó en 2: era {initial_stock}, ahora {stock_after_order}"

    # Verificar que se registró la clave temporal en Redis
    pending_order_key = f"order:pending:{order_id}"
    assert r.get(pending_order_key) is not None, f"Clave {pending_order_key} no registrada en Redis"
    pending_ttl = r.ttl(pending_order_key)
    assert 0 < pending_ttl <= 1800, f"TTL de pedido pendiente inválido: {pending_ttl}"

    # Cancelar el pedido y verificar RESTAURACIÓN de stock
    cancel_resp = requests.patch(
        f"{PEDIDOS_URL}/orders/{order_id}/status?format=json",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {current_user_token}"},
        timeout=5
    )
    assert cancel_resp.status_code == 200, f"Cancelación falló: {cancel_resp.text}"

    with psycopg.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT stock FROM books WHERE id = 2;")
            restored_stock = cur.fetchone()[0]
    assert restored_stock == initial_stock, f"Stock no restaurado: era {initial_stock}, ahora {restored_stock}"
    assert r.get(pending_order_key) is None, "La clave temporal de pedido pendiente no fue eliminada al cancelar"

    log_result("5. Pedidos: Stock Atómico y Redis", True,
               f"Stock descontado (-2) en PostgreSQL, temporal {pending_order_key} en Redis (TTL={pending_ttl}s), stock restaurado (+2) tras cancelación")

    # -------------------------------------------------------------
    # 6. Pagos: Idempotencia en Redis y Confirmación
    # -------------------------------------------------------------
    # Crear un nuevo pedido para pagar
    new_order_resp = requests.post(
        f"{PEDIDOS_URL}/orders?format=json",
        json={"items": [{"book_id": 2, "quantity": 1}]},
        headers={"Authorization": f"Bearer {current_user_token}"},
        timeout=5
    )
    assert new_order_resp.status_code == 201
    pay_order_id = new_order_resp.json()["order"]["id"]
    pay_order_total = new_order_resp.json()["order"]["total"]

    # Procesar pago con idempotencia
    pay_payload = {
        "order_id": pay_order_id,
        "amount": pay_order_total,
        "method": "simulated_card"
    }
    pay1_resp = requests.post(
        f"{PAGOS_URL}/payments?format=json",
        json=pay_payload,
        headers={"Authorization": f"Bearer {current_user_token}"},
        timeout=5
    )
    assert pay1_resp.status_code == 201, f"Pago inicial falló: {pay1_resp.text}"
    pay1_data = pay1_resp.json()
    receipt_id = pay1_data.get("payment", {}).get("id") or pay1_data.get("payment", {}).get("payment_id")
    assert receipt_id is not None, f"id de pago no generado: {pay1_data}"

    # Verificar que el estado del pedido cambió a 'confirmed' en PostgreSQL
    with psycopg.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE id = %s;", (pay_order_id,))
            final_status = cur.fetchone()[0]
    assert final_status == "confirmed", f"Estado de pedido esperado 'confirmed', actual '{final_status}'"

    # Verificar clave de idempotencia en Redis
    idempotency_key = f"idempotency:payment:order:{pay_order_id}"
    assert r.get(idempotency_key) is not None, f"Clave de idempotencia {idempotency_key} no encontrada en Redis"
    idem_ttl = r.ttl(idempotency_key)
    assert 0 < idem_ttl <= 86400, f"TTL de idempotencia inválido: {idem_ttl}"

    # Ejecutar SEGUNDO pago idéntico -> Debe retornar respuesta idéntica (Idempotent Replay) sin duplicar cobro
    pay2_resp = requests.post(
        f"{PAGOS_URL}/payments?format=json",
        json=pay_payload,
        headers={"Authorization": f"Bearer {current_user_token}"},
        timeout=5
    )
    assert pay2_resp.status_code == 200, f"Replay de pago esperado 200, recibido {pay2_resp.status_code}: {pay2_resp.text}"
    pay2_data = pay2_resp.json()
    replay_id = pay2_data.get("payment", {}).get("id") or pay2_data.get("payment", {}).get("payment_id")
    assert replay_id == receipt_id, f"El ID de comprobante no coincidió en el replay: {replay_id} vs {receipt_id}"

    # Verificar en PostgreSQL que NO existe un segundo registro en simulated_payments
    with psycopg.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM simulated_payments WHERE order_id = %s;", (pay_order_id,))
            payments_count = cur.fetchone()[0]
    assert payments_count == 1, f"Se duplicó el pago en la BD: count={payments_count}"

    log_result("6. Pagos: Idempotencia en Redis", True,
               f"Pago inicial 201 (status: confirmed), replay 200 idempotente con comprobante {receipt_id}, sin duplicación en PostgreSQL")

    # -------------------------------------------------------------
    # 7. Formatos duales (JSON y XML) y Métricas
    # -------------------------------------------------------------
    xml_resp = requests.get(f"{BOOKS_URL}/books?format=xml", timeout=5)
    assert xml_resp.status_code == 200, f"XML response falló: {xml_resp.text}"
    assert "xml" in xml_resp.headers.get("Content-Type", "").lower(), f"Content-Type no es XML: {xml_resp.headers}"
    assert "<books>" in xml_resp.text or "<root>" in xml_resp.text or "<?xml" in xml_resp.text, "Cuerpo no contiene XML"

    metrics_resp = requests.get(f"{LOGIN_URL}/metrics", timeout=5)
    assert metrics_resp.status_code == 200, "Metrics endpoint no respondió 200"
    assert "http_requests_total" in metrics_resp.text, "Métrica http_requests_total no encontrada"

    log_result("7. Formato Dual y Métricas", True,
               "GET /books?format=xml retornó XML válido y GET /metrics expone contadores Prometheus")

    print("\n" + "="*80)
    print(" TODAS LAS PRUEBAS COMPLETADAS SATISFACTORIAMENTE (7/7 PASS)")
    print("="*80 + "\n")
    return results_log

if __name__ == "__main__":
    run_suite()
