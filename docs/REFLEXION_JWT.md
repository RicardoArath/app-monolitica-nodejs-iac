# 📝 Reflexión Técnica: Implementación de Arquitectura de Seguridad con JSON Web Tokens (JWT)

**Alumno:** Ricardo Arath Martínez Sánchez  
**Matrícula:** 583928  
**Materia / Práctica:** Ejercicio de Autenticación y Autorización con JWT en Microservicios Distribuidos  
**Fecha:** 29 de Septiembre de 2026  

---

## 1. Contexto y Objetivos del Ejercicio
El objetivo principal de esta sesión consistió en diseñar, implementar y verificar un esquema de seguridad perimetral basado en **JSON Web Tokens (JWT)** para proteger el ecosistema de microservicios de la librería en línea y reconstruir/adaptar la aplicación cliente de escritorio desarrollada en Python Tkinter.

Los requerimientos arquitectónicos establecidos fueron:
1. **Autoridad de Emisión (Microservicio Login - Puerto 5000):** Emisión de tokens firmados tras validar credenciales con bcrypt en `POST /login`, acompañados de endpoints especializados de validación (`POST /token/verify`) y renovación (`POST /token/refresh`).
2. **Protección Perimetral Granular (Microservicio Books - Puerto 5001):** Proteger estrictamente todas las operaciones de modificación de datos (`POST`, `PUT`, `PATCH`, `DELETE`) exigiendo el encabezado HTTP estándar `Authorization: Bearer <token>`, mientras se preserva el acceso público a las operaciones de solo lectura (`GET /books`, `GET /books/{isbn}`).
3. **Adaptación de la Aplicación Cliente (Python Tkinter):** Almacenar en memoria y persistir localmente el token recibido tras un login exitoso, inyectarlo automáticamente en las cabeceras de peticiones de escritura y capturar de forma controlada cualquier rechazo `401 Unauthorized` sin congelar ni cerrar la interfaz.
4. **Trazabilidad y Observabilidad:** Registrar logs descriptivos en la consola en cada etapa (emisión, validación, rechazo y renovación).

---

## 2. Decisiones de Diseño y Arquitectura Stateless

### Desacoplamiento Real entre Servicios
En una arquitectura monolítica tradicional, la autenticación depende de sesiones persistidas en memoria compartida o tablas de sesión en base de datos. En microservicios distribuidos, este enfoque genera un fuerte acoplamiento y cuellos de botella: cada vez que el microservicio de libros recibiera una petición, tendría que realizar una consulta de red o base de datos hacia el servicio de autenticación para comprobar si la sesión sigue viva.

Con la adopción de **JWT**, la autenticación pasa a ser completamente **stateless (sin estado)**:
- El servicio de login emite un token firmado con el algoritmo criptográfico **HS256** utilizando una clave simétrica compartida (`JWT_SECRET`).
- El token viaja auto-contenido, incluyendo los claims esenciales:
  - `sub`: Identificador único del usuario (almacenado estrictamente como `string` para cumplir con la especificación RFC 7519 y compatibilidad con PyJWT).
  - `username`, `email`, `role`, `nombre`: Atributos para auditoría y control de acceso basado en roles.
  - `iat`: Timestamp de emisión (*Issued At*).
  - `exp`: Timestamp de expiración (*Expiration Time* configurado a 60 minutos).
- El microservicio de libros valida la firma del token de manera puramente computacional a través de su middleware `@jwt_required`, sin emitir ninguna consulta de red hacia el servicio de login ni a la base de datos de usuarios.

---

## 3. Retos Técnicos y Soluciones Implementadas

### A. Tipado Estricto de Claims en la Librería PyJWT
Durante las primeras pruebas de integración, la validación del token arrojó el error `Token JWT inválido: Subject must be a string`. Las versiones modernas de PyJWT exigen que el claim estándar `sub` sea de tipo cadena de texto y no un entero. Se resolvió aplicando conversión explícita `str(user_id)` al construir el payload tanto en `routes/auth.py` como en `routes/token.py`.

### B. Cumplimiento de Longitud de Clave Criptográfica (RFC 7518)
Al validar tokens con HMAC-SHA256, se identificó la advertencia `InsecureKeyLengthWarning: The HMAC key is below the minimum recommended length of 32 bytes`. Se actualizó la clave secreta compartida al formato de 32 bytes (`libreria-jwt-secret-2026-seguro-key-32b`), garantizando entropía criptográfica robusta y eliminando advertencias en tiempo de ejecución.

### C. Codificación de Consola en Sistemas Operativos Heterogéneos (Windows vs Linux)
Al probar en Windows PowerShell con codificación de página de códigos `cp1252`, los caracteres especiales y emojis en los logs (`🔐`, `✅`, `❌`) provocaban excepciones `UnicodeEncodeError`. Se estandarizaron todos los mensajes de consola con identificadores legibles en ASCII (`[JWT-CLIENT]`, `[JWT-GUARD]`, `[AUTH-SERVICE]`), asegurando portabilidad idéntica tanto en entornos locales Windows como en servidores Linux en la nube (GCP).

### D. Verificación de Seguridad y Detección de Firmas Inválidas
En la fase de pruebas, se forzó el envío de tokens con claves modificadas y tokens previamente cacheados. El microservicio de libros rechazó de forma inmediata y certera las peticiones con `401 Unauthorized` bajo el mensaje `Signature verification failed`, confirmando que ningún usuario puede falsificar un token o enviar un token emitido con una clave no reconocida.

---

## 4. Conclusiones y Aprendizajes
La implementación de JWT demostró ser la solución idónea para la seguridad perimetral de microservicios:
- **Seguridad robusta:** Protege las operaciones críticas de escritura (creación, edición y eliminación) sin requerir almacenar credenciales ni contraseñas en el cliente.
- **Rendimiento:** Las lecturas se mantienen públicas y sin sobrecoste, mientras que las escrituras se autorizan en microsegundos mediante verificación matemática de firma.
- **Resiliencia en el cliente:** La aplicación Python Tkinter orquesta la inyección del header `Authorization: Bearer <token>` de forma transparente y desacoplada mediante un cliente HTTP centralizado, ofreciendo retroalimentación visual al usuario en caso de revocación o expiración.
