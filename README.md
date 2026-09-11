# Librería en línea — Aplicación Web Monolítica

Proyecto del **Ejercicio Guiado 02** (SC3705 · Integración de Aplicaciones
Computacionales). Aplicación web **monolítica** en **Node.js + Express + EJS**
que gestiona una librería en línea con acceso directo a **PostgreSQL**.

> Restricción arquitectónica respetada: no hay APIs REST/GraphQL/SOAP ni
> intercambio de datos en JSON/XML. Todo el renderizado ocurre en el
> servidor y los formularios HTML postean directamente a las rutas de
> este mismo proceso. `package.json` existe únicamente porque `npm` lo
> requiere para administrar dependencias.

## 1. Requisitos

- Node.js 18+ (usa `fetch`/`--watch`, pero solo `--watch` es opcional)
- PostgreSQL 14+ (probado con **CentOS 10 Stream** en GCP Compute Engine,
  según el escenario de la clase)
- Extensión `pgcrypto` disponible en el servidor de PostgreSQL

## 2. Estructura del proyecto

```
libreria-online/
├── app.js                  # Punto de entrada del monolito (Express)
├── config/db.js            # Pool de conexión a PostgreSQL
├── middleware/
│   ├── auth.js             # Sesión, requireLogin, requireAdmin
│   └── upload.js           # multer: subida de imágenes JPG/PNG/WebP
├── routes/
│   ├── authRoutes.js       # /login /register /logout
│   ├── catalogRoutes.js    # / (catálogo) /books/:id (detalle)
│   └── adminRoutes.js      # /admin/** (CRUD completo)
├── services/                # Acceso a datos (SQL parametrizado con pg)
│   ├── userService.js
│   ├── bookService.js
│   └── catalogService.js
├── views/                   # Plantillas EJS (renderizado server-side)
├── public/
│   ├── css/style.css
│   └── uploads/             # Imágenes subidas por el administrador
├── db/                      # Scripts SQL (ver sección 3)
└── docs/
  ├── DECISIONES.md        # Documento inicial de decisiones
  ├── ENGINEERING_DECISIONS.md # Registro trazable de decisiones
  ├── REQUIREMENTS.md      # Requisitos y criterios de aceptación
  └── DB_DESIGN_ER3FN.md   # Diseño entidad-relación inicial
```

El alcance y los criterios de aceptación están definidos en
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md). El registro formal de
decisiones se mantiene en
[`docs/ENGINEERING_DECISIONS.md`](docs/ENGINEERING_DECISIONS.md).

## 3. Puesta en marcha de la base de datos

Ejecutar en este orden, conectado al host de PostgreSQL:

```bash
psql -U postgres    -h <host> -f db/00_create_database.sql
psql -U libreria_app -h <host> -d libreria_online -f db/01_schema.sql
psql -U libreria_app -h <host> -d libreria_online -f db/02_seed_30_per_table.sql
psql -U libreria_app -h <host> -d libreria_online -f db/03_all_quieries_before_stored_procedures.sql
psql -U libreria_app -h <host> -d libreria_online -f db/04_stored_procedures.sql
psql -U libreria_app -h <host> -d libreria_online -f db/05_triggers.sql
psql -U libreria_app -h <host> -d libreria_online -f db/06_views.sql
```

> `03_all_quieries_before_stored_procedures.sql` contiene las consultas de
> referencia con `$1, $2...` que usa la app; no crea objetos, solo
> documenta las sentencias antes de encapsularlas en `sp_*` (procedimientos).

Después del seed, existe un usuario **administrador único**:

- usuario: `admin`
- contraseña: `Passw0rd!`  *(cámbiala en producción)*

## 4. Puesta en marcha de la aplicación Node.js

```bash
cp .env.example .env
# editar .env con host/usuario/password reales de PostgreSQL
npm install
npm start
```

La app queda disponible en `http://localhost:3000` (o el `PORT` que definas).

Para desarrollo con recarga automática: `npm run dev`.

## 5. Funcionalidades

- **Autenticación:** registro y login con contraseñas hasheadas (`bcryptjs`).
  Un único administrador, protegido por índice único parcial en la BD.
- **Usuario regular:** consulta el catálogo, busca por título/ISBN y ve el
  detalle de cada libro (autores, géneros, conceptos, imágenes).
- **Administrador actual:** libros, autores, géneros, formatos, categorías,
  conceptos por libro e imágenes (JPG/PNG/WebP vía `multipart/form-data`,
  guardadas en `public/uploads`). La administración de usuarios, capítulo y
  página de conceptos y texto alternativo de imágenes forman parte de la
  siguiente fase.
- Todas las consultas usan **SQL parametrizado** (`pg`), nunca concatenación
  de strings con datos de usuario.

El alcance acordado también incluye un flujo académico de carrito, pedidos y
pago simulado. No se integrarán pagos reales ni proveedores externos; estas
funciones se implementarán después de completar el modelo de datos y sus
pruebas de integridad.

## 6. Verificación de integridad (Parte 2, punto 4 del ejercicio)

Con la base ya creada, para comprobar la regla de "máximo un administrador":

```sql
INSERT INTO users (username, email, password_hash, role)
VALUES ('otro_admin', 'otro@correo.com', crypt('Passw0rd!', gen_salt('bf')), 'admin');
```

PostgreSQL rechaza el segundo administrador con un error de violación del
índice único parcial `one_admin_only`:

```
ERROR:  duplicate key value violates unique constraint "one_admin_only"
DETAIL:  Key (role)=(admin) already exists.
```

Esto documenta también el comportamiento pedido en la Parte 2 del ejercicio.

## 7. Documentación de ingeniería

Consulta [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) para los requisitos,
actores y criterios de aceptación. Consulta
[`docs/ENGINEERING_DECISIONS.md`](docs/ENGINEERING_DECISIONS.md) para la
justificación de arquitectura, datos, seguridad, archivos, compra y
despliegue. [`docs/DECISIONES.md`](docs/DECISIONES.md) conserva el documento
inicial de decisiones y contexto del diseño.
