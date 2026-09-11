# Registro de decisiones de ingenieria

Este registro aplica el formato: **necesidad o problema -> alternativas consideradas -> decision -> justificacion tecnica -> riesgo o limitacion -> evidencia de validacion**.

## ED-01. Monolito server-side

- **Necesidad o problema:** Construir una libreria en linea para un equipo pequeno, con una sola unidad de despliegue y sin APIs entre componentes.
- **Alternativas consideradas:** Monolito sin separacion interna, monolito modular, frontend desacoplado con API y microservicios.
- **Decision:** Monolito modular server-side con Node.js, Express, EJS y PostgreSQL.
- **Justificacion tecnica:** El dominio y el equipo tienen un tamano acotado. Un solo proceso simplifica despliegue, transacciones, depuracion y operacion, mientras `routes/`, `services/`, `middleware/`, `views/` y `config/` conservan separacion de responsabilidades.
- **Riesgo o limitacion:** La aplicacion escala como una unidad y un error de despliegue puede afectar todas las funciones. La sesion y los archivos locales requieren una estrategia adicional si se agregan instancias.
- **Evidencia de validacion:** Estructura del proyecto, rutas EJS funcionales, pruebas de navegacion y despliegue mediante reverse proxy. Pendiente: diagrama `docs/ARCHITECTURE_MONOLITHIC.png` y captura de flujo completo.

## ED-02. Renderizado con EJS

- **Necesidad o problema:** Entregar HTML desde el servidor y enviar formularios directamente al monolito.
- **Alternativas consideradas:** EJS server-side, SPA con React/Vue, plantillas estaticas con JavaScript cliente.
- **Decision:** EJS como motor de vistas y formularios HTML tradicionales.
- **Justificacion tecnica:** Cumple la restriccion del ejercicio, reduce complejidad de frontend y permite que autenticacion, autorizacion y validacion se concentren en el servidor.
- **Riesgo o limitacion:** Las interacciones dinamicas requieren una nueva respuesta HTML y la experiencia puede ser menos rica que una SPA.
- **Evidencia de validacion:** Vistas en `views/`, `res.render()` en las rutas y ausencia de endpoints JSON. Pendiente: prueba manual de formularios y navegacion bajo `/library`.

## ED-03. Acceso directo a PostgreSQL con `pg`

- **Necesidad o problema:** Persistir datos relacionales y aplicar integridad fuerte desde la aplicacion.
- **Alternativas consideradas:** ORM, API intermedia, microservicio de datos y consultas directas con `pg`.
- **Decision:** Pool centralizado de `pg` en `config/db.js`, con consultas parametrizadas y procedimientos almacenados para operaciones compuestas.
- **Justificacion tecnica:** PostgreSQL puede proteger directamente PK, FK, `CHECK`, `UNIQUE`, triggers y transacciones. `pg` mantiene visible el SQL requerido por el ejercicio y evita una capa innecesaria.
- **Riesgo o limitacion:** El equipo debe revisar manualmente SQL, transacciones y ciclo de vida del esquema. Los scripts actuales son de laboratorio y requieren endurecimiento para despliegue.
- **Evidencia de validacion:** `config/db.js`, servicios con parametros `$1`, scripts `db/03` a `db/06` y pruebas negativas de PostgreSQL. Pendiente: matriz de pruebas y ejecucion documentada.

## ED-04. Modelo normalizado hasta 4FN

- **Necesidad o problema:** Un libro puede tener multiples autores, generos, conceptos e imagenes independientes.
- **Alternativas consideradas:** Listas separadas por comas, arrays dentro de `books`, una tabla ancha con combinaciones o tablas puente/hijas.
- **Decision:** Tablas independientes para catalogos, tablas puente para relaciones N:M y tablas hijas para conceptos e imagenes.
- **Justificacion tecnica:** Las tablas puente `book_authors` y `book_genres` eliminan dependencias multivaluadas independientes. `book_concepts` permite definiciones distintas por libro y `book_images` conserva metadatos y varias imagenes sin columnas repetitivas.
- **Riesgo o limitacion:** El detalle necesita varias consultas y el modelo requiere mas tablas que una estructura desnormalizada.
- **Evidencia de validacion:** `db/01_schema.sql`, relaciones FK y restricciones `UNIQUE`. Pendiente: evolucion demostrable 1FN -> 2FN -> 3FN/BCNF -> 4FN en `docs/NORMALIZATION_4FN.xlsx` y diagrama ER PNG.

## ED-05. Integridad critica en PostgreSQL

- **Necesidad o problema:** Evitar que reglas como un solo administrador, stock no negativo o una sola portada dependan unicamente de la interfaz.
- **Alternativas consideradas:** Validacion solo en rutas, validacion solo en vistas, validacion en servicios y defensa adicional en PostgreSQL.
- **Decision:** Aplicar validacion en servidor y restricciones, procedimientos y triggers en PostgreSQL.
- **Justificacion tecnica:** Cualquier cliente de la base de datos queda sujeto a las reglas criticas. La defensa en profundidad reduce inconsistencias por errores de interfaz o futuras rutas.
- **Riesgo o limitacion:** Los mensajes de PostgreSQL deben traducirse a respuestas controladas y los scripts deben ejecutarse en el orden correcto.
- **Evidencia de validacion:** Indice parcial `one_admin_only`, `CHECK` de stock/precio, FK, `book_images_single_primary` y procedimientos `sp_*`. Pendiente: capturas `psql` de errores reales.

## ED-06. Sesiones de servidor

- **Necesidad o problema:** Mantener autenticacion sin tokens ni intercambio JSON.
- **Alternativas consideradas:** Sesiones en memoria, sesiones persistidas en PostgreSQL, Redis, JWT y cookies con datos de usuario.
- **Decision:** Usar sesiones de servidor con cookie HTTP-only. Antes del despliegue se debe resolver si se adopta `connect-pg-simple` o se limita formalmente a una sola instancia.
- **Justificacion tecnica:** El estado no se expone al cliente y el modelo encaja con formularios server-side. PostgreSQL es una opcion coherente con la infraestructura existente.
- **Riesgo o limitacion:** `MemoryStore` pierde sesiones al reiniciar y no permite escalar horizontalmente. No debe usarse como configuracion final para varias instancias.
- **Evidencia de validacion:** `express-session`, cookie HTTP-only y expiracion configurada en `app.js`. Pendiente: decision final, regeneracion posterior al login y prueba de reinicio/despliegue.

## ED-07. Carga de imagenes en disco

- **Necesidad o problema:** Permitir imagenes JPG, PNG y WebP sin convertirlas a JSON o base64.
- **Alternativas consideradas:** Base de datos, almacenamiento local, almacenamiento de objetos y servicio externo de imagenes.
- **Decision:** `multer` con nombres generados por el sistema y almacenamiento en `public/uploads` durante el ejercicio.
- **Justificacion tecnica:** Es simple, compatible con `multipart/form-data` y suficiente para una instancia academica. Los metadatos se guardan en PostgreSQL.
- **Riesgo o limitacion:** El disco local no es adecuado para multiples instancias y el MIME declarado por el cliente no prueba el contenido real. Deben validarse tamanos, tipos, nombre y limpieza ante errores.
- **Evidencia de validacion:** `middleware/upload.js`, limite configurable y filtro de MIME. Pendiente: texto alternativo, magic bytes, persistencia y pruebas de archivos invalidos.

## ED-08. Compra academica con pago simulado

- **Necesidad o problema:** Extender el catalogo a una compra verificable sin introducir credenciales financieras ni un proveedor externo.
- **Alternativas consideradas:** Sin compra, pago real de terceros, pago simulado local.
- **Decision:** Carrito, pedido, detalle de pedido y pago simulado aprobado/rechazado, todo dentro del monolito.
- **Justificacion tecnica:** Permite demostrar relaciones, transacciones, stock, estados e integridad sin riesgos financieros ni dependencia externa. El precio historico se copia al detalle del pedido y el stock se valida en la transaccion.
- **Riesgo o limitacion:** No representa seguridad ni cumplimiento de pagos reales. Un cambio futuro a pagos reales requeriria proveedor, webhooks, secretos, idempotencia y auditoria.
- **Evidencia de validacion:** Pendiente de implementar: esquema, procedimientos, rutas, vistas y pruebas de pago aprobado/rechazado.

## ED-09. Reverse proxy bajo `/library`

- **Necesidad o problema:** Publicar Node sin exponerlo directamente a Internet y cumplir la URL requerida por el ejercicio.
- **Alternativas consideradas:** Exponer Node en el puerto publico, Apache o NGINX como reverse proxy.
- **Decision:** Node escuchara en `127.0.0.1:3000`; Apache o NGINX publicara `/library` y reenviara al proceso.
- **Justificacion tecnica:** El proxy centraliza entrada, puede terminar TLS y permite mantener Node aislado del trafico externo.
- **Riesgo o limitacion:** Enlaces, formularios, recursos estaticos, sesiones y redirecciones deben respetar el prefijo. Una configuracion incorrecta puede producir rutas rotas o cookies inconsistentes.
- **Evidencia de validacion:** Pendiente: `docs/GCP_COMMANDS.md`, archivo de proxy, prueba local y prueba externa bajo `/library`.

## ED-10. Pruebas como evidencia

- **Necesidad o problema:** Demostrar que las funciones y las restricciones se comportan como se afirma.
- **Alternativas consideradas:** Capturas aisladas, pruebas manuales sin matriz, pruebas automatizadas y matriz con evidencia.
- **Decision:** Combinar pruebas automatizadas, pruebas SQL negativas, pruebas manuales de navegador y `docs/TEST_PLAN.md`.
- **Justificacion tecnica:** Las pruebas automatizadas detectan regresiones; las pruebas SQL verifican integridad; las capturas documentan despliegue y usabilidad. La matriz relaciona cada resultado con un requisito.
- **Riesgo o limitacion:** Las pruebas de infraestructura dependen de PostgreSQL, GCP y reverse proxy disponibles.
- **Evidencia de validacion:** Pendiente: minimo 15 casos documentados, resultados observados, estados y capturas explicadas.

## ED-11. Correccion de inconsistencias entre esquema SQL y capa de aplicacion

- **Necesidad o problema:** Se detectaron tres inconsistencias criticas entre el esquema de BD y la aplicacion Node.js:
  1. `book_images.alt_text` es `NOT NULL` pero `bookService.addImage()` no lo enviaba, provocando error 500 en toda subida de imagen.
  2. `book_concepts.chapter` y `book_concepts.page_number` existian en la BD pero eran ignorados por las funciones de servicio, rutas y formularios (RF-22 incumplido).
  3. La vista `v_catalog` ya exponia `cover_image` y `cover_alt_text` pero `views/books/index.ejs` siempre renderizaba un placeholder con la inicial del titulo.
- **Alternativas consideradas:**
  1. Relajar el esquema (hacer `alt_text` nullable o con valor por defecto) para que el INSERT no fallara.
  2. Corregir la capa de aplicacion para respetar el contrato de la BD.
- **Decision:** Opcion 2. Ajustar servicio, ruta y vista para enviar todos los campos que el esquema exige, sin debilitar las restricciones de PostgreSQL.
- **Justificacion tecnica:** Las restricciones `NOT NULL` y `CHECK` son defensas en profundidad que protegen la integridad del modelo aunque la aplicacion contenga errores. Relajarlas para evitar un bug de codigo contradice el principio de que la BD debe ser la ultima linea de validacion. Es mejor que la aplicacion cumpla el contrato.
- **Riesgo o limitacion:** Si en el futuro se agregan columnas obligatorias al esquema, debe verificarse que las funciones de servicio las incluyan. Se recomienda agregar una prueba negativa que verifique que el INSERT funciona con todos los campos requeridos.
- **Evidencia de validacion:** `node -e "require('./services/bookService')"` carga sin error. Las firmas de `addImage()` (5 parametros) y `addConcept()`/`updateConcept()` (5 parametros) coinciden con las columnas declaradas en `01_schema.sql`. `views/books/index.ejs` condiciona la portada a `b.cover_image` antes de renderizar.

## ED-12. Flujo de compra academica y simulacion de pago atómico

- **Necesidad o problema:** Implementar el proceso de compra (carrito, congelamiento de precios históricos, validación y descuento de existencias) y el pago simulado garantizando consistencia transaccional y cumplimiento de los requisitos RF-27 al RF-35.
- **Alternativas consideradas:**
  1. Realizar múltiples consultas individuales desde Node.js: consultar items del carrito, verificar stock, insertar orden, insertar partidas, actualizar stock y borrar el carrito.
  2. Encapsular la transacción completa en el procedimiento almacenado `sp_checkout_cart` en PostgreSQL utilizando bloqueos de fila `FOR UPDATE`, y exponer en la interfaz dos botones explícitos de simulación ("Simular pago APROBADO" y "Simular pago RECHAZADO") conforme a la opción elegida por el equipo de ingeniería.
- **Decision:** Alternativa 2. Delegar la transacción a `sp_checkout_cart` y controlar la simulación mediante formularios HTML tradicionales.
- **Justificacion tecnica:**
  - `FOR UPDATE` sobre los libros involucrados en un orden canónico previene condiciones de carrera e interbloqueos ante compras concurrentes del mismo título.
  - El uso de snapshots (`title_snapshot`, `unit_price`, `line_total`) en `order_items` asegura que el historial contable del pedido sea inmutable aunque el libro cambie de precio o se descontinúe.
  - Al simular un pago rechazado, el pedido se guarda en estado `pending`, no se descuenta stock y los artículos permanecen en el carrito para permitir reintentos, cumpliendo estrictamente con el RF-35.
  - Proveer controles explícitos para ambos resultados permite generar evidencia técnica verificable tanto para el camino feliz como para el camino alternativo en la matriz de pruebas.
- **Riesgo o limitacion:** Si la aplicación migrara a un procesador de pagos asíncrono real (como Stripe o MercadoPago con webhooks), la transacción atómica inmediata debería sustituirse por un flujo de dos fases con estados intermedios y retención temporal de inventario.
- **Evidencia de validacion:** `services/cartService.js`, `services/orderService.js`, `routes/cartRoutes.js`, `routes/orderRoutes.js`, `views/cart/index.ejs`, `views/orders/index.ejs`, `views/orders/detail.ejs`, `views/admin/orders-list.ejs`, `views/admin/order-detail.ejs`. Compilación verificada con `node -c app.js`.

