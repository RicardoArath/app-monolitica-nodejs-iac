# 📝 Reflexión Técnica sobre la Integración de Microservicios

**Alumno:** Ricardo Arath Martínez Sánchez  
**Matrícula:** 583928  
**Actividad:** Cliente de Escritorio Python (Tkinter) y Microservicios REST (Flask + PostgreSQL en GCP)

---

A partir del diseño del plan de implementación, la mayor dificultad técnica consistió en sincronizar el cliente de escritorio con dos microservicios independientes y resolver las incompatibilidades en la capa de persistencia y red. En el backend, al invocar `POST /books`, PostgreSQL rechazaba la ejecución porque Psycopg 3 infería argumentos no tipados (`unknown`) en arreglos vacíos de autores y géneros; se solventó aplicando *type casts* explícitos (`%s::int[]`, `%s::numeric`) en `sp_create_book`. Asimismo, en la infraestructura en la nube de GCP, el bloqueo perimetral del puerto 25 obligó a desacoplar el envío de correos con timeouts estrictos para no degradar el registro de usuarios.

En cuanto a la tolerancia a fallos, si un microservicio como el de libros se detiene durante la operación, la arquitectura asíncrona implementada con hilos (`threading.Thread`) evita que la interfaz gráfica se congele o colapse. El sistema captura la excepción de red, conmuta el semáforo visual a 🔴 Rojo indicando la caída y despliega un diálogo controlado al usuario, permitiendo que las demás funciones (como la autenticación o configuración) sigan operando y reconectándose automáticamente al restablecer el servicio.

Consumir servicios remotos en GCP evidenció diferencias críticas frente al entorno local: la latencia de red demandó políticas de reintentos y timeouts más amplios (`10s` conexión / `30s` lectura), además de configurar reglas de firewall en la VPC. Finalmente, la aplicación de escritorio jamás debe conectarse directamente a la base de datos: exponer credenciales y puertos de PostgreSQL en clientes finales representa una grave vulnerabilidad de seguridad, rompe el desacoplamiento arquitectónico y destruye la encapsulación de las reglas de negocio que los contratos REST (`200`, `201`, `401`, `409`) deben gobernar.

