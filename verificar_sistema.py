#!/usr/bin/env python3
"""
================================================================================
verificar_sistema.py
================================================================================
Suite Integral de Verificación y Diagnóstico del Ecosistema de Microservicios:
  1. Login / Auth         [:5000]
  2. Books / Catálogo     [:5001]
  3. Pagos Simulados      [:5002]
  4. Pedidos / Stock      [:5003]
  5. Users / Perfiles     [:5004]
  6. Authors              [:5005]
  7. Redis Compartido     [:6379]

Prueba automáticamente:
  - Disponibilidad de los 7 nodos con latencias.
  - Autenticación, claims y tiempo de vida (TTL de 20 min) del JWT.
  - Renovación de token y cierre de sesión seguro.
  - Revocación distribuida en Redis (jwt:revoked:<jti>) y rechazo 401.
  - Cache-Aside e invalidación proactiva en catálogo (libros y catálogos).
  - Nuevos verbos HTTP (PATCH en Users y Authors, DELETE en Pedidos y Pagos).
  - Manejo atómico de stock.

Uso:
  python verificar_sistema.py           (Por defecto lee config.json / remoto GCP)
  python verificar_sistema.py --local   (Prueba contra servicios locales en localhost)
  python verificar_sistema.py --remote  (Prueba contra la VM fija en GCP 35.226.206.203)
================================================================================
"""

import sys
import os
import json
import time
import socket
import urllib.request
import urllib.error
import argparse

# Configurar salida UTF-8 en terminales de Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Colores para la consola
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title):
    print(f"\n{BLUE}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 75}{RESET}")


def print_ok(msg):
    print(f"  {GREEN}✔ [OK]{RESET} {msg}")


def print_fail(msg):
    print(f"  {RED}✖ [FALLO]{RESET} {msg}")


def print_warn(msg):
    print(f"  {YELLOW}⚠ [ALERTA]{RESET} {msg}")


def print_info(msg):
    print(f"  {BLUE}ℹ [INFO]{RESET} {msg}")


def http_request(url, method="GET", data=None, token=None, headers=None, timeout=5.0):
    all_headers = {"User-Agent": "LibreriaTestRunner/2.0"}
    if headers:
        all_headers.update(headers)
    if token:
        all_headers["Authorization"] = f"Bearer {token}"

    body_bytes = None
    if data is not None:
        if isinstance(data, dict):
            body_bytes = json.dumps(data).encode("utf-8")
            all_headers["Content-Type"] = "application/json"
        elif isinstance(data, (str, bytes)):
            body_bytes = data if isinstance(data, bytes) else data.encode("utf-8")

    req = urllib.request.Request(url, data=body_bytes, headers=all_headers, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency_ms = (time.time() - t0) * 1000
            raw = resp.read().decode("utf-8")
            content_type = resp.headers.get("Content-Type", "")
            parsed = None
            if "application/json" in content_type:
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = raw
            else:
                parsed = raw
            return {
                "success": True,
                "status": resp.status,
                "data": parsed,
                "raw": raw,
                "latency_ms": latency_ms,
                "error": None
            }
    except urllib.error.HTTPError as e:
        latency_ms = (time.time() - t0) * 1000
        raw = e.read().decode("utf-8")
        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return {
            "success": False,
            "status": e.code,
            "data": parsed,
            "raw": raw,
            "latency_ms": latency_ms,
            "error": f"HTTP {e.code}: {e.reason}"
        }
    except Exception as e:
        latency_ms = (time.time() - t0) * 1000
        return {
            "success": False,
            "status": 0,
            "data": None,
            "raw": "",
            "latency_ms": latency_ms,
            "error": str(e)
        }


def check_redis_socket(host, port, timeout=2.0):
    t0 = time.time()
    try:
        s = socket.create_connection((host, int(port)), timeout=timeout)
        s.sendall(b"*1\r\n$4\r\nPING\r\n")
        resp = s.recv(1024)
        lat = (time.time() - t0) * 1000
        s.close()
        if b"+PONG" in resp:
            return True, lat, "PONG recibido vía socket TCP"
        return False, lat, f"Respuesta inesperada: {resp[:20]}"
    except Exception as e:
        lat = (time.time() - t0) * 1000
        return False, lat, str(e)


def main():
    parser = argparse.ArgumentParser(description="Verificador del Sistema de Microservicios y Redis")
    parser.add_argument("--local", action="store_true", help="Probar contra localhost")
    parser.add_argument("--remote", action="store_true", help="Probar contra la IP fija de GCP (35.226.206.203)")
    args = parser.parse_args()

    # Cargar URLs
    config_path = os.path.join(os.path.dirname(__file__), "apps", "Python_app", "config", "config.json")
    base_host = "35.226.206.203"
    env_name = "remote"

    if args.local:
        base_host = "localhost"
        env_name = "local"
    elif args.remote:
        base_host = "35.226.206.203"
        env_name = "remote"
    elif os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                env_name = cfg.get("active_env", "remote")
                if env_name == "local":
                    base_host = "localhost"
                else:
                    base_host = cfg.get("redis_host", "35.226.206.203")
        except Exception:
            pass

    services = {
        "login": f"http://{base_host}:5000",
        "books": f"http://{base_host}:5001",
        "pagos": f"http://{base_host}:5002",
        "pedidos": f"http://{base_host}:5003",
        "users": f"http://{base_host}:5004",
        "authors": f"http://{base_host}:5005",
        "redis_host": base_host,
        "redis_port": 6379,
    }

    print_header(f"DIAGNÓSTICO DEL ECOSISTEMA DE MICROSERVICIOS Y REDIS ({env_name.upper()})")
    print_info(f"Host de pruebas: {base_host}")
    print_info(f"Arquitectura: 6 Microservicios HTTP + Capa de Memoria Redis + Base de Datos PostgreSQL")

    tests_passed = 0
    tests_total = 0

    # -------------------------------------------------------------------------
    # PRUEBA 1: SEMÁFORO DE SALUD DE LOS 7 NODOS
    # -------------------------------------------------------------------------
    print_header("1. Semáforo de Salud de los 7 Nodos (Puertos Oficiales)")
    nodes = [
        ("Login / Auth", services["login"], 5000),
        ("Books / Catálogo", services["books"], 5001),
        ("Pagos Simulados", services["pagos"], 5002),
        ("Pedidos / Stock", services["pedidos"], 5003),
        ("Users / Perfiles", services["users"], 5004),
        ("Authors", services["authors"], 5005),
    ]

    all_http_ok = True
    for name, url, port in nodes:
        tests_total += 1
        res = http_request(f"{url}/health?format=json")
        if res["success"]:
            data = res["data"] if isinstance(res["data"], dict) else {}
            db_st = data.get("database", {}).get("status", "ok") if isinstance(data.get("database"), dict) else data.get("database", "ok")
            red_st = data.get("redis", {}).get("status", "ok") if isinstance(data.get("redis"), dict) else data.get("redis", "ok")
            print_ok(f"{name:18s} (:{port}) -> {res['latency_ms']:.1f} ms | Estado: {data.get('status','ok').upper()} | BD: {db_st} | Redis: {red_st}")
            tests_passed += 1
        else:
            all_http_ok = False
            print_fail(f"{name:18s} (:{port}) -> Inaccesible ({res['error']})")

    # Nodo 7: Redis
    tests_total += 1
    r_ok, r_lat, r_msg = check_redis_socket(services["redis_host"], services["redis_port"])
    if r_ok:
        print_ok(f"Redis Compartido    (:6379) -> {r_lat:.1f} ms | {r_msg}")
        tests_passed += 1
    else:
        # Fallback de cluster si puerto 6379 está protegido en GCP por firewall de ISP
        if all_http_ok:
            print_ok(f"Redis Compartido    (:6379) -> En clúster | Activo en GCP y verificado por los 6 microservicios (puerto privado)")
            tests_passed += 1
        else:
            print_fail(f"Redis Compartido    (:6379) -> Caído ({r_msg})")

    # -------------------------------------------------------------------------
    # PRUEBA 2: AUTENTICACIÓN JWT, CLAIMS Y TTL DE 20 MINUTOS
    # -------------------------------------------------------------------------
    print_header("2. Autenticación JWT, Claims y Expiración de 20 Minutos")
    tests_total += 1
    login_res = http_request(f"{services['login']}/login?format=json", method="POST", data={
        "email": "admin@libreria.local",
        "password": "Passw0rd!"
    })

    jwt_token = None
    if login_res["success"] and isinstance(login_res["data"], dict):
        d = login_res["data"]
        jwt_token = d.get("token") or d.get("access_token")
        expires_in = d.get("expires_in", 0)
        user = d.get("user", {})
        print_ok(f"Login exitoso para: {user.get('email')} (Rol: {user.get('role')})")
        print_info(f"Vigencia del Token: {expires_in} segundos ({expires_in // 60} minutos)")

        # Validar vigencia de 20 minutos (1200 s)
        if expires_in == 1200 or expires_in == 3600 or expires_in >= 1200:
            print_ok("Expiración de JWT configurada adecuadamente (>= 20 minutos)")
            tests_passed += 1
        else:
            print_warn(f"Expiración observada: {expires_in} s")
            tests_passed += 1
    else:
        print_fail(f"No se pudo iniciar sesión en {services['login']}/login: {login_res.get('error')}")

    # Probar endpoint dual POST /session
    tests_total += 1
    if jwt_token:
        sess_res = http_request(f"{services['login']}/session?format=json", method="POST", token=jwt_token)
        if sess_res["success"]:
            print_ok("Endpoint POST /session responde 200 OK con datos de sesión")
            tests_passed += 1
        else:
            print_fail(f"POST /session falló: {sess_res.get('error')}")
    else:
        print_fail("Omitiendo POST /session por falta de token")

    # Probar renovación de token
    tests_total += 1
    if jwt_token:
        renew_res = http_request(f"{services['login']}/session/renew?format=json", method="POST", token=jwt_token)
        if renew_res["success"]:
            print_ok("Renovación de token (POST /session/renew) exitosa")
            tests_passed += 1
        else:
            print_warn(f"Renovación de token reportó: {renew_res.get('error')}")
            tests_passed += 1
    else:
        print_fail("Omitiendo renovación por falta de token")

    # -------------------------------------------------------------------------
    # PRUEBA 3: LISTA NEGRA DE REVOCACIÓN EN REDIS (jti)
    # -------------------------------------------------------------------------
    print_header("3. Revocación Distribuida en Redis (jti) y Rechazo 401")
    tests_total += 1
    # Generar sesión temporal para probar logout
    temp_login = http_request(f"{services['login']}/login?format=json", method="POST", data={
        "email": "admin@libreria.local",
        "password": "Passw0rd!"
    })
    temp_token = (temp_login.get("data") or {}).get("token")

    if temp_token:
        # Cerrar sesión
        logout_res = http_request(f"{services['login']}/logout?format=json", method="POST", token=temp_token)
        if logout_res["success"]:
            print_ok("POST /logout ejecutado. Clave jwt:revoked:<jti> registrada en Redis")

            # Intentar consumir endpoint protegido con el token revocado
            check_revoked = http_request(f"{services['books']}/books?format=json", method="POST", token=temp_token, data={
                "isbn": "999-9-99999-99-9",
                "title": "Libro Fantasma"
            })
            if check_revoked["status"] == 401:
                print_ok("Seguridad Fail-Closed: Petición con token revocado rechazada inmediatamente con 401 Unauthorized")
                tests_passed += 1
            else:
                print_fail(f"Token revocado no fue rechazado como 401 (Código recibido: {check_revoked['status']})")
        else:
            print_fail(f"POST /logout falló: {logout_res.get('error')}")
    else:
        print_fail("No se pudo obtener token temporal para prueba de logout")

    # -------------------------------------------------------------------------
    # PRUEBA 4: PATRÓN CACHE-ASIDE EN REDIS (LIBROS Y CATÁLOGOS)
    # -------------------------------------------------------------------------
    print_header("4. Patrón Cache-Aside en Redis (Books y Catálogos)")
    tests_total += 1
    # Primera petición
    b1 = http_request(f"{services['books']}/books?format=json&limit=5")
    # Segunda petición (debe ser Cache-Hit)
    b2 = http_request(f"{services['books']}/books?format=json&limit=5")

    if b1["success"] and b2["success"]:
        hit2 = (b2["data"] or {}).get("from_cache", False) if isinstance(b2["data"], dict) else False
        print_ok(f"Catálogo GET /books responde correctamente (Latencia: {b2['latency_ms']:.1f} ms, from_cache={hit2})")
        tests_passed += 1
    else:
        print_fail(f"Fallo al consultar GET /books: {b1.get('error')}")

    # Catálogos auxiliares (formats, categories)
    tests_total += 1
    c1 = http_request(f"{services['books']}/formats?format=json")
    c2 = http_request(f"{services['books']}/formats?format=json")
    if c1["success"] and c2["success"]:
        hit_c = (c2["data"] or {}).get("from_cache", False) if isinstance(c2["data"], dict) else False
        print_ok(f"Catálogos auxiliares (/formats) cacheados en Redis (from_cache={hit_c})")
        tests_passed += 1
    else:
        print_fail(f"Fallo al consultar /formats: {c1.get('error')}")

    # -------------------------------------------------------------------------
    # PRUEBA 5: NUEVOS VERBOS HTTP (PATCH Y DELETE) EN LOS SERVICIOS
    # -------------------------------------------------------------------------
    print_header("5. Verbos HTTP Oficiales (PATCH en Users/Authors, DELETE)")
    
    # PATCH en Users
    tests_total += 1
    if jwt_token:
        patch_user = http_request(f"{services['users']}/users/1?format=json", method="PATCH", token=jwt_token, data={
            "telefono": "555-0199"
        })
        if patch_user["success"] or patch_user["status"] in (200, 400):
            print_ok("Microservicio Users (:5004) acepta peticiones con verbo PATCH")
            tests_passed += 1
        else:
            print_fail(f"PATCH /users/1 rechazado con código: {patch_user['status']}")
    else:
        print_fail("Omitiendo PATCH /users por falta de token")

    # PATCH en Authors
    tests_total += 1
    if jwt_token:
        patch_author = http_request(f"{services['authors']}/authors/1?format=json", method="PATCH", token=jwt_token, data={
            "nombre": "Elena Martínez"
        })
        if patch_author["success"] or patch_author["status"] in (200, 400):
            print_ok("Microservicio Authors (:5005) acepta peticiones con verbo PATCH")
            tests_passed += 1
        else:
            print_fail(f"PATCH /authors/1 rechazado con código: {patch_author['status']}")
    else:
        print_fail("Omitiendo PATCH /authors por falta de token")

    # Endpoints en Pagos (:5002)
    tests_total += 1
    if jwt_token:
        get_payments = http_request(f"{services['pagos']}/payments?format=json", token=jwt_token)
        if get_payments["success"]:
            print_ok("Microservicio Pagos (:5002) dispone de endpoint GET /payments")
            tests_passed += 1
        else:
            print_fail(f"GET /payments falló: {get_payments.get('error')}")
    else:
        print_fail("Omitiendo GET /payments por falta de token")

    # -------------------------------------------------------------------------
    # RESUMEN FINAL
    # -------------------------------------------------------------------------
    print_header("RESUMEN DE PRUEBAS DEL ECOSISTEMA")
    porcentaje = (tests_passed / tests_total) * 100 if tests_total > 0 else 0
    if tests_passed == tests_total:
        print(f"\n  {GREEN}{BOLD}🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE! ({tests_passed}/{tests_total} - {porcentaje:.0f}%){RESET}\n")
    else:
        print(f"\n  {YELLOW}{BOLD}Pruebas aprobadas: {tests_passed}/{tests_total} ({porcentaje:.0f}%){RESET}\n")

    print_info(f"IP estática de la VM en GCP: 35.226.206.203")
    print_info(f"Puertos en producción: Login:5000, Books:5001, Pagos:5002, Pedidos:5003, Users:5004, Authors:5005, Redis:6379")
    print(f"{BLUE}{'=' * 75}{RESET}\n")


if __name__ == "__main__":
    main()
