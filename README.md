# Plant Lens — Pipeline Completo de Datos con IA

**Curso:** Administración de Datos — LEAD University  
**Modelo:** Pl@ntNet API (identificación de plantas por imagen)  
**Base de datos:** MongoDB Atlas

---

## Arquitectura del pipeline

```
MongoDB Atlas
  └── identifications (raw)
         │
         ▼
      etl.py
   (Extract → Transform → Load)
         │
         ▼
  identifications_clean (curada)
         │
         ▼
      app.py (Flask API)
         │
         ▼
  index.html (Frontend)
         │
         ▼
  Pl@ntNet API (Modelo IA)
```

---

## Estructura de archivos

```
├── pipeline.py        ← Orquestador principal (corre todo en orden)
├── etl.py             ← ETL: extrae, transforma y carga datos
├── app.py             ← API Flask con todos los endpoints
├── index.html         ← Interfaz web (tabs: Identify / Stats / History)
├── style.css          ← Estilos botánicos
├── script.js          ← Lógica del frontend
└── README.md
```

---

## Instalación

```bash
pip install flask flask-cors pymongo requests
```

---

## Ejecución

### 1. Correr el pipeline completo (ETL + métricas + verificación)

```bash
python pipeline.py
```

Esto ejecuta 4 etapas en orden y genera logs con evidencia de cada paso.

### 2. Levantar la app Flask

```bash
python app.py
```

### 3. Abrir la interfaz

Abre `index.html` en tu navegador (o usa Live Server en VS Code).

---

## Endpoints de la API

| Método | Endpoint      | Descripción                                      |
|--------|---------------|--------------------------------------------------|
| POST   | /identify     | Identifica una planta con Pl@ntNet               |
| GET    | /stats        | Top 5 plantas desde colección curada (post-ETL)  |
| GET    | /history      | Últimas 20 identificaciones curadas              |
| POST   | /save-note    | Guarda nota del usuario en MongoDB               |
| GET    | /notes        | Obtiene notas guardadas                          |

---

## Colecciones en MongoDB

| Colección               | Descripción                          |
|-------------------------|--------------------------------------|
| `identifications`       | Datos crudos de cada identificación  |
| `identifications_clean` | Datos curados post-ETL               |
| `plant_notes`           | Notas escritas por el usuario        |

---

## Proceso ETL

El script `etl.py` realiza:

**Extracción:** Lee todos los documentos de `identifications`.

**Transformación:**
- Elimina duplicados por `_id`
- Limpia valores nulos y corrige tipos
- Normaliza nombres científicos
- Genera campos derivados:
  - `confidence_pct` — confianza en porcentaje
  - `confidence_tier` — clasificación: high / medium / low
  - `primary_common` — primer nombre común
  - `etl_processed_at` — timestamp del procesamiento

**Carga:** Inserta o actualiza documentos en `identifications_clean` usando upsert (idempotente, no duplica).

---

## Modelo de IA

- **Tipo:** API de clasificación visual (Pl@ntNet v2)
- **Input:** Imagen de planta (JPG/PNG/WEBP)
- **Output:** Nombre científico, familia, nombres comunes, score de confianza
- **Métrica de evaluación:** Confianza promedio del modelo sobre el dataset acumulado (visible en `pipeline.py` etapa 3 y en el tab Stats de la app)