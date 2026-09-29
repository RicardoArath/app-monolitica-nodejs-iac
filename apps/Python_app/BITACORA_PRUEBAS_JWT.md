# 📋 Bitácora de Pruebas: Seguridad con JWT en Microservicios

**Alumno:** Ricardo Arath Martínez Sánchez  
**Matrícula:** 583928  
**Actividad:** Pruebas de Integración y Evidencias de JWT  

---

## 📊 Matriz de Pruebas y Evidencias Fotográficas

| N° | Caso de Prueba | Método HTTP | Endpoint / Recurso | Código Esperado | Código Obtenido | Resultado Observado | Archivo de Captura |
| :---: | :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| **01** | Formulario de autenticación con credenciales | `POST` | `/login` | `200 OK` | `200 OK` | Interfaz gráfica solicitando usuario y contraseña para emisión inicial de JWT. | `01_formulario_login_jwt.png` |
| **02** | Emisión, recepción y almacenamiento de JWT | `POST` | `/login` | `200 OK` | `200 OK` | Servidor emite JWT (`HS256`, 3600s). La app lo almacena en `ApiClient` y lo persiste en `session.json`. | `02_emision_y_almacenamiento_jwt.png` |
| **03** | Detección y rechazo de firma inválida / token alterado | `POST` | `/books` | `401 Unauthorized` | `401 Unauthorized` | Petición con firma de token no coincidente es rechazada: *"Token JWT inválido: Signature verification failed"*. | `03_seguridad_rechazo_401_firma_invalida.png` |
| **04** | Restauración de sesión y consultas con Authorization Bearer | `GET` | `/session` y `/books` | `200 OK` | `200 OK` | Token cargado desde caché local; peticiones inyectan `Authorization: Bearer <token>` y el catálogo responde correctamente. | `04_sesion_activa_y_consultas_bearer_jwt.png` |
| **05** | Creación de libro con token JWT válido | `POST` | `/books` | `201 Created` | `201 Created` | Token válido verificado por `@jwt_required`; inserción exitosa en PostgreSQL mediante stored procedure. | *(Verificado en consola/script)* |
| **06** | Acceso público al catálogo sin autenticación | `GET` | `/books` | `200 OK` | `200 OK` | Consulta libre de libros sin requerir encabezado de autorización ni credenciales. | *(Verificado en catálogo)* |

---

## 📁 Archivos de Evidencia Incluidos en este Paquete

Las capturas de pantalla están organizadas en la carpeta `evidencias_screenshots/`:
1. `01_formulario_login_jwt.png`
2. `02_emision_y_almacenamiento_jwt.png`
3. `03_seguridad_rechazo_401_firma_invalida.png`
4. `04_sesion_activa_y_consultas_bearer_jwt.png`
