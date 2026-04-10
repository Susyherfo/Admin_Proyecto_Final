"""
etl.py — Pipeline ETL para Plant Lens
--------------------------------------
Extrae datos crudos de la colección 'identifications',
los transforma y limpia, y los carga en 'identifications_clean'.
"""

import logging
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Conexión ─────────────────────────────────────────────────────────────────
MONGO_URI = (
    "mongodb+srv://elenaherfo_db_user:dhnRUXL98MGlkO8u"
    "@plant-lens-app.ju0hslr.mongodb.net/?retryWrites=true&w=majority"
)

client     = MongoClient(MONGO_URI)
db         = client["plant_lens"]
raw_col    = db["identifications"]          # fuente
clean_col  = db["identifications_clean"]    # destino curado


# ══════════════════════════════════════════════════════════════════════════════
# FASE 1 — EXTRACCIÓN
# ══════════════════════════════════════════════════════════════════════════════
def extract() -> list[dict]:
    log.info("── FASE 1: EXTRACCIÓN ──────────────────────────────────────")
    records = list(raw_col.find({}, {"_id": 1,
                                     "scientific_name": 1,
                                     "confidence": 1,
                                     "common_names": 1,
                                     "family": 1,
                                     "image_name": 1,
                                     "timestamp": 1}))
    log.info(f"  Documentos extraídos de 'identifications': {len(records)}")
    return records


# ══════════════════════════════════════════════════════════════════════════════
# FASE 2 — TRANSFORMACIÓN
# ══════════════════════════════════════════════════════════════════════════════
def _confidence_tier(score: float) -> str:
    if score >= 0.80:
        return "high"
    elif score >= 0.50:
        return "medium"
    return "low"


def _normalize_name(name: str) -> str:
    """Capitaliza correctamente el nombre científico."""
    if not name or name == "Unknown":
        return "Unknown"
    parts = name.strip().split()
    return " ".join(
        parts[0].capitalize() + ((" " + " ".join(p.lower() for p in parts[1:])) if len(parts) > 1 else "")
        for _ in [None]  # one-liner trick to use join result
    ).strip()


def transform(records: list[dict]) -> list[dict]:
    log.info("── FASE 2: TRANSFORMACIÓN ──────────────────────────────────")

    seen_ids   = set()
    cleaned    = []
    duplicates = 0
    nulls      = 0
    fixed      = 0

    for doc in records:
        raw_id = str(doc["_id"])

        # — Deduplicación por _id —
        if raw_id in seen_ids:
            duplicates += 1
            continue
        seen_ids.add(raw_id)

        # — Limpieza de nulos / tipos —
        name       = doc.get("scientific_name") or "Unknown"
        confidence = doc.get("confidence")
        family     = doc.get("family") or "Unknown"
        common     = doc.get("common_names") or []
        image      = doc.get("image_name") or "unknown_image"
        timestamp  = doc.get("timestamp") or datetime.utcnow()

        # Convertir confidence a float si llega como string
        try:
            confidence = float(confidence) if confidence is not None else 0.0
        except (ValueError, TypeError):
            confidence = 0.0
            nulls += 1

        # — Normalización —
        name_clean = _normalize_name(name)
        if name_clean != name:
            fixed += 1

        # — Feature engineering: campos derivados —
        clean_doc = {
            "source_id":        raw_id,
            "scientific_name":  name_clean,
            "family":           family.strip(),
            "common_names":     [c.strip() for c in common if isinstance(c, str)],
            "primary_common":   common[0].strip() if common else None,
            "confidence":       round(confidence, 4),
            "confidence_pct":   round(confidence * 100, 2),
            "confidence_tier":  _confidence_tier(confidence),
            "image_name":       image,
            "timestamp":        timestamp,
            "etl_processed_at": datetime.utcnow(),
        }
        cleaned.append(clean_doc)

    log.info(f"  Registros procesados : {len(records)}")
    log.info(f"  Duplicados removidos : {duplicates}")
    log.info(f"  Valores nulos/fijos  : {nulls}")
    log.info(f"  Nombres normalizados : {fixed}")
    log.info(f"  Registros limpios    : {len(cleaned)}")
    return cleaned


# ══════════════════════════════════════════════════════════════════════════════
# FASE 3 — CARGA
# ══════════════════════════════════════════════════════════════════════════════
def load(records: list[dict]) -> int:
    log.info("── FASE 3: CARGA ───────────────────────────────────────────")

    if not records:
        log.warning("  Sin registros para cargar.")
        return 0

    # Crear índice único para evitar re-inserciones
    clean_col.create_index([("source_id", ASCENDING)], unique=True)

    inserted = 0
    skipped  = 0

    for doc in records:
        try:
            clean_col.update_one(
                {"source_id": doc["source_id"]},
                {"$set": doc},
                upsert=True
            )
            inserted += 1
        except Exception as e:
            log.warning(f"  Documento omitido ({doc['source_id']}): {e}")
            skipped += 1

    log.info(f"  Documentos cargados en 'identifications_clean': {inserted}")
    log.info(f"  Documentos omitidos (ya existían): {skipped}")
    return inserted


# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════
def summary():
    total   = clean_col.count_documents({})
    high    = clean_col.count_documents({"confidence_tier": "high"})
    medium  = clean_col.count_documents({"confidence_tier": "medium"})
    low     = clean_col.count_documents({"confidence_tier": "low"})

    log.info("── RESUMEN DE COLECCIÓN CURADA ─────────────────────────────")
    log.info(f"  Total documentos    : {total}")
    log.info(f"  Confianza alta      : {high}")
    log.info(f"  Confianza media     : {medium}")
    log.info(f"  Confianza baja      : {low}")


# ══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
def run_etl():
    raw     = extract()
    clean   = transform(raw)
    loaded  = load(clean)
    summary()
    return loaded


if __name__ == "__main__":
    run_etl()