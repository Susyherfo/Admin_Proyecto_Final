# Plant Lens - Identificador de Plantas con IA

Aplicación web que permite identificar plantas a partir de una imagen utilizando la API de Pl@ntNet.
Además, los usuarios pueden agregar información adicional sobre las plantas detectadas.

---

## Características

* Subir imagen de una planta
* Identificación automática usando IA (Pl@ntNet API)
* Visualización del nombre científico
* Porcentaje de confianza del modelo
* Formulario para agregar información de la planta
* Almacenamiento local de datos
* Interfaz con estilo botánico

---

## Estructura del Proyecto

```
plant-lens-app/
│
├── index.html
├── style.css
├── script.js
├── app.py
└── README.md
```

---

## Tecnologías utilizadas

* HTML5
* CSS3
* JavaScript
* Python
* Flask
* API Pl@ntNet

---

## Instalación

### 1. Clonar o descargar el proyecto

```
git clone <tu-repositorio>
cd plant-lens-app
```

### 2. Instalar dependencias

```
pip install flask requests flask-cors
```

### 3. Configurar API Key

En `app.py` reemplazar:

```
API_KEY = "TU_API_KEY_AQUI"
```

con tu API key de Pl@ntNet.

---

## Ejecución

### 1. Ejecutar backend

```
python app.py
```

Esto iniciará el servidor en:

```
http://127.0.0.1:5000
```

### 2. Abrir frontend

Abrir el archivo `index.html` en el navegador
o usar un servidor local:

```
python -m http.server 5500
```

---

## Flujo de la Aplicación

1. Usuario sube imagen
2. Frontend envía imagen al backend
3. Backend llama API Pl@ntNet
4. Se obtiene la especie
5. Se muestra resultado en pantalla
6. Usuario puede agregar información adicional

---

## Funcionalidades futuras

* Guardar plantas en base de datos
* Historial de identificaciones
* Subida de imágenes adicionales
* Sistema colaborativo
* Geolocalización de plantas
* Diseño tipo app móvil

---

## Autor

Proyecto desarrollado por Susana Herrera Fonseca & Yulissa Navarro
Bachillerato en Ingeniería en Ciencia de Datos

---

## Licencia

Este proyecto es para fines educativos.
