# Decisiones de Ingeniería — Librería en línea (Monolito)

Este documento explica **qué se construyó y por qué**, siguiendo el
formato pedido: **Necesidad → Decisión → Justificación → Ventajas → Limitaciones**.

---

## 1. Arquitectura seleccionada

### Diagrama de arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    APLICACIÓN MONOLÍTICA (Node.js)                │
│                                                                     │
│  ┌───────────────┐   ┌────────────────────┐   ┌────────────────┐  │
│  │ Presentación   │   │ Lógica de negocio  │   │ Acceso a datos │  │
│  │ (EJS + CSS)    │──▶│ routes/ + services/│──▶│  config/db.js  │  │
│  │ views/         │   │ (validación, roles)│   │  (pg, SQL      │  │
│  └───────▲────────┘   └─────────┬──────────┘   │  parametrizado)│  │
│          │                      │               └───────┬────────┘  │
│  HTTP/HTTPS (formularios HTML,  │                        │           │
│  sin JSON/XML, sin APIs)        │                        │           │
└──────────┼──────────────────────┼────────────────────────┼──────────┘
           │                      │                        │
      Navegador Web         Sesión en memoria         PostgreSQL
     (usuario/admin)        (express-session)      (libreria_online)
```

Un único proceso Node.js concentra interfaz (vistas EJS), lógica de
negocio (rutas + servicios) y acceso a datos (pool `pg`), tal como se
definió en la clase para el patrón **Monolítico**.

| Necesidad | Decisión | Justificación | Ventajas | Limitaciones |
|---|---|---|---|---|
| Entregar un sistema funcional, simple y rápido de construir para un dominio acotado (librería en línea) | Arquitectura **monolítica en capas** (presentación / lógica / datos), sin servicios externos | El enunciado lo exige explícitamente: sin REST/GraphQL/SOAP, sin JSON/XML entre componentes. Además, para el tamaño del proyecto (un equipo, un dominio estable), el monolito minimiza complejidad operativa | Despliegue como una sola unidad, depuración sencilla, transacciones locales simples (una sola BD) | Escala verticalmente como unidad completa; un cambio grande puede requerir redesplegar toda la app |

El monolito **no es código desorganizado**: se mantiene modular
internamente (`routes/`, `services/`, `middleware/`, `views/`), con
fronteras claras entre responsabilidades, aunque todo se despliegue
como una sola unidad (lo que la clase llama **monolito modular**).

---

## 2. Diseño, estructura y normalización de la base de datos

### Necesidad
El modelo de datos original (ISBN, título, autor, año, género, precio,
stock, formato, imágenes, conceptos) mezcla atributos monovaluados con
**dependencias multivaluadas**: un libro puede tener varios autores,
pertenecer a varios géneros, tener varias imágenes y definir varios
conceptos (donde el mismo nombre de concepto puede repetirse en otro
libro con **definición distinta**).

### Decisión
Normalizar hasta **3FN**, tratando las relaciones multivaluadas
independientes (autores, géneros) como **tablas puente** separadas
(equivalente a resolver la dependencia multivaluada que rompería 4FN si
se dejaran como listas dentro de `books`):

- `books` — atributos que dependen únicamente del ISBN (clave)
- `authors`, `genres`, `formats`, `categories` — catálogos independientes
- `book_authors`, `book_genres` — relaciones N:M (evitan repetir autores
  como texto dentro de `books` y eliminan anomalías de actualización)
- `book_concepts` — **no** es un catálogo compartido: la definición
  depende del par `(book_id, name)`, por eso vive en su propia tabla
  ligada a `books`, no como fila de un catálogo global de "conceptos"
- `book_images` — un libro puede tener N imágenes; se modela como tabla
  hija en vez de columna repetida o array

### Justificación
Guardar autores/géneros/imágenes/conceptos como listas dentro de
`books` (por ejemplo, columnas de texto separadas por comas o arrays)
rompería 1FN/3FN: dificultaría búsquedas, generaría redundancia y
anomalías de actualización (renombrar un autor obligaría a editar cada
libro que lo mencione).

### Ventajas
- Sin redundancia de datos de autores/géneros
- Integridad referencial garantizada por `FOREIGN KEY`
- Búsquedas e índices eficientes (`idx_books_title`, `idx_books_isbn`)

### Limitaciones
- Las consultas de detalle requieren varios `JOIN`/subconsultas (mitigado
  con la vista `v_catalog` en `db/06_views.sql`)
- Mayor número de tablas a mantener que un diseño desnormalizado

### Diagrama entidad-relación (resumen)

Ver [`docs/DB_DESIGN_ER3FN.md`](DB_DESIGN_ER3FN.md) para el diagrama
completo y el detalle campo por campo.

---

## 3. Organización de módulos y componentes

| Carpeta | Responsabilidad |
|---|---|
| `routes/` | Recibe peticiones HTTP, valida entrada básica, delega en `services/`, decide qué vista renderizar |
| `services/` | Única capa que ejecuta SQL contra PostgreSQL (SQL parametrizado) |
| `middleware/` | Autenticación de sesión, control de roles, subida de archivos |
| `views/` | Plantillas EJS, sin lógica de negocio (solo presentación) |
| `config/` | Configuración de infraestructura (pool de conexión) |

Esta separación por capas (patrón **Layered/N-Tier** visto en clase)
existe **dentro** del mismo proceso: sigue siendo un monolito porque
todo se despliega, ejecuta y escala como una sola unidad; no hay
límites de red ni contratos de comunicación entre estos módulos, solo
llamadas de función directas (`require(...)`).

---

## 4. Funcionalidades implementadas

- Registro y login de usuarios; un único administrador
- Catálogo con búsqueda por título/ISBN y paginación
- Detalle de libro: autores, géneros, conceptos, imágenes
- CRUD completo (todas las tablas): libros, autores, géneros, formatos,
  categorías, conceptos por libro, imágenes
- Carga de imágenes JPG/PNG/WebP

---

## 5. Flujo de información entre usuario, aplicación y base de datos

```
Usuario (navegador)
   │  1. Envía formulario HTML (POST application/x-www-form-urlencoded
   │     o multipart/form-data para imágenes)
   ▼
routes/*.js
   │  2. express.urlencoded() parsea el body; multer parsea archivos
   ▼
services/*.js
   │  3. Ejecuta SQL parametrizado ($1, $2...) contra PostgreSQL
   │     (algunas operaciones compuestas usan stored procedures:
   │     sp_create_book, sp_set_book_authors, sp_register_user...)
   ▼
PostgreSQL
   │  4. Devuelve filas / RETURNING id
   ▼
services/*.js → routes/*.js
   │  5. res.render('vista', { datos })
   ▼
views/*.ejs
   │  6. Genera HTML final del lado del servidor
   ▼
Usuario (navegador) recibe HTML listo para mostrar
```

No existe en ningún punto un payload JSON/XML entre "componentes": el
navegador solo envía formularios HTML y recibe HTML renderizado.

---

## 6. Autenticación, autorización, roles y seguridad

| Necesidad | Decisión | Justificación | Ventajas | Limitaciones |
|---|---|---|---|---|
| Distinguir usuarios regulares de administrador | Sesión de servidor (`express-session`, cookie `httpOnly`) + columna `role` con `CHECK` | Evita manejar tokens/JSON; encaja con el patrón "todo en el mismo proceso" | Simple de implementar y depurar; la sesión no puede leerse ni modificarse desde JS del cliente (`httpOnly`) | Sesión en **memoria del proceso**: no sobrevive a un reinicio ni escala a múltiples instancias sin sticky sessions o un store compartido |
| Garantizar un único administrador | Índice único parcial `CREATE UNIQUE INDEX one_admin_only ON users ((role)) WHERE role = 'admin'` | Reglas de negocio críticas deben vivir en la base de datos, no solo en la aplicación (defensa en profundidad) | Imposible violar la regla aunque se inserte por otra vía (psql directo, otro proceso) | Un solo administrador es una limitación de diseño explícita del ejercicio, no pensada para producción multi-admin |
| Evitar contraseñas en texto plano | `bcryptjs` con `SALT_ROUNDS = 10` | Estándar de la industria para hashing de contraseñas | Resistente a ataques de fuerza bruta/rainbow tables | Costo de CPU en cada login (aceptable para el volumen del ejercicio) |
| Evitar inyección SQL | SQL 100% parametrizado (`$1, $2...`) en toda la capa `services/` | Nunca se concatenan valores de usuario dentro del texto SQL | Elimina la clase de vulnerabilidad más común en apps con acceso directo a BD | Los nombres de tabla en `catalogService.js` se restringen a una lista blanca (`TABLES`), nunca a input crudo del usuario |
| Proteger rutas de administración | Middleware `requireAdmin` aplicado a todo `routes/adminRoutes.js` | Centraliza la verificación en un solo punto en vez de repetirla por ruta | Reduce el riesgo de "olvidar" proteger una ruta nueva | — |

---

## 7. Validación de datos y manejo de errores

- **Validación de formularios:** required/minlength/type en HTML5 +
  revalidación en servidor (ej. contraseñas coinciden, longitud mínima,
  campos obligatorios de libro) antes de tocar la base de datos.
- **Restricciones a nivel de base de datos** (última línea de defensa):
  `CHECK` (precio ≥ 0, stock ≥ 0, año entre 1450–2100, rol válido),
  `UNIQUE` (ISBN, nombres de catálogos, un admin), `FOREIGN KEY` con
  `ON DELETE CASCADE` donde corresponde.
- **Manejo de errores:** cada ruta usa `try/catch` y delega en
  `next(err)`; un middleware central en `app.js` captura cualquier error
  no manejado y renderiza `views/errors/500.ejs` sin filtrar detalles
  internos en producción (`NODE_ENV=production`).
- **Errores de integridad traducidos a mensajes útiles:** por ejemplo,
  el código de error `23505` (violación de `UNIQUE`, como ISBN
  duplicado) se traduce a un mensaje flash entendible para el usuario en
  lugar de mostrar el error crudo de PostgreSQL.

---

## 8. Gestión de archivos e imágenes

| Necesidad | Decisión | Justificación | Ventajas | Limitaciones |
|---|---|---|---|---|
| Subir imágenes de portada sin usar JSON/base64 como transporte | `multer` con `diskStorage`, `multipart/form-data` directo desde el formulario HTML | Es el mecanismo nativo del navegador para archivos; no requiere codificar la imagen como texto/JSON | Eficiente (streaming a disco), simple de integrar con Express | Almacenamiento en disco local: no apto para múltiples instancias sin un volumen compartido |
| Restringir tipos de archivo | `fileFilter` que solo acepta `image/jpeg`, `image/png`, `image/webp` + `limits.fileSize` (5 MB por defecto) | Evita subir ejecutables u otros tipos peligrosos disfrazados de imagen | Reduce superficie de ataque | La validación es por MIME type declarado por el cliente; para un entorno productivo se recomendaría además verificar los "magic bytes" del archivo |
| Nombres de archivo únicos | `crypto.randomBytes(12)` + timestamp | Evita colisiones y sobrescritura accidental de archivos de otros libros | — | — |
| Una sola imagen "principal" por libro | Trigger `book_images_single_primary` en PostgreSQL | La regla de negocio se protege en la base de datos, no solo en la UI | Consistente aunque se inserte por otra vía | — |

---

## 9. Despliegue y configuración del servidor

Según el escenario de la clase (GCP Compute Engine + CentOS 10 Stream):

1. Instalar Node.js LTS y PostgreSQL en la instancia.
2. Ejecutar los scripts de `db/` en el orden indicado en el `README.md`.
3. Configurar `.env` (host de BD, credenciales, `SESSION_SECRET`).
4. `npm install && npm start` (o gestionarlo con `pm2` para reinicio
   automático y ejecución en segundo plano).
5. Publicar detrás de Apache/NGINX como *reverse proxy* (terminación
   TLS/HTTPS), con `app.set('trust proxy', 1)` ya configurado en
   `app.js` para que las cookies de sesión funcionen correctamente
   detrás del proxy.

---

## 10. Consideraciones de rendimiento, mantenimiento y escalabilidad

- **Rendimiento:** índices en `books.title`, `books.isbn` y
  `book_images.book_id`; pool de conexiones (`pg.Pool`, máx. 10)
  reutiliza conexiones en vez de abrir una por petición.
- **Mantenimiento:** la separación en `services/` aísla todo el SQL en
  un solo lugar por entidad, facilitando cambios futuros (por ejemplo,
  migrar una tabla a otra tecnología) sin tocar las rutas.
- **Escalabilidad (limitaciones honestas del monolito):**
  - Escala **verticalmente** (más CPU/RAM a la misma instancia) o
    replicando la app completa detrás de un balanceador, aunque solo
    una parte del tráfico (p. ej. subir imágenes) lo necesite.
  - La sesión en memoria impide correr múltiples instancias sin sticky
    sessions o un store de sesión compartido.
  - Si el catálogo, los pedidos o los usuarios crecieran mucho y
    necesitaran evolucionar/desplegarse de forma independiente, el
    siguiente paso natural (visto en clase) sería migrar hacia una
    **arquitectura desacoplada por componentes** (frontend, catálogo,
    inventario, etc. con bases de datos propias y contratos de
    comunicación), y solo si existiera una razón técnica u
    organizacional concreta, evolucionar hacia microservicios.

---

## 11. Reflexión (para la discusión en clase)

- **¿Un monolito siempre es mala arquitectura?** No. Para un sistema de
  este tamaño, con un solo equipo y un dominio estable, el monolito
  reduce complejidad operativa sin sacrificar buenas prácticas internas
  (separación de capas, SQL parametrizado, triggers para reglas
  críticas).
- **¿Qué separaría primero si el sistema creciera?** El módulo de
  **imágenes/archivos** (por su naturaleza de I/O intensivo y
  necesidad de almacenamiento distribuido) y el de **catálogo de
  búsqueda**, si el tráfico de lectura creciera mucho más que el de
  escritura.
- **¿Qué problemas aparecen al comunicarse por red?** Latencia,
  timeouts, fallos parciales, necesidad de reintentos/circuit breakers,
  consistencia eventual en vez de transacciones ACID entre componentes.
- **¿Cuándo una base compartida genera demasiado acoplamiento?** Cuando
  distintos equipos necesitan cambiar el esquema de la misma tabla con
  ritmos y objetivos distintos, o cuando una tabla se vuelve un cuello
  de botella de escritura para módulos que deberían evolucionar por
  separado.
