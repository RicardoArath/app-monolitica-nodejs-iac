# 📋 Bitácora de Pruebas de Integración

**Alumno:** Ricardo Arath Martínez Sánchez  
**Matrícula:** 583928  
**Proyecto:** Cliente Python Tkinter para Microservicios REST (Librería en Línea)  
**Servidor Remoto:** Google Cloud Platform (`http://35.193.230.144`)

---

## 📊 Matriz de Pruebas de Integración y Evidencias Fotográficas

| N° | Acción / Caso de Prueba | Método | Endpoint / Recurso | Código HTTP | Resultado Observado | Archivo de Captura de Pantalla |
| :---: | :--- | :---: | :--- | :---: | :--- | :--- |
| **01** | Inicio de sesión con credenciales válidas (admin) | `POST` | `/login` | `200 OK` | Autenticación correcta, cookie de sesión almacenada y redirección al catálogo. | `01_pantalla_inicial_login.png` |
| **02** | Intento de inicio de sesión con datos incorrectos | `POST` | `/login` | `401 Unauthorized` | Mensaje controlado en interfaz: "Credenciales incorrectas", sin crash en la app. | `04_intento_login_incorrecto.png` |
| **03** | Reto CAPTCHA para validación humana | `GET` | `/captcha` | `200 OK` | Generación de reto matemático ("¿Cuánto es 1 + 10?") y recepción de `captcha_id`. | `02_registro_usuario_captcha.png` |
| **04** | Registro de nuevo usuario con datos válidos | `POST` | `/register` | `201 Created` | Usuario registrado en PostgreSQL y generación de token de verificación. | `02_registro_exitoso_modal.png` |
| **05** | Intento de registro con correo ya existente | `POST` | `/register` | `409 Conflict` | Mensaje controlado: "El correo ya está registrado en el sistema" (conflicto 409). | `03_registro_correo_duplicado_409.png` |
| **06** | Verificación de email mediante token | `GET` | `/verify?token=...` | `200 OK` | Activación de cuenta en PostgreSQL (`email_verified = true`), habilitando login. | `01_pantalla_inicial_login.png` |
| **07** | Validación de sesión persistida al abrir la app | `GET` | `/session` | `200 OK` | Carga de `session.json`, validación con el servidor y acceso directo sin login. | `05_panel_principal_catalogo.png` |
| **08** | Extensión de tiempo de vida de sesión activa | `POST` | `/session/extend` | `200 OK` | Temporizador de inactividad reiniciado a 30 minutos y notificación visual. | `07_perfil_del_usuario.png` |
| **09** | Actualización de perfil del usuario | `PATCH` | `/profile` | `200 OK` | Modificación de nombre y apellidos reflejados inmediatamente en sesión y DB. | `07_perfil_del_usuario.png` |
| **10** | Consulta general del catálogo de libros | `GET` | `/books?format=json` | `200 OK` | Carga de 31 libros remotos con paginación, autores, géneros, precios y stock. | `08_catalogo_de_libros_general.png` |
| **11** | Búsqueda y filtrado de libros por título | `GET` | `/books?title=alquimia` | `200 OK` | Filtrado instantáneo mostrando libro ("Alquimia en los Fogones Olvidados"). | `09_busqueda_filtrado_titulo.png` |
| **12** | Búsqueda de libros por código ISBN | `GET` | `/books?isbn=978-0-000014-4` | `200 OK` | Coincidencia exacta mostrada en la tabla del catálogo. | `09b_busqueda_por_isbn.png` |
| **13** | Detalle completo de libro con conceptos | `GET` | `/books/978-0-000014-4` | `200 OK` | Apertura de modal con carátula, datos editoriales y conceptos asociados. | `10_detalle_de_un_libro_conceptos.png` |
| **14** | Consulta de libro inexistente por ISBN | `GET` | `/books/999-999-999` | `404 Not Found` | Manejo controlado de 404 informando que el recurso no fue localizado. | *(Manejado en catálogo/consola)* |
| **15** | Creación de libro individual (Matrícula) | `POST` | `/books` | `201 Created` | Creación exitosa de `PRUEBA INTEGRACION - 583928` mediante `sp_create_book`. | `11_creacion_libro_matricula_583928_POST.png` |
| **16** | Intento de creación con ISBN duplicado | `POST` | `/books` | `409 Conflict` | Detección de colisión de clave única y mensaje informativo de conflicto 409. | *(Manejado en consola HTTP)* |
| **17** | Modificación completa de libro (PUT) | `PUT` | `/books/978-0-000014-4` | `200 OK` | Reemplazo integral de todos los atributos del recurso editorial. | `12_modificacion_completa_PUT.png` |
| **18** | Modificación parcial de atributo (PATCH) | `PATCH` | `/books/978-0-000015-5` | `200 OK` | Diálogo PATCH enviando únicamente `{"stock": 20}` sin alterar demás columnas. | `13_modificacion_parcial_dialogo_PATCH.png` |
| **18b**| Éxito de modificación parcial (PATCH) | `PATCH` | `/books/978-0-000015-5` | `200 OK` | Confirmación 200 OK y registro en la consola HTTP en vivo de la GUI. | `13b_modificacion_parcial_exito_PATCH.png` |
| **19** | Eliminación de libro con confirmación (DELETE) | `DELETE` | `/books/{isbn}` | `200 OK` | Eliminación definitiva del recurso tras confirmación previa del usuario. | *(Confirmado en catálogo)* |
| **20** | Diagnóstico de salud de servicios en línea | `GET` | `/health` (ambos) | `200 OK` | Semáforos en 🟢 Verde indicando microservicios activos y PostgreSQL conectado. | `08_catalogo_de_libros_general.png` |
| **21** | Tolerancia a fallos: detención de servicio | `GET` | `/health` (books) | `Error (0) / 503` | Conmutación de semáforo a 🔴 Rojo sin crasheo ni cierre inesperado del programa. | `18_caso_b_books_detenido_rojo.png` |
| **22** | Tolerancia a fallos: restauración de servicio | `GET` | `/health` (books) | `200 OK` | Reconexión automática tras `systemctl start`, semáforo restaurado a 🟢 Verde. | `19_caso_c_books_recuperado_verde.png` |
| **23** | Diagnóstico de conectividad en configuración | `GET` | `/health` | `200 OK` | Comprobación y persistencia de URLs en `config.json` (Local vs GCP). | `20_pantalla_configuracion_servidor.png` |

---

## 📁 Ubicación de Archivos de Evidencia

Todas las capturas de pantalla referenciadas en esta bitácora se encuentran archivadas en alta resolución dentro del directorio local:
`apps/Python_app/evidencias_screenshots/`

