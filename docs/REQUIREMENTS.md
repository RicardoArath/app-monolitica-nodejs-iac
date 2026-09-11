# Requisitos de la libreria en linea

## 1. Alcance

La aplicacion es un monolito server-side construido con Node.js, Express, EJS y PostgreSQL. La interfaz se entrega como HTML renderizado en el servidor y los formularios envian datos directamente al proceso Express.

El alcance incluye catalogo, administracion, conceptos, imagenes y un flujo academico de compra con pago simulado. No incluye cobros reales, integracion con proveedores externos ni microservicios.

## 2. Actores

| Actor | Puede hacer | Debe rechazarse |
|---|---|---|
| Visitante | Ver login y registro | Catalogo, detalle, carrito, pedidos y administracion |
| Usuario registrado | Consultar catalogo, buscar, ver detalles, gestionar su carrito, crear pedidos y consultar sus pedidos | CRUD administrativo, modificar otros usuarios o consultar pedidos ajenos |
| Administrador | Todo lo del usuario y CRUD de libros, catalogos, usuarios, conceptos, imagenes, pedidos y pagos simulados | Crear un segundo administrador o eliminar datos protegidos por relaciones |

## 3. Requisitos funcionales

### Autenticacion y usuarios

- **RF-01. Registro:** El visitante puede registrar una cuenta con nombre de usuario, correo y contrasena valida.
- **RF-02. Inicio de sesion:** Un usuario registrado puede iniciar sesion con credenciales validas.
- **RF-03. Cierre de sesion:** Un usuario autenticado puede cerrar su sesion.
- **RF-04. Hash de contrasenas:** El sistema nunca almacena contrasenas en texto plano.
- **RF-05. Roles:** El sistema distingue entre usuario regular y administrador.
- **RF-06. Administrador unico:** La base de datos impide crear mas de un administrador.
- **RF-07. CRUD de usuarios:** El administrador puede consultar, crear, modificar y eliminar usuarios respetando las reglas de rol y relaciones.
- **RF-08. Aislamiento de usuarios:** Un usuario regular no puede modificar cuentas ni datos de otros usuarios.

### Catalogo y libros

- **RF-09. Catalogo autenticado:** Un usuario autenticado puede consultar el catalogo de libros.
- **RF-10. Busqueda:** El usuario puede buscar libros por ISBN o coincidencias en el titulo.
- **RF-11. Detalle:** El usuario puede consultar titulo, ISBN, ano, precio, existencia, formato, categoria, autores, generos, conceptos e imagenes de un libro.
- **RF-12. CRUD de libros:** El administrador puede crear, consultar, modificar y eliminar libros.
- **RF-13. CRUD de autores:** El administrador puede crear, consultar, modificar y eliminar autores.
- **RF-14. CRUD de generos:** El administrador puede crear, consultar, modificar y eliminar generos.
- **RF-15. CRUD de formatos:** El administrador puede crear, consultar, modificar y eliminar formatos.
- **RF-16. CRUD de categorias:** El administrador puede crear, consultar, modificar y eliminar categorias.
- **RF-17. Relaciones libro-autor:** Un libro puede tener varios autores y un autor puede participar en varios libros.
- **RF-18. Relaciones libro-genero:** Un libro puede tener varios generos y un genero puede clasificar varios libros.
- **RF-19. Precio y stock:** El administrador puede registrar y modificar precio y existencia de cada libro.

### Conceptos e imagenes

- **RF-20. Conceptos por libro:** El administrador puede crear, consultar, modificar y eliminar conceptos asociados a un libro.
- **RF-21. Definiciones por libro:** Cada concepto puede tener una definicion especifica para el libro donde aparece.
- **RF-22. Referencia editorial:** Un concepto puede registrar referencia opcional a capitulo y pagina.
- **RF-23. Carga de imagenes:** El administrador puede cargar imagenes JPG, PNG o WebP mediante formulario multipart.
- **RF-24. Metadatos de imagen:** Cada imagen conserva nombre generado por el sistema, MIME, texto alternativo y fecha de carga.
- **RF-25. Portada:** El administrador puede marcar una imagen como portada y el sistema mantiene como maximo una portada por libro.
- **RF-26. Eliminacion de imagenes:** El administrador puede eliminar una imagen y su archivo asociado sin dejar referencias invalidas.

### Compra academica y pago simulado

- **RF-27. Carrito:** Un usuario autenticado puede agregar libros con una cantidad valida, modificar cantidades y eliminar elementos.
- **RF-28. Validacion de stock:** El sistema no permite agregar ni confirmar cantidades superiores al stock disponible.
- **RF-29. Creacion de pedido:** El usuario puede confirmar su carrito y crear un pedido con sus partidas, precios y total calculados por el servidor.
- **RF-30. Descuento atomico:** La confirmacion del pedido descuenta stock dentro de una transaccion y revierte todos los cambios si alguna validacion falla.
- **RF-31. Estado de pedido:** El sistema registra y muestra estados validos del pedido, por ejemplo pendiente, confirmado, enviado, cancelado y completado.
- **RF-32. Historial propio:** El usuario puede consultar unicamente sus propios pedidos y sus detalles.
- **RF-33. Administracion de pedidos:** El administrador puede consultar pedidos y actualizar su estado.
- **RF-34. Pago simulado:** El usuario puede seleccionar un resultado simulado aprobado o rechazado; no se procesan tarjetas ni dinero real.
- **RF-35. Consistencia del pago:** Un pago rechazado no confirma el pedido ni descuenta stock; un pago aprobado deja el pedido en el estado definido por el negocio.

### Persistencia y base de datos

- **RF-36. Integridad relacional:** Las relaciones entre libros, catalogos, conceptos, imagenes, carritos y pedidos se protegen con claves foraneas.
- **RF-37. Operaciones SQL:** Las operaciones de la aplicacion utilizan consultas parametrizadas o procedimientos almacenados con parametros.
- **RF-38. Vistas y procedimientos:** El sistema conserva vistas y procedimientos para consultas y operaciones compuestas justificadas.

## 4. Requisitos no funcionales

- **RNF-01. Arquitectura:** La solucion se despliega como una sola unidad monolitica Node.js.
- **RNF-02. Presentacion:** Las vistas se renderizan con EJS en el servidor; no se desarrollan APIs REST, GraphQL o SOAP.
- **RNF-03. Intercambio:** Los formularios usan `application/x-www-form-urlencoded` o `multipart/form-data`; no se usa JSON/XML como mecanismo de comunicacion de la aplicacion.
- **RNF-04. Seguridad SQL:** Ningun valor proporcionado por el usuario se concatena directamente en una consulta SQL.
- **RNF-05. Validacion:** Todo dato recibido se valida en el servidor aunque exista validacion HTML.
- **RNF-06. Autorizacion:** Cada ruta administrativa requiere sesion valida y rol administrador.
- **RNF-07. Sesiones:** Las cookies de sesion deben ser HTTP-only, tener expiracion definida y configuracion segura para el entorno.
- **RNF-08. Secretos:** Credenciales, claves de sesion, tokens y archivos `.env` no se publican ni se incluyen en el paquete final.
- **RNF-09. Archivos:** Las imagenes se validan por tipo permitido, tamano maximo, nombre generado y referencia segura.
- **RNF-10. Integridad:** PostgreSQL protege unicidad, rangos, relaciones, stock y administrador unico aun si la aplicacion se omite.
- **RNF-11. Errores:** El usuario recibe mensajes controlados; los detalles de SQL y stack traces no se exponen en produccion.
- **RNF-12. Mantenibilidad:** La presentacion, rutas, servicios, middleware, configuracion y acceso a datos permanecen separados.
- **RNF-13. Rendimiento:** El catalogo usa indices y paginacion para evitar cargar todos los libros en una sola respuesta.
- **RNF-14. Disponibilidad:** La aplicacion se ejecuta detras de Apache o NGINX y Node escucha solo en localhost.
- **RNF-15. Trazabilidad:** Cada requisito implementado debe relacionarse con pruebas y evidencia reproducible.
- **RNF-16. Despliegue:** La instalacion de base de datos y aplicacion debe documentarse sin publicar secretos.
- **RNF-17. Usabilidad:** Los formularios muestran errores comprensibles, estados vacios y confirmaciones de operaciones.
- **RNF-18. Compatibilidad:** La interfaz debe funcionar en navegadores modernos de escritorio y movil.

## 5. Supuestos

1. El ejercicio se ejecuta con PostgreSQL 14 o superior y la extension `pgcrypto` disponible.
2. El administrador inicial se crea mediante el seed o un procedimiento controlado.
3. El pago simulado representa un escenario academico y no constituye una operacion financiera.
4. Las imagenes se almacenan en el servidor durante el despliegue de una sola instancia.
5. Los precios y totales se calculan en el servidor y no se aceptan como valores confiables del navegador.
6. La aplicacion opera bajo el prefijo `/library` al publicarse mediante reverse proxy.

## 6. Restricciones

1. Se conserva la arquitectura monolitica server-side.
2. No se agregan microservicios, APIs publicas, SPA ni proveedores de pago reales.
3. El proyecto debe usar PostgreSQL mediante `pg` y consultas parametrizadas.
4. El codigo fuente no debe depender de secretos incluidos en el repositorio.
5. Debe existir como maximo un usuario con rol administrador.
6. El paquete final debe excluir `.env`, `node_modules`, llaves privadas, tokens y contrasenas reales.

## 7. Criterios de aceptacion

- **CA-01:** Un visitante no puede acceder al catalogo, detalle, carrito, pedidos ni administracion.
- **CA-02:** Un usuario regular puede autenticarse, buscar libros, consultar detalles, comprar con pago aprobado y consultar su historial.
- **CA-03:** Un usuario regular recibe acceso denegado al intentar cualquier ruta administrativa.
- **CA-04:** El administrador puede completar los CRUD definidos y gestionar relaciones, conceptos e imagenes.
- **CA-05:** Un segundo administrador es rechazado por PostgreSQL y la aplicacion muestra un mensaje controlado.
- **CA-06:** ISBN duplicado, stock negativo, precio invalido, FK inexistente y cantidades sin stock son rechazados.
- **CA-07:** Conceptos e imagenes de un libro no pueden modificarse usando el ID de otro libro.
- **CA-08:** Un archivo no permitido o mayor al limite es rechazado y no queda almacenado como archivo utilizable.
- **CA-09:** Un pago simulado rechazado no descuenta stock ni confirma el pedido.
- **CA-10:** Un pedido aprobado descuenta stock una sola vez y conserva sus precios historicos.
- **CA-11:** Las consultas con caracteres especiales no alteran la consulta SQL ni exponen datos de otros registros.
- **CA-12:** La aplicacion funciona en `127.0.0.1:3000/library` y mediante reverse proxy bajo `/library`.
- **CA-13:** La entrega incluye requisitos, decisiones, normalizacion 4FN, diagramas, SQL, seguridad, pruebas, GCP, despliegue y evidencias.
- **CA-14:** La publicacion externa funciona sin sesion previa y no expone secretos ni archivos privados.
