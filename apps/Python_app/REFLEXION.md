# 📝 Reflexión Técnica sobre la Implementación de Autenticación JWT en Microservicios

**Alumno:** Ricardo Arath Martínez Sánchez  
**Matrícula:** 583928  
**Actividad:** Protección de Microservicios Distribuidos con JSON Web Tokens (JWT) y Adaptación de Cliente Python Tkinter  

---

### 1. Justificación Arquitectónica: Sesiones de Estado vs Autenticación Stateless con JWT
La transición de un esquema tradicional basado en sesiones con cookies a una arquitectura orientada a **JSON Web Tokens (JWT)** responde a la necesidad de mantener el desacoplamiento estricto entre microservicios. En un entorno distribuido, si el servicio de catálogo de libros dependiera de verificar sesiones contra la base de datos o memoria del servicio de autenticación, se introduciría un cuello de botella crítico y una dependencia directa que anularía la autonomía de cada componente.

Con JWT, el microservicio de **Login (`:5000`)** actúa como la única Autoridad de Emisión: tras validar las credenciales del usuario con bcrypt, genera un token criptográficamente firmado mediante el algoritmo **HS256** utilizando una clave simétrica secreta (`JWT_SECRET`). Dicho token encapsula en sus claims la identidad del sujeto (`sub`), su rol, nombre y el tiempo de expiración (`exp`), garantizando integridad matemática contra modificaciones en tránsito.

Por su parte, el microservicio de **Books (`:5001`)** implementa un guard (`@jwt_required`) que valida de forma autónoma la firma digital del encabezado `Authorization: Bearer <token>` sin realizar consultas de red ni accesos adicionales a la base de datos de usuarios. Esta validación *stateless* (sin estado) reduce la latencia en las operaciones de escritura y permite escalar horizontalmente los microservicios de negocio sin preocuparse por replicación de sesiones.

---

### 2. Estrategia de Protección Granular: Rutas de Escritura vs Consulta Pública
Un requerimiento fundamental del sistema consistió en preservar la accesibilidad pública del catálogo sin comprometer la integridad de la base de datos:
- **Operaciones de Lectura Públicas (`GET /books`, `GET /books/{isbn}`, `GET /catalogs`):** Permanecen abiertas a cualquier visitante o cliente sin exigir token alguno. Esto optimiza el rendimiento y facilita la indexación y navegación libre de los recursos editoriales.
- **Operaciones de Escritura Protegidas (`POST`, `PUT`, `PATCH`, `DELETE /books`):** Exigen estrictamente un token JWT válido y no expirado. Cualquier intento de crear, sobreescribir completamente, actualizar campos específicos o eliminar un libro sin el encabezado correspondiente es interceptado de inmediato por el middleware retornando un código de estado `401 Unauthorized` con un payload informativo.

---

### 3. Adaptación del Cliente de Escritorio Python Tkinter y Tolerancia a Fallos
La aplicación cliente fue reconstruida para orquestar el ciclo de vida del JWT de manera transparente:
1. **Captura y Almacenamiento Seguro:** Al iniciar sesión en la pestaña Perfil, el cliente HTTP (`ApiClient`) extrae el token emitido por el servicio de login y lo almacena en memoria, además de persistirlo de forma cifrada en el archivo `session.json` local.
2. **Inyección Automática de Encabezados:** Toda petición subsecuente intercepta dinámicamente si existe un token en la sesión e inyecta el header `Authorization: Bearer <token>`.
3. **Manejo Resiliente de Excepciones:** Si el token expira o el servidor responde `401 Unauthorized`, el cliente no se bloquea ni genera excepciones no controladas; despliega una alerta explicativa al usuario invitándolo a reautenticarse y limpia el estado local para evitar inconsistencias.
4. **Trazabilidad y Observabilidad en Consola:** Se integró un sistema de logs en tiempo real con prefijos claros (`[JWT-CLIENT]`, `[JWT-GUARD]`, `[AUTH-SERVICE]`), lo que permite auditar en vivo la transmisión del token, los códigos HTTP y los tiempos de expiración durante las pruebas de integración.
