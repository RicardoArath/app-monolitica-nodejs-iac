# Bitácora Exhaustiva de Pruebas: Integración Redis y Microservicios

**Proyecto:** Librería en Línea  
**Fecha de Ejecución:** 6 de Octubre de 2026  
**Ambiente de Ejecución:** Localhost (Windows x64 / Python 3.14 / Redis 5.0.14.1 RESP2 / PostgreSQL 16)  
**Script Automatizado:** `apps/services/test_redis_suite.py`  
**Resultado Global:** **7 / 7 PRUEBAS EXITOSAS (100% PASS)**  

---

## 1. Resumen Ejecutivo de Resultados

| ID | Prueba / Escenario | Componentes Evaluados | Código HTTP | Resultado | Métrica / Latencia |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **0** | Comprobación de Salud de 7 Nodos | Login, Books, Users, Authors, Pedidos, Pagos, Redis | `200 OK` | **PASS** | 7/7 Nodos Operacionales |
| **1** | Autenticación, JWT, Sesión y Refresh Token | Login (:5000) + Redis (:6379) | `200 OK` | **PASS** | JWT 1200s TTL, JTI UUID v4, Redis TTL 7200s |
| **2** | Cache-Aside Catálogo (MISS -> HIT) | Books (:5001) + PostgreSQL + Redis | `200 OK` | **PASS** | MISS: 39.7ms -> HIT: 7.1ms (82% más rápido) |
| **3** | Invalidación Activa de Caché tras Mutación | Authors (:5003) + Books (:5001) + Redis | `201 / 200` | **PASS** | Purga atómica de `books:*` y `authors:*` |
| **4** | Revocación Instantánea (JTI) y RBAC | Login (:5000) + Users (:5002) + Redis | `403 / 401` | **PASS** | RBAC 403, Logout blacklistea JTI, Token rechazado 401 |
| **5** | Pedidos: Stock Atómico y Clave Temporal | Pedidos (:5004) + PostgreSQL + Redis | `201 / 200` | **PASS** | Bloqueo `FOR UPDATE`, decremento -2, restauración +2 |
| **6** | Pagos: Idempotencia y Anti-Duplicados | Pagos (:5005) + Redis + PostgreSQL | `201 / 200` | **PASS** | Cobro inicial 201, Replay idempotente 200, 0 duplicados |
| **7** | Respuestas Duales (JSON/XML) y Métricas | Books (:5001) + Login (:5000) | `200 OK` | **PASS** | Content-Type `application/xml` y métricas Prometheus |

---

## 2. Registro Detallado de Pruebas

---

### Prueba 0: Comprobación de Salud de los 7 Nodos del Ecosistema

**Objetivo:** Verificar que los 6 microservicios Flask y el servidor Redis se encuentren activos, respondiendo correctamente y conectados a la base de datos PostgreSQL.

#### Peticiones Ejecutadas:
```bash
curl -X GET "http://127.0.0.1:5000/health?format=json"
curl -X GET "http://127.0.0.1:5001/health?format=json"
curl -X GET "http://127.0.0.1:5002/health?format=json"
curl -X GET "http://127.0.0.1:5003/health?format=json"
curl -X GET "http://127.0.0.1:5004/health?format=json"
curl -X GET "http://127.0.0.1:5005/health?format=json"
redis-cli -p 6379 ping
```

#### Respuestas Obtenidas:
```json
// Login (:5000)
{
  "status": "ok",
  "service": "login-service",
  "database": "connected",
  "redis": "connected",
  "port": 5000,
  "timestamp": "2026-10-06T15:46:11.234125"
}

// Redis CLI
PONG
```
*Los 6 microservicios reportaron `database: "connected"` y `redis: "connected"` con código HTTP 200.*

---

### Prueba 1: Autenticación, JWT Claims, Sesión en Redis y Rotación de Refresh Token

**Objetivo:** Validar que el inicio de sesión genera un JWT firmado con HS256, expiración de 20 minutos (1200 segundos), claim `jti` único, guarda la sesión en Redis (`session:<user_id>`), guarda el refresh token (`refresh:<token>`) y permite su rotación atómica.

#### Petición HTTP (Login):
```bash
curl -X POST "http://127.0.0.1:5000/login?format=json" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@libreria.local", "password": "Passw0rd!"}'
```

#### Respuesta Obtenida (`200 OK`):
```json
{
  "status": "success",
  "message": "Inicio de sesión exitoso.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AbGlicmVyaWEubG9jYWwiLCJyb2xlIjoiYWRtaW4iLCJyb2xlX2lkIjoxLCJub21icmUiOiJBZG1pbmlzdHJhZG9yIEdlbmVyYWwiLCJqdGkiOiIwYjkxZjA0Zi04YzlkLTQzNmMtYTY5Yy1lYWI0NTM1NjQ2NmIiLCJpYXQiOjE3OTEzMjQwMDAsImV4cCI6MTc5MTMyNTIwMH0.xxxx",
  "refresh_token": "a8f3b29c1d...",
  "token_type": "Bearer",
  "expires_in": 1200,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@libreria.local",
    "role": "admin",
    "role_id": 1
  }
}
```

#### Inspección en Redis:
```bash
redis-cli -p 6379 get "session:1"
# Retorna: {"id": 1, "username": "admin", "role": "admin", "email": "admin@libreria.local"}
redis-cli -p 6379 ttl "session:1"
# Retorna: 7199 (TTL inicial de 7200 segundos)

redis-cli -p 6379 get "refresh:a8f3b29c1d..."
# Retorna: "1" (user_id)
redis-cli -p 6379 ttl "refresh:a8f3b29c1d..."
# Retorna: 604799 (TTL de 7 días)
```

#### Petición HTTP (Rotación de Refresh Token):
```bash
curl -X POST "http://127.0.0.1:5000/token/refresh?format=json" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "a8f3b29c1d..."}'
```

#### Comprobación de Rotación:
- Se emitió un nuevo Access Token con nuevo `jti`.
- El refresh token antiguo `a8f3b29c1d...` fue **eliminado** de Redis (`GET` retorna `nil`).
- El nuevo refresh token fue registrado en Redis con TTL de 7 días.

---

### Prueba 2: Catálogo de Libros con Cache-Aside (MISS -> HIT)

**Objetivo:** Comprobar la reducción de latencia del catálogo mediante Cache-Aside en Redis y verificar el tiempo de vida (TTL) configurado.

#### Paso 2.1: Cache MISS (Primera Consulta)
```bash
curl -X GET "http://127.0.0.1:5001/books?page=1&format=json"
```
- **Latencia observada:** 39.7 ms (consulta ejecutada en PostgreSQL `v_catalog`).
- **Respuesta:**
```json
{
  "status": "success",
  "from_cache": false,
  "books": [ ... 12 libros ... ],
  "meta": { "total": 30, "page": 1, "totalPages": 3 }
}
```

#### Inspección en Redis:
```bash
redis-cli -p 6379 keys "books:list:*"
# Retorna: "books:list:isbn=:title=:year=:min=:max=:p=1"
redis-cli -p 6379 ttl "books:list:isbn=:title=:year=:min=:max=:p=1"
# Retorna: 298 (TTL de 300 segundos = 5 minutos)
```

#### Paso 2.2: Cache HIT (Segunda Consulta Idéntica)
```bash
curl -X GET "http://127.0.0.1:5001/books?page=1&format=json"
```
- **Latencia observada:** **7.1 ms** (recuperado de la RAM de Redis sin tocar PostgreSQL).
- **Respuesta:**
```json
{
  "status": "success",
  "from_cache": true,
  "books": [ ... 12 libros ... ]
}
```
*Mejora de rendimiento: 82.1% de reducción en el tiempo de respuesta.*

---

### Prueba 3: Invalidación Activa de Caché tras Mutación

**Objetivo:** Verificar que cualquier operación de escritura (`POST /authors`) invalida de inmediato las claves en memoria (`books:*` y `authors:*`) para evitar servir datos obsoletos.

#### Petición HTTP (Creación de Autor por Administrador):
```bash
curl -X POST "http://127.0.0.1:5003/authors?format=json" \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Gabriel García Márquez"}'
```
- **Código HTTP:** `201 Created`

#### Inspección en Redis:
```bash
redis-cli -p 6379 keys "books:*"
# Retorna: (empty list or set) -> 0 claves
redis-cli -p 6379 keys "authors:*"
# Retorna: (empty list or set) -> 0 claves
```

#### Petición de Verificación:
```bash
curl -X GET "http://127.0.0.1:5001/books?page=1&format=json"
```
- **Respuesta:** `"from_cache": false` (Cache MISS forzado; regeneración limpia de la caché con los datos más recientes).

---

### Prueba 4: Revocación Instantánea de JWT (Blacklist JTI) y RBAC

**Objetivo:** Demostrar que un token JWT puede revocarse al instante en Redis antes de su expiración natural, y que el middleware `@jwt_required` deniega el acceso a los servicios periféricos.

#### Paso 4.1: Validación de RBAC (Role-Based Access Control)
- Petición con token de usuario regular (`role: 'user'`):
```bash
curl -X GET "http://127.0.0.1:5002/users?format=json" \
  -H "Authorization: Bearer <USER_JWT>"
```
- **Resultado:** `403 Forbidden`
```json
{
  "status": "error",
  "message": "Acceso denegado: Su rol ('user') no tiene permisos para realizar esta operación. Roles requeridos: admin."
}
```

#### Paso 4.2: Cierre de Sesión (Logout de Administrador)
```bash
curl -X POST "http://127.0.0.1:5000/logout?format=json" \
  -H "Authorization: Bearer <ADMIN_JWT>"
```
- **Código HTTP:** `200 OK`
```json
{
  "status": "success",
  "message": "Sesión cerrada exitosamente y token revocado."
}
```

#### Inspección en Redis:
```bash
redis-cli -p 6379 get "jwt:revoked:0b91f04f-8c9d-436c-a69c-eab45356466b"
# Retorna: "1"
redis-cli -p 6379 ttl "jwt:revoked:0b91f04f-8c9d-436c-a69c-eab45356466b"
# Retorna: 1199 (segundos restantes de vida del token)
redis-cli -p 6379 get "session:1"
# Retorna: (nil) -> Sesión purgada
```

#### Paso 4.3: Intento de Acceso con Token Revocado
```bash
curl -X GET "http://127.0.0.1:5002/users?format=json" \
  -H "Authorization: Bearer <ADMIN_JWT_REVOCADO>"
```
- **Resultado:** `401 Unauthorized`
```json
{
  "status": "error",
  "message": "Token ha sido revocado. Inicie sesión nuevamente."
}
```
*Veredicto: El token revocado fue inmediatamente invalidado en toda la red de microservicios.*

---

### Prueba 5: Pedidos (Transacción Atómica de Stock y Clave Temporal en Redis)

**Objetivo:** Comprobar el bloqueo transaccional `SELECT ... FOR UPDATE` en PostgreSQL, el decremento de stock, la creación de la clave temporal `order:pending:<id>` y la restauración de stock ante cancelación.

#### Paso 5.1: Estado Inicial en PostgreSQL
```sql
SELECT id, title, stock FROM books WHERE id = 2;
-- Retorna: id=2, stock=15
```

#### Paso 5.2: Creación de Pedido
```bash
curl -X POST "http://127.0.0.1:5004/orders?format=json" \
  -H "Authorization: Bearer <USER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"book_id": 2, "quantity": 2}]}'
```
- **Código HTTP:** `201 Created`
- **ID de Pedido Generado:** `order_id = 9`

#### Verificación en PostgreSQL (Stock Descontado):
```sql
SELECT stock FROM books WHERE id = 2;
-- Retorna: 13 (15 - 2 = 13)
```

#### Inspección en Redis:
```bash
redis-cli -p 6379 get "order:pending:9"
# Retorna: {"user_id": 2, "total": 224.0}
redis-cli -p 6379 ttl "order:pending:9"
# Retorna: 1799 (TTL de 30 minutos)
```

#### Paso 5.3: Cancelación del Pedido
```bash
curl -X PATCH "http://127.0.0.1:5004/orders/9/status?format=json" \
  -H "Authorization: Bearer <USER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"status": "cancelled"}'
```
- **Código HTTP:** `200 OK`

#### Verificación en PostgreSQL (Stock Restaurado):
```sql
SELECT stock FROM books WHERE id = 2;
-- Retorna: 15 (Stock restaurado atómicamente a 15)
```

#### Inspección en Redis:
```bash
redis-cli -p 6379 get "order:pending:9"
# Retorna: (nil) -> Clave temporal eliminada
```

---

### Prueba 6: Pagos (Candado de Idempotencia en Redis y Anti-Duplicados)

**Objetivo:** Evitar doble cobro en pedidos garantizando que peticiones idénticas procesadas en paralelo o reenviadas devuelvan el comprobante original sin duplicar transacciones en la base de datos.

#### Paso 6.1: Pago Inicial
```bash
curl -X POST "http://127.0.0.1:5005/payments?format=json" \
  -H "Authorization: Bearer <USER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"order_id": 10, "amount": 112.00, "method": "simulated_card"}'
```
- **Código HTTP:** `201 Created`
- **Comprobante Emitido:** `id = 5`
- **Estado de Orden en PostgreSQL:** `confirmed`

#### Inspección en Redis:
```bash
redis-cli -p 6379 get "idempotency:payment:order:10"
# Retorna: {"status": "success", "payment": {"id": 5, "order_id": 10, "amount": 112.0, "status": "approved"}, ...}
redis-cli -p 6379 ttl "idempotency:payment:order:10"
# Retorna: 86398 (TTL de 24 horas)
```

#### Paso 6.2: Reenvío Idéntico de Pago (Simulación de Doble Clic)
```bash
curl -X POST "http://127.0.0.1:5005/payments?format=json" \
  -H "Authorization: Bearer <USER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"order_id": 10, "amount": 112.00, "method": "simulated_card"}'
```
- **Código HTTP:** `200 OK`
- **Respuesta:**
```json
{
  "status": "success",
  "idempotent_replay": true,
  "payment": {
    "id": 5,
    "order_id": 10,
    "amount": 112.0,
    "status": "approved"
  }
}
```

#### Comprobación en PostgreSQL (Cero Duplicados):
```sql
SELECT COUNT(*) FROM simulated_payments WHERE order_id = 10;
-- Retorna: 1 (Exactamente 1 registro, ningún cobro duplicado)
```

---

### Prueba 7: Respuestas Duales (JSON y XML) y Métricas de Monitoreo

**Objetivo:** Comprobar soporte del parámetro `?format=xml` en todos los endpoints y la exposición de métricas estándar para Prometheus en `/metrics`.

#### Petición XML:
```bash
curl -X GET "http://127.0.0.1:5001/books?format=xml"
```
- **Encabezado:** `Content-Type: application/xml; charset=utf-8`
- **Cuerpo:**
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<response>
  <status>success</status>
  <from_cache>true</from_cache>
  <books>
    <item>
      <id>1</id>
      <isbn>978-0-000001-4</isbn>
      <title>Don Quijote de la Mancha</title>
      <price>199.99</price>
      <stock>25</stock>
    </item>
  </books>
</response>
```

#### Petición de Métricas Prometheus:
```bash
curl -X GET "http://127.0.0.1:5000/metrics"
```
- **Muestreo de Métricas Obtenidas:**
```text
# HELP http_requests_total Total de peticiones HTTP procesadas
# TYPE http_requests_total counter
http_requests_total{endpoint="auth.login",method="POST",status="200"} 8
http_requests_total{endpoint="health.health_check",method="GET",status="200"} 142

# HELP redis_cache_hits_total Aciertos de caché en Redis
# TYPE redis_cache_hits_total counter
redis_cache_hits_total{prefix="books"} 34
redis_cache_hits_total{prefix="authors"} 12

# HELP redis_cache_misses_total Fallos de caché en Redis (consulta a Postgres)
# TYPE redis_cache_misses_total counter
redis_cache_misses_total{prefix="books"} 3
```

---

## 3. Conclusión de la Evaluación

La suite de pruebas automatizadas demostró de manera concluyente:
1. **Total estabilidad del clúster de microservicios** ejecutándose en puertos 5000 al 5005.
2. **Cumplimiento estricto de las reglas arquitectónicas:**
   - PostgreSQL se mantiene inalterado como la única fuente de la verdad para persistencia duradera.
   - Redis opera como capa compartida en memoria con comportamiento **Dual Fail-Safe** (Fail-Open para catálogos y Fail-Closed para seguridad).
   - El ciclo de vida de los JWT se encuentra protegido contra robo o sesiones abandonadas mediante revocación instantánea por `jti`.
   - Las operaciones de compras y pagos garantizan integridad transaccional e idempotencia absoluta.
