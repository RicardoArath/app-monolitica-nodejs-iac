"""
common
Paquete compartido por todos los microservicios Flask de Librería en Línea
(login, books, users, authors, pedidos, pagos).

Centraliza:
- config        -> variables de entorno comunes (PostgreSQL, Redis, JWT, CORS, TTLs)
- db            -> pool de conexiones PostgreSQL (fuente principal de datos)
- redis_client  -> conexión compartida a Redis, caché fail-open y operaciones fail-closed
- security      -> emisión/validación de JWT, lista de revocación (jti) y RBAC
- response      -> respuestas JSON/XML homogéneas
- metrics       -> contadores en memoria expuestos en /metrics (formato Prometheus)
- app_factory   -> creación de apps Flask con /health, /metrics, CORS y manejo de errores
"""
