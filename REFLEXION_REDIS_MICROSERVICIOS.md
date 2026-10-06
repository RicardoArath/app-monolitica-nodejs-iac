# Reflexión Arquitectónica: Integración de Redis en el Ecosistema de Microservicios

**Proyecto:** Librería en Línea  
**Autor:** Ricardo Sánchez / Arquitectura de Software  
**Fecha:** Octubre 2026  
**Ecosistema:** 6 Microservicios Flask (Python), Redis en Memoria, PostgreSQL (SSOT), Cliente de Escritorio Tkinter  

---

## 1. Justificación Técnica y Arquitectónica de Redis

En una arquitectura orientada a microservicios donde conviven múltiples dominios de negocio desacoplados (Autenticación, Catálogo de Libros, Administración de Usuarios, Autores, Pedidos y Pagos), una base de datos relacional tradicional (PostgreSQL) presenta cuellos de botella inherentes si se utiliza para operaciones efímeras, de alta frecuencia o de baja latencia.

La introducción de **Redis** como **capa compartida en memoria** resuelve tres problemas fundamentales del sistema:

### 1.1. Gestión de Sesiones, Refresh Tokens y Revocación Instantánea de JWT
- **El dilema de los JWT Stateless:** Los tokens JWT son tradicionalmente apátridas (*stateless*). Una vez que un token es firmado criptográficamente, es matemáticamente válido hasta su tiempo de expiración (`exp`), lo que imposibilita revocarlo en caso de cierre de sesión (*logout*), compromiso de credenciales o cambio de privilegios de usuario.
- **La solución con Redis (Blacklist por JTI):** Cada JWT emitido incluye un identificador único criptográfico (`jti`, UUID v4). Al invocar `POST /logout`, el servicio de login almacena la clave `jwt:revoked:<jti>` con valor `"1"` y un tiempo de vida (TTL) exactamente igual a los segundos restantes de validez del token. Todos los microservicios, a través del middleware compartido `@jwt_required`, consultan Redis antes de procesar una petición protegida. Si el `jti` existe en Redis, la petición es rechazada de inmediato con `401 Unauthorized`.
- **Expiración natural de memoria:** Al vincular el TTL de la clave de revocación a la expiración del JWT, Redis descarta automáticamente los identificadores cuando el token ya ha expirado por sí mismo, manteniendo el consumo de memoria acotado y constante sin necesidad de procesos batch de limpieza.
- **Refresh Tokens Rotativos:** Los tokens de refresco (7 días) se guardan como `refresh:<token>` apuntando a `user_id`. Al utilizarse para obtener un nuevo access token de 20 minutos, el refresh token anterior se destruye inmediatamente en Redis y se emite uno nuevo, implementando el patrón seguro de **Refresh Token Rotation**.

### 1.2. Estrategia de Caché: Patrón Cache-Aside
Para las consultas de lectura masiva del catálogo (`GET /books`, `GET /books/<isbn>`, `GET /authors`), se implementó el patrón **Cache-Aside** (Lazy Loading):
1. El microservicio busca la clave en Redis (`books:list:<filtros>` con TTL 300s o `books:<isbn>` con TTL 900s).
2. **Cache HIT:** Si la clave existe, deserializa el JSON en memoria y responde al cliente en menos de 10 milisegundos sin tocar PostgreSQL.
3. **Cache MISS:** Si la clave no existe o expiró, ejecuta la consulta optimizada contra PostgreSQL (`v_catalog`), almacena el resultado en Redis con su TTL y retorna los datos al cliente.
4. **Invalidación Activa:** Ante cualquier mutación (`POST`, `PUT`, `PATCH`, `DELETE`) en libros o autores, se invoca `redis_client.invalidate_pattern('books:*')` y `authors:*` mediante comandos no bloqueantes `SCAN` y pipelines atómicos, asegurando coherencia eventual inmediata.

### 1.3. Patrón de Resiliencia: Dual Fail-Safe
No todas las operaciones tienen los mismos requisitos de consistencia y seguridad. Por ello se diseñó la política **Dual Fail-Safe**:
- **FAIL-OPEN (Caché de Catálogo):** Si el servidor Redis sufre una caída de red, latencia extrema o falla de conexión, las lecturas del catálogo capturan la excepción, registran la anomalía en Prometheus (`redis_cache_bypass_total`), y desvían la consulta de forma transparente a PostgreSQL. El usuario final sigue navegando el catálogo sin percibir caídas ni errores HTTP 500.
- **FAIL-CLOSED (Seguridad, Sesión, Revocación e Idempotencia):** En operaciones donde la seguridad y la integridad financiera están en juego (comprobación de revocación de JWT, adquisición de candados de pago o verificación de refresh tokens), si Redis no responde, el sistema **falla de forma segura** retornando `503 Service Unavailable` o `401 Unauthorized`. Jamás se acepta un token potencialmente revocado ni se procesa un pago sin control de concurrencia.

### 1.4. Transacciones Atómicas de Stock y Coordinación Temporal
- **PostgreSQL como Single Source of Truth (SSOT):** El stock real de inventario y las órdenes residen en PostgreSQL. Al crear un pedido (`POST /orders`), se ejecuta una transacción atómica con bloqueo de filas mediante `SELECT ... FOR UPDATE` para evitar condiciones de carrera (*race conditions*). El stock se decrementa en la misma transacción y se insertan las líneas en `order_items`.
- **Redis como Coordinador Temporal:** Al confirmarse el pedido en estado `pending`, se publica una clave efímera `order:pending:<order_id>` en Redis con TTL de 30 minutos (1800s). Esto permite que tareas asíncronas o monitores liberen el stock si el usuario abandona la pasarela de pago sin completar la transacción. Si el usuario cancela (`PATCH /orders/<id>/status` -> `cancelled`), el stock se restaura atómicamente y la clave temporal de Redis es purgada.

### 1.5. Idempotencia en Pagos (Prevención de Doble Cobro)
En el microservicio de Pagos (`:5005`), para evitar cobros duplicados causados por reintentos de red o múltiples clics del cliente:
1. Se calcula la clave de idempotencia `payment:order:<order_id>`.
2. Se ejecuta una adquisición atómica `client.set("idempotency:payment:order:<order_id>", "processing", ex=86400, nx=True)`.
3. Si el resultado es `False` (ya existía), se consulta el resultado previo y se devuelve la respuesta original con la bandera `idempotent_replay: true` y código `200 OK`.
4. Si se adquirió exitosamente el candado, se valida el pedido en PostgreSQL, se aprueba el pago en `simulated_payments`, se actualiza el estado del pedido a `confirmed`, se guarda la confirmación en Redis y se elimina la clave de pedido pendiente.

---

## 2. Matriz de Microservicios, Endpoints y Claves Redis

| Servicio | Puerto | Endpoint | Método | JWT Requerido | Rol Requerido | Clave Redis Asociada | TTL Redis | Política Fail-Safe | Descripción |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :--- |
| **Login** | 5000 | `/login` | POST | No | Público | `session:<user_id>`, `refresh:<token>` | 7200s (2h) / 7 días | Fail-Closed | Autentica con bcrypt, emite JWT (20m) con JTI y refresh token. |
| **Login** | 5000 | `/logout` | POST | Sí | Cualquiera | `jwt:revoked:<jti>`, `session:<user_id>` (DEL) | Restante del JWT | Fail-Closed | Revoca el JTI en Redis y destruye la sesión y el refresh token. |
| **Login** | 5000 | `/token/refresh` | POST | No | Público | `refresh:<token>` (DEL anterior, SET nuevo) | 7 días | Fail-Closed | Rotación de Refresh Token y emisión de nuevo Access Token (20m). |
| **Login** | 5000 | `/session` | GET | Opcional | Cualquiera | `jwt:revoked:<jti>` (verificación) | N/A | Fail-Closed | Comprueba validez de sesión y umbral de renovación (`expiring`). |
| **Login** | 5000 | `/health` | GET | No | Público | Ping a Redis | N/A | Fail-Open | Semáforo de salud de base de datos y Redis. |
| **Books** | 5001 | `/books` | GET | No | Público | `books:list:<filtros>:p=<page>` | 300s (5m) | Fail-Open | Listado paginado y búsqueda con Cache-Aside. |
| **Books** | 5001 | `/books/<isbn>` | GET | No | Público | `books:<isbn>` | 900s (15m) | Fail-Open | Detalle de libro con autores y géneros cacheados. |
| **Books** | 5001 | `/books` | POST | Sí | `admin` | Invalida `books:*` | N/A | Fail-Closed (Auth) | Alta de libro y purga masiva de caché. |
| **Books** | 5001 | `/books/<id>` | PUT | Sí | `admin` | Invalida `books:*` | N/A | Fail-Closed (Auth) | Modificación de libro y purga masiva de caché. |
| **Books** | 5001 | `/books/<id>` | DELETE | Sí | `admin` | Invalida `books:*` | N/A | Fail-Closed (Auth) | Eliminación lógica/física e invalidación en Redis. |
| **Users** | 5002 | `/users` | GET | Sí | `admin` | `jwt:revoked:<jti>` (verificación) | N/A | Fail-Closed | Listado completo de usuarios registrados. |
| **Users** | 5002 | `/users/<id>` | GET | Sí | `admin` o propio | `jwt:revoked:<jti>` (verificación) | N/A | Fail-Closed | Detalle y roles de usuario específico. |
| **Users** | 5002 | `/users` | POST | Sí | `admin` | `jwt:revoked:<jti>` | N/A | Fail-Closed | Creación administrativa de usuario con rol y hash bcrypt. |
| **Users** | 5002 | `/users/<id>` | PUT | Sí | `admin` | Invalida `session:<id>` | N/A | Fail-Closed | Actualización de rol o datos; fuerza reinicio de sesión en Redis. |
| **Users** | 5002 | `/users/<id>` | DELETE | Sí | `admin` | Invalida `session:<id>` | N/A | Fail-Closed | Baja de usuario y purga inmediata de su sesión en Redis. |
| **Authors** | 5003 | `/authors` | GET | No | Público | `authors:list` | 300s (5m) | Fail-Open | Catálogo de autores con conteo de obras cacheadas. |
| **Authors** | 5003 | `/authors/<id>` | GET | No | Público | `authors:<id>` | 300s (5m) | Fail-Open | Perfil de autor con libros vinculados. |
| **Authors** | 5003 | `/authors` | POST | Sí | `admin` | Invalida `authors:*`, `books:*` | N/A | Fail-Closed (Auth) | Creación de autor e invalidación cruzada. |
| **Authors** | 5003 | `/authors/<id>/books`| POST | Sí | `admin` | Invalida `authors:*`, `books:*` | N/A | Fail-Closed (Auth) | Vinculación M2M libro-autor e invalidación cruzada. |
| **Pedidos** | 5004 | `/orders` | GET | Sí | Cualquiera | `jwt:revoked:<jti>` | N/A | Fail-Closed | Admin ve todos los pedidos; Usuario regular solo los suyos. |
| **Pedidos** | 5004 | `/orders` | POST | Sí | Cualquiera | `order:pending:<order_id>`, invalida `books:*` | 1800s (30m) | Fail-Closed | Bloqueo `FOR UPDATE`, decremento de stock, clave temporal en Redis. |
| **Pedidos** | 5004 | `/orders/<id>/status`| PATCH | Sí | Propietario / `admin`| Invalida `books:*`, borra `order:pending:<id>` | N/A | Fail-Closed | Si pasa a `cancelled`, restaura stock atómicamente en PostgreSQL. |
| **Pagos** | 5005 | `/payments` | POST | Sí | Cualquiera | `idempotency:payment:order:<id>`, borra `order:pending:<id>` | 86400s (24h) | Fail-Closed | Candado atómico `SET NX EX`, confirmación de pedido y anti-duplicados. |
| **Pagos** | 5005 | `/payments/<id>` | GET | Sí | Propietario / `admin`| `idempotency:payment:order:<id>` | N/A | Fail-Closed | Consulta de recibo/comprobante de pago simulado. |

---

## 3. Storyboard Técnico Detallado (Animación Ubiquitous)

Este guión describe la animación conceptual para la herramienta **Ubiquitous**, representando el flujo de paquetes, estados y transiciones en la arquitectura distribuida.

### Visión General del Escenario Visual
- **Nodos Principales:**
  1. `[CLIENTE]`: Interfaz gráfica Tkinter de escritorio (laptop moderna con semáforo superior).
  2. `[MICROSERVICIOS]`: Barra de 6 contenedores (`Login`, `Books`, `Users`, `Authors`, `Pedidos`, `Pagos`).
  3. `[REDIS]`: Cilindro rojo brillante de memoria ultrarrápida con rayos de luz y contadores TTL.
  4. `[POSTGRESQL]`: Gran almacén cilíndrico azul con estantes relacionales y candados ACID.

---

### Escena 1: Autenticación, Emisión de Tokens y Almacenamiento en Redis
- **Visual:** El usuario ingresa credenciales (`admin@libreria.local` / `Passw0rd!`) en la ventana de login de Tkinter.
- **Acción:**
  1. Un paquete con las credenciales viaja al nodo `[Login :5000]`.
  2. `[Login]` consulta a `[PostgreSQL]` para verificar el hash bcrypt (`$2b$12$...`).
  3. `[Login]` genera:
     - Un Access Token JWT con payload `{sub: 1, role: "admin", jti: "uuid-v4", exp: +1200s}`.
     - Un Refresh Token criptográfico aleatorio de 64 caracteres.
  4. `[Login]` dispara dos haces de luz instantáneos hacia `[Redis]`:
     - Clave `session:1` (JSON con datos de perfil, TTL 7200s).
     - Clave `refresh:<token>` con valor `"1"` (TTL 7 días).
  5. `[Login]` responde a `[CLIENTE]` con el token JWT y el refresh token.
- **Efecto Visual:** En la pantalla del cliente se enciende el semáforo verde de "Login" y la barra superior muestra `"👤 Administrador General (Rol: ADMIN)"`.

---

### Escena 2: Consulta del Catálogo de Libros (Cache-Aside: MISS -> HIT)
- **Visual:** El cliente abre la pestaña "Catálogo" y realiza una búsqueda de libros.
- **Acción (Paso 1: Cache MISS):**
  1. La petición `GET /books?page=1` llega a `[Books :5001]`.
  2. `[Books]` pregunta a `[Redis]`: `EXISTS books:list:...`.
  3. `[Redis]` responde con un destello amarillo: **Cache MISS** (`null`).
  4. `[Books]` va a `[PostgreSQL]` y ejecuta un `SELECT` sobre `v_catalog` (latencia ~40ms).
  5. Al recibir los datos, `[Books]` deposita una réplica en `[Redis]` con la clave `books:list:...` y un temporizador visible de 300 segundos (TTL).
  6. Los libros se despliegan en la tabla del cliente.
- **Acción (Paso 2: Cache HIT):**
  1. El usuario cambia de pestaña y vuelve al catálogo.
  2. `[Books]` consulta a `[Redis]`.
  3. `[Redis]` responde inmediatamente en **7 milisegundos**: **Cache HIT**.
  4. Los datos fluyen sin tocar `[PostgreSQL]`.
- **Efecto Visual:** En la tarjeta de Books se muestra un badge verde parpadeante: `"Cache HIT (Redis) — 7ms"`.

---

### Escena 3: Compra con Reserva Atómica de Stock y Clave Temporal
- **Visual:** El usuario selecciona el libro "Cien Años de Soledad" (Stock actual: 15) y hace clic en "Crear Pedido" (2 unidades).
- **Acción:**
  1. La petición viaja con `Authorization: Bearer <JWT>` hacia `[Pedidos :5004]`.
  2. `[Pedidos]` consulta en microsegundos a `[Redis]` si el token está revocado (`jwt:revoked:<jti>`). Redis confirma que el token es limpio.
  3. `[Pedidos]` abre una transacción ACID en `[PostgreSQL]` con un candado dorado: `SELECT stock FROM books WHERE id=2 FOR UPDATE`.
  4. PostgreSQL verifica stock suficiente (15 >= 2), decrementa el inventario a 13 e inserta la fila en `orders` (`status='pending'`) y `order_items`. Se confirma el `COMMIT`.
  5. `[Pedidos]` ejecuta dos acciones en `[Redis]`:
     - Pulveriza las claves `books:*` (invalidación de catálogo para reflejar el nuevo stock).
     - Crea una clave temporal `order:pending:101` con un reloj de arena de 30 minutos (1800s).
- **Efecto Visual:** El stock en el catálogo del cliente se actualiza a 13 unidades y el pedido aparece en estado "Pendiente de Pago".

---

### Escena 4: Pasarela de Pagos con Candado de Idempotencia
- **Visual:** El usuario hace clic en "Pagar Pedido #101" con tarjeta simulada. Por un fallo de conexión del cliente, este presiona el botón dos veces rápidamente.
- **Acción (Primer Clic):**
  1. Petición 1 llega a `[Pagos :5005]` con `order_id=101`.
  2. `[Pagos]` adquiere el candado en `[Redis]`: `SET idempotency:payment:order:101 "processing" NX EX 86400`. Redis otorga el candado (`OK`).
  3. `[Pagos]` valida el monto contra `[PostgreSQL]`, inserta en `simulated_payments` y actualiza la orden a `status='confirmed'`.
  4. `[Pagos]` guarda el comprobante `{payment_id: 88, status: 'approved'}` en `[Redis]` y borra `order:pending:101`.
  5. Responde con `201 Created`.
- **Acción (Segundo Clic duplicado):**
  1. Petición 2 llega a `[Pagos :5005]` con `order_id=101`.
  2. `[Pagos]` consulta `[Redis]` y encuentra el resultado ya procesado.
  3. Responde de inmediato con `200 OK` (`idempotent_replay: true`) reutilizando el comprobante #88 sin duplicar el cargo en PostgreSQL.
- **Efecto Visual:** Se proyecta un escudo protector verde sobre PostgreSQL impidiendo la duplicidad del cobro, mientras el cliente recibe su recibo exitoso.

---

### Escena 5: Cierre de Sesión, Revocación Instantánea (Blacklist) y Bloqueo RBAC
- **Visual:** El administrador hace clic en "Cerrar Sesión" en la esquina superior derecha.
- **Acción:**
  1. `[CLIENTE]` envía `POST /logout` con su JWT a `[Login :5000]`.
  2. `[Login]` extrae el `jti` (`0b91f04f-...`) y calcula los 850 segundos de vida que le quedaban al token.
  3. `[Login]` inserta en `[Redis]` la clave `jwt:revoked:0b91f04f-... = "1"` con TTL de 850s, y borra la sesión `session:1`.
  4. Un atacante intenta utilizar ese mismo JWT en `[Users :5002]` para listar la nómina (`GET /users`).
  5. El middleware `@jwt_required` de `[Users]` pregunta a `[Redis]`: `EXISTS jwt:revoked:0b91f04f-...`.
  6. `[Redis]` responde afirmativamente (`1`).
  7. `[Users]` frena la petición en seco y retorna `401 Unauthorized: "El token JWT ha sido revocado"`.
- **Efecto Visual:** Una barrera roja detiene el paquete no autorizado con el sonido de un candado digital cerrándose.

---

### Escena 6: Prueba de Caída de Redis (Demostración Dual Fail-Safe)
- **Visual:** El cable de red hacia `[Redis]` se desconecta (simulación de fallo catastrófico en memoria).
- **Acción (Navegación en Catálogo - Fail-Open):**
  1. Un usuario entra a `GET /books`.
  2. `[Books]` detecta timeout de Redis (1.0s), incrementa la métrica `redis_cache_bypass_total`, y de forma silenciosa e ininterrumpida consulta `[PostgreSQL]`.
  3. La página carga con éxito (Fail-Open).
- **Acción (Operación Sensible - Fail-Closed):**
  1. Un usuario intenta autenticarse o acceder a `/users`.
  2. `[Users]` intenta verificar la lista de revocación en Redis, pero Redis no responde.
  3. El sistema activa **Fail-Closed**: rechaza la operación con `503 Service Unavailable: "Redis no disponible para validar seguridad"`.
  4. Se garantiza que ningún token revocado pueda colarse durante la caída de la infraestructura de memoria.
- **Efecto Visual:** El semáforo de Redis en la aplicación de escritorio pasa a rojo intenso (`🔴 Redis: Error de Conexión`), los semáforos de microservicios pasan a ámbar, y un banner de seguridad informa al usuario la degradación controlada del servicio.

---

## 4. Conclusiones y Lecciones Aprendidas

1. **La combinación híbrida PostgreSQL + Redis ofrece lo mejor de dos mundos:** PostgreSQL garantiza la consistencia transaccional ACID estricta para inventario y pagos, mientras que Redis absorbe el 90% del tráfico de lectura del catálogo y resuelve la revocación en tiempo real de tokens JWT.
2. **Dual Fail-Safe es un principio de resiliencia indispensable:** Diseñar el sistema para degradarse elegantemente (*graceful degradation*) en lecturas de catálogo sin comprometer jamás la seguridad en autenticación y cobros previene tanto caídas masivas de cara al usuario como brechas de seguridad críticas.
3. **Compatibilidad estricta de protocolos (RESP2 vs RESP3):** La selección explícita del protocolo (`protocol=2`) aseguró la interoperabilidad total entre el entorno de desarrollo local (Redis 5.0 en Windows) y los entornos productivos modernos en la nube (Redis 6/7/8 en Google Cloud Platform).
