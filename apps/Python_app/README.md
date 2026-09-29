# 📚 Librería en Línea — Cliente de Escritorio en Python

Aplicación gráfica de escritorio desarrollada en Python que funciona como cliente independiente para la plataforma de librería en línea, interactuando de forma exclusiva mediante **HTTP**, endpoints **REST**, **JSON**, sesiones, cookies y códigos de respuesta HTTP estándar con los microservicios de **Autenticación** (`services/login` en el puerto `5000`) y **Gestión de Libros** (`services/books` en el puerto `5001`).

---

## 📋 Especificaciones del Entorno

* **Versión de Python:** Python 3.10 o superior (compatible con Python 3.11, 3.12 y 3.14).
* **Biblioteca Gráfica (GUI):** `Tkinter` con widgets temáticos `ttk` y temas modernos (`clam`/`vista`), incluida de forma nativa en la distribución estándar de Python en Windows.
* **Bibliotecas de Terceros:**
  * `requests` (v2.31+): Manejo de comunicaciones HTTP/REST, sesiones persistentes y gestión automática de cookies de Flask.
  * `Pillow` (v10.0+): Procesamiento y renderizado de imágenes de carátulas en la GUI.

---

## 🛠️ Instalación y Preparación

### 1. Clonar o descargar el repositorio
Navegar al directorio de la aplicación:
```bash
cd apps/Python_app
```

### 2. Crear y activar entorno virtual (Recomendado)
En PowerShell (Windows):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

En Command Prompt (CMD):
```cmd
python -m venv venv
.\venv\Scripts\activate.bat
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración de los Microservicios

La aplicación permite conectarse de forma transparente tanto a los microservicios ejecutándose localmente como a la infraestructura desplegada en Google Cloud Platform (GCP).

### Direcciones Predeterminadas
* **Modo Remoto (Nube GCP):**
  * Microservicio de Login: `http://35.193.230.144:5000`
  * Microservicio de Libros: `http://35.193.230.144:5001`
* **Modo Local:**
  * Microservicio de Login: `http://localhost:5000`
  * Microservicio de Libros: `http://localhost:5001`

### Cambio de Entorno sin Modificar Código Fuente
Dentro de la aplicación, en la pestaña **⚙️ Configuración del Servidor**:
1. Utilice los botones de selección rápida: **"Modo Remoto (GCP)"** o **"Modo Local"**.
2. O bien, ingrese manualmente cualquier dirección IP y puerto deseado.
3. Presione **"Probar Conexión"** para verificar la disponibilidad de los servicios en tiempo real.
4. Presione **"Guardar y Aplicar Configuración"**: Los valores se almacenarán en `config/config.json` y persistirán automáticamente al cerrar y volver a abrir el programa.

---

## 🚀 Ejecución de la Aplicación

Con el entorno virtual activo, ejecute:
```bash
python main.py
```

---

## 📂 Estructura del Código Fuente

```text
apps/Python_app/
├── config/
│   ├── __init__.py
│   ├── config.json          # Archivo de persistencia de URLs del servidor
│   └── settings.py          # Clase Settings con presets local/remoto y persistencia
├── network/
│   ├── __init__.py
│   ├── api_client.py        # Cliente HTTP con requests.Session, timeout y tolerancia a fallos
│   ├── auth_service.py      # Mapeo de endpoints del microservicio de autenticación (:5000)
│   └── books_service.py     # Mapeo de endpoints del microservicio de libros (:5001)
├── session/
│   ├── __init__.py
│   ├── session.json         # Almacenamiento local seguro de sesión y cookies
│   └── session_manager.py   # Validación de sesión en arranque (GET /session) y persistencia
├── ui/
│   ├── __init__.py
│   ├── auth_window.py       # Ventana de Login y Registro con CAPTCHA matemático
│   ├── main_window.py       # Panel Principal con pestañas ttk.Notebook y header
│   ├── tabs/
│   │   ├── catalog_tab.py   # Catálogo con filtros avanzados (ISBN, título, año, precios)
│   │   ├── book_detail_dialog.py # Detalle modal con carátula y conceptos asociados
│   │   ├── admin_books_tab.py # CRUD completo: POST, PUT, PATCH, DELETE y consola HTTP
│   │   ├── profile_tab.py   # Perfil de usuario (PATCH /profile) y extensión de sesión
│   │   ├── health_tab.py    # Semáforo de 3 estados (🟢🟡🔴) con polling y timestamps
│   │   └── settings_tab.py  # Configuración interactiva de URLs y presets
│   └── widgets/
│       ├── __init__.py
│       └── status_badge.py  # Widget de semáforo con Canvas de 3 estados de color
├── main.py                  # Punto de entrada de la aplicación
├── requirements.txt         # Lista de dependencias del proyecto
└── README.md                # Este documento de arquitectura y operación
```

---

## 🌐 Endpoints REST Consumidos

### Microservicio de Autenticación (`services/login` — Puerto 5000)
| Método | Endpoint | Función en la Aplicación |
| :--- | :--- | :--- |
| `POST` | `/register` | Registrar un nuevo usuario con verificación CAPTCHA. |
| `GET` | `/verify` | Verificar correo electrónico mediante token. |
| `POST` | `/login` | Autenticar credenciales y generar cookie de sesión HTTP. |
| `POST` | `/logout` | Cerrar sesión y destruir el estado en el servidor. |
| `GET` | `/session` | Validar vigencia de sesión y detectar expiración por inactividad. |
| `POST` | `/session/extend` | Extender el tiempo de vida de la sesión activa (30 min adicionales). |
| `PATCH`| `/profile` | Modificar parcialmente datos del usuario (nombre, apellidos, email, password). |
| `GET` | `/health` | Diagnosticar estado operativo y conectividad a PostgreSQL. |

### Microservicio de Libros (`services/books` — Puerto 5001)
| Método | Endpoint | Función en la Aplicación |
| :--- | :--- | :--- |
| `GET` | `/books` | Listar catálogo con filtros (`title`, `isbn`, `year`, `min_price`, `max_price`). |
| `GET` | `/books/{isbn}` | Consultar detalle completo, carátula y conceptos de un libro por ISBN. |
| `POST` | `/books` | Registrar un nuevo libro en la base de datos. |
| `PUT` | `/books/{isbn}` | Actualización completa (sobrescribe todos los atributos). |
| `PATCH`| `/books/{isbn}` | Actualización parcial (modifica únicamente el atributo seleccionado). |
| `DELETE`| `/books/{isbn}` | Eliminar permanentemente un libro por su ISBN con confirmación previa. |
| `GET` | `/health` | Monitoreo del estado de salud del servicio y su base de datos. |
| `GET` | `/authors`, `/genres`, etc. | Obtención de catálogos auxiliares para formularios. |

---

## 🚦 Semáforo de Estado de Microservicios

La aplicación implementa un semáforo visual que distingue al menos 3 estados operacionales:
* 🟢 **Verde (En Línea):** El microservicio responde HTTP 200 y reporta conexión exitosa a PostgreSQL (`database: connected`).
* 🟡 **Amarillo (Degradado):** El microservicio responde, pero la base de datos está desconectada o inaccesible (`database: disconnected`).
* 🔴 **Rojo (Fuera de Línea):** El servicio no responde, el puerto está cerrado o se presenta un error de red (`Connection Refused`, `Timeout`).

La pestaña **🚦 Estado de los Servicios** cuenta con:
* Fecha y hora exacta de la última comprobación.
* Botón **"Comprobar Ahora"** para refresco manual instantáneo.
* Hilo en segundo plano que actualiza el estado cada 30 segundos sin congelar la interfaz gráfica.

---

## 🔄 Diferencia Técnica entre PUT y PATCH

La pestaña **🛠️ Administración de Libros** demuestra en la práctica la diferencia entre ambos métodos HTTP:
* **`PUT /books/{isbn}` (Actualización Completa):** Reemplaza íntegramente la representación del recurso en el servidor. El cliente envía la totalidad de los atributos del libro (`title`, `year`, `price`, `stock`, `format_id`, `category_id`, `description`, etc.).
* **`PATCH /books/{isbn}` (Actualización Parcial):** Modifica únicamente uno o varios atributos específicos (por ejemplo, solamente el `price` o el `stock`), dejando inalterados todos los demás campos del recurso en el servidor. El payload JSON contiene únicamente las llaves que se desean alterar.

---

## 🛡️ Tolerancia a Fallos y Manejo de Errores

La aplicación implementa aislamiento por hilos (`threading.Thread`) y timeouts estrictos en todas las llamadas de red:
* **Caída de servicio:** Si el microservicio de libros se detiene durante la ejecución, el catálogo informa amigablemente la situación al usuario mediante un diálogo informativo, sin que la aplicación se congele o se cierre inesperadamente.
* **Credenciales inválidas (401):** Presenta un mensaje de advertencia claro al usuario en lugar de un error genérico.
* **Conflicto de ISBN (409):** Detecta duplicados y notifica que el ISBN ya pertenece a otro libro.
* **Recurso no encontrado (404):** Manejo controlado ante consultas o eliminaciones de ISBNs inexistentes.

---

## ❓ Solución de Problemas Frecuentes

1. **Error `Connection Refused` o semáforo en 🔴 Rojo:**
   * Verifique en la pestaña de configuración si está en modo Local o Remoto.
   * Si está en modo Local, confirme que los servicios en los puertos 5000 y 5001 estén en ejecución.
   * Si está en modo Remoto (GCP), verifique que la máquina virtual esté encendida y que la IP pública corresponda a la asignada por GCP.
2. **Error de autenticación `403` al iniciar sesión:**
   * La cuenta fue registrada pero su correo aún no ha sido confirmado. En el entorno de pruebas, asegúrese de verificar el correo o activar la bandera en la base de datos.
3. **Imágenes de carátula no aparecen:**
   * Si el libro no tiene carátula en el servidor, la aplicación muestra automáticamente un indicador visual limpio (`📖 Sin Imagen`) sin provocar fallos de ejecución.
