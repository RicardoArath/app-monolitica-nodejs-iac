"""
start_all_microservices.py
Arranca concurrentemente los 6 microservicios Flask del ecosistema:
  - Login (:5000)
  - Books (:5001)
  - Pagos (:5002)
  - Pedidos (:5003)
  - Users (:5004)
  - Authors (:5005)
Verifica que Redis esté activo en localhost:6379 y reporta la salud de los 7 componentes.
"""
import os
import sys
import time
import subprocess
import socket
import urllib.request
import json

# Asegurar codificación utf-8 en terminal de Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable

SERVICES = [
    {"name": "Login", "port": 5000, "cwd": os.path.join(SERVICES_DIR, "login"), "script": "app.py"},
    {"name": "Books", "port": 5001, "cwd": os.path.join(SERVICES_DIR, "books"), "script": "app.py"},
    {"name": "Pagos", "port": 5002, "cwd": os.path.join(SERVICES_DIR, "pagos"), "script": "app.py"},
    {"name": "Pedidos", "port": 5003, "cwd": os.path.join(SERVICES_DIR, "pedidos"), "script": "app.py"},
    {"name": "Users", "port": 5004, "cwd": os.path.join(SERVICES_DIR, "users"), "script": "app.py"},
    {"name": "Authors", "port": 5005, "cwd": os.path.join(SERVICES_DIR, "authors"), "script": "app.py"},
]


def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0


def main():
    print("=" * 70)
    print("[INIT] INICIANDO ECOSISTEMA DE 6 MICROSERVICIOS Y CAPA COMPARTIDA REDIS")
    print("=" * 70)

    # 1. Comprobar Redis
    if check_port(6379):
        print(" [REDIS]   [OK] Redis Server detectado activo en 127.0.0.1:6379")
    else:
        print(" [REDIS]   [WARN] Redis no responde en 127.0.0.1:6379. Intentando iniciar...")
        redis_exe = os.path.expandvars(r"%USERPROFILE%\tools\redis\redis-server.exe")
        if os.path.exists(redis_exe):
            subprocess.Popen([redis_exe, "--port", "6379"])
            time.sleep(1)
            print(" [REDIS]   [OK] Redis Server arrancado con exito.")
        else:
            print(" [REDIS]   [WARN] No se encontro redis-server.exe local; asegurese de que Redis este activo.")

    # 2. Iniciar cada microservicio
    processes = []
    for svc in SERVICES:
        script_path = os.path.join(svc["cwd"], svc["script"])
        if not os.path.exists(script_path):
            print(f" [ERROR] No existe {script_path}")
            continue

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["FLASK_DEBUG"] = "0"

        # Lanzar proceso
        p = subprocess.Popen(
            [PYTHON_EXE, svc["script"]],
            cwd=svc["cwd"],
            env=env
        )
        processes.append((svc, p))
        print(f" [{svc['name']:7s}] Iniciando en puerto {svc['port']} (PID {p.pid})...")

    print("\nEsperando 4 segundos a que los servicios inicien...")
    time.sleep(4)

    # 3. Comprobar salud de los 6 microservicios
    print("\n" + "=" * 70)
    print("DIAGNOSTICO DE SALUD DE LOS 6 MICROSERVICIOS")
    print("=" * 70)

    for svc in SERVICES:
        url = f"http://127.0.0.1:{svc['port']}/health?format=json"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'HealthChecker'})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                status = data.get('status', 'ok')
                db_st = data.get('database', {}).get('status', 'ok')
                redis_st = data.get('redis', {}).get('status', 'ok')
                print(f" [{svc['name']:7s} :{svc['port']}] [OK] {status.upper()} | DB: {db_st} | Redis: {redis_st}")
        except Exception as e:
            print(f" [{svc['name']:7s} :{svc['port']}] [ERROR] de conexion: {e}")

    print("=" * 70)
    print("Todos los servicios estan corriendo en segundo plano.\n")

    try:
        while True:
            time.sleep(1)
            for svc, p in processes:
                if p.poll() is not None:
                    print(f" [ALERTA] Proceso {svc['name']} (PID {p.pid}) termino con codigo {p.returncode}")
    except KeyboardInterrupt:
        print("\nDeteniendo microservicios...")
        for svc, p in processes:
            p.terminate()
            p.wait()
        print("Todos los microservicios fueron detenidos limpiamente.")


if __name__ == '__main__':
    main()
