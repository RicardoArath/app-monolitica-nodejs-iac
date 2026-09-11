# 📚 Librería en Línea – Aplicación de Escritorio (Electron)

Aplicación de escritorio para **Windows 11** construida con **Electron** que muestra el catálogo de libros de la librería en línea consumiendo **exclusivamente XML** provisto por el microservicio Flask.

## Características

- ✅ Consumo exclusivo de datos en formato **XML**
- ✅ Parseo de XML con `DOMParser` nativo
- ✅ Cards con imagen, autor(es), ISBN, stock, año, género y precio
- ✅ **Paginación** del lado del cliente (12 libros por página)
- ✅ Búsqueda/filtro por título, autor o ISBN
- ✅ **URL y endpoint configurables** con persistencia en `localStorage`
- ✅ Indicador de estado de conexión al microservicio
- ✅ Tema oscuro moderno adaptado a Windows 11

---

## Requisitos previos

1. **Node.js** v18 o superior instalado  
   Verificar con:
   ```bash
   node --version
   ```

2. **Microservicio XML** corriendo (Flask en el puerto 5001)  
   La URL por defecto apunta a: `http://34.51.99.221:5001/books`  
   Esto es configurable desde la aplicación.

---

## Pasos para ejecutar en Windows 11

### 1. Abrir terminal (PowerShell o CMD)

Presiona `Win + R`, escribe `powershell` y presiona Enter. O busca "Terminal" en el menú de inicio.

### 2. Navegar a la carpeta del proyecto

```bash
cd C:\Users\ricar\Downloads\libreria-online\libreria-electron
```

### 3. Instalar dependencias

```bash
npm install
```

> **Nota:** La primera vez descargará Electron (~200 MB). Esto puede tardar unos minutos dependiendo de tu conexión a Internet.

### 4. Ejecutar la aplicación

```bash
npm start
```

La ventana de la aplicación se abrirá mostrando el catálogo de libros.

---

## Configuración del microservicio

La aplicación permite configurar la URL y el endpoint del microservicio XML:

1. Haz clic en el botón de **engranaje** (⚙️) en la esquina superior derecha
2. Modifica los campos:
   - **URL Base**: `http://34.51.99.221:5001` (o tu IP local)
   - **Endpoint**: `/books`
3. Haz clic en **"Guardar y recargar"**

La configuración se guarda automáticamente en `localStorage` y persiste entre sesiones.

### Valores predeterminados

| Campo | Valor |
|-------|-------|
| URL Base | `http://34.51.99.221:5001` |
| Endpoint | `/books` |

---

## Estructura del proyecto

```
libreria-electron/
├── main.js               ← Proceso principal (ventana + fetch IPC)
├── preload.js             ← Puente seguro (contextBridge)
├── package.json           ← Dependencias y scripts
├── README.md              ← Este archivo
└── renderer/
    ├── index.html         ← Interfaz: header, cards, paginación, modal
    ├── styles.css          ← Tema oscuro moderno Windows 11
    └── app.js              ← Lógica: fetch XML, parseo, renderizado
```

---

## Tecnologías utilizadas

| Tecnología | Uso |
|------------|-----|
| **Electron** | Framework para aplicaciones de escritorio |
| **DOMParser** | Parseo nativo de XML en el navegador |
| **localStorage** | Persistencia de configuración |
| **IPC** (Inter-Process Communication) | Comunicación segura main ↔ renderer |
| **contextBridge** | Exposición segura de APIs al renderer |

---

## Formato XML esperado

La aplicación espera recibir XML con la siguiente estructura:

```xml
<library language="en">
  <book isbn="9780134092669">
    <title>Cloud Computing</title>
    <authors>
      <author>Thomas Erl</author>
    </authors>
    <year>2017</year>
    <genres>
      <genre>Cloud</genre>
    </genres>
    <price>1099.00</price>
    <stock>12</stock>
    <format>Hardcover</format>
    <images>
      <image uri="https://...jpg">Descripción</image>
    </images>
  </book>
</library>
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `npm start` no funciona | Verifica que `npm install` se completó sin errores |
| "Error de conexión" en la app | Verifica que el microservicio esté corriendo y la URL sea correcta (⚙️) |
| Imágenes no cargan | Verifica que las URLs de las imágenes en el XML sean accesibles |
| La app no abre | Ejecuta `npx electron .` directamente para ver errores en consola |

---

**Universidad de Monterrey** · Integración de Aplicaciones Computacionales · 2026

