"""
pipeline.py — Orquestador principal de Plant Lens
---------------------------------------------------
Ejecuta el pipeline completo en orden:
 
  ETAPA 1  Verificar conexión a MongoDB
  ETAPA 2  Correr ETL (extract → transform → load)
  ETAPA 3  Evaluar modelo (métricas sobre colección curada)
  ETAPA 4  Verificar que la app Flask está lista
 
Cada etapa imprime logs con timestamp. El pipeline puede
repetirse de forma idempotente (no duplica datos).
"""
 
import sys
import time
import logging
from datetime import datetime
 
# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("pipeline")
 
SEPARATOR = "=" * 60
 
 
def section(title: str):
    log.info(SEPARATOR)
    log.info(f"  {title}")
    log.info(SEPARATOR)
 
 
def step_ok(msg: str):
    log.info(f"  [OK]  {msg}")
 
 
def step_fail(msg: str):
    log.error(f"  [FAIL]  {msg}")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 1 — VERIFICAR CONEXIÓN A MONGODB
# ══════════════════════════════════════════════════════════════════════════════
def stage_1_check_db() -> bool:
    section("ETAPA 1 — Verificar conexión a MongoDB Atlas")
    try:
        from pymongo import MongoClient
        MONGO_URI = (
            "mongodb+srv://elenaherfo_db_user:dhnRUXL98MGlkO8u"
            "@plant-lens-app.ju0hslr.mongodb.net/?retryWrites=true&w=majority"
        )
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=6000)
        client.admin.command("ping")
        db = client["plant_lens"]
 
        raw_count   = db["identifications"].count_documents({})
        clean_count = db["identifications_clean"].count_documents({})
 
        step_ok("Conexión a MongoDB Atlas exitosa")
        step_ok(f"Colección 'identifications'       : {raw_count} documentos")
        step_ok(f"Colección 'identifications_clean' : {clean_count} documentos")
        return True
 
    except Exception as e:
        step_fail(f"No se pudo conectar a MongoDB: {e}")
        return False
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 2 — ETL
# ══════════════════════════════════════════════════════════════════════════════
def stage_2_etl() -> bool:
    section("ETAPA 2 — Pipeline ETL (Extract → Transform → Load)")
    try:
        from etl import run_etl
        loaded = run_etl()
        step_ok(f"ETL completado. Documentos en colección curada: {loaded}")
        return True
    except Exception as e:
        step_fail(f"Error en ETL: {e}")
        return False
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 3 — EVALUACIÓN DEL MODELO
# ══════════════════════════════════════════════════════════════════════════════
def stage_3_evaluate_model() -> bool:
    section("ETAPA 3 — Evaluación del modelo de IA (Pl@ntNet)")
    try:
        from pymongo import MongoClient
        MONGO_URI = (
            "mongodb+srv://elenaherfo_db_user:dhnRUXL98MGlkO8u"
            "@plant-lens-app.ju0hslr.mongodb.net/?retryWrites=true&w=majority"
        )
        client     = MongoClient(MONGO_URI)
        clean_col  = client["plant_lens"]["identifications_clean"]
 
        total = clean_col.count_documents({})
 
        if total == 0:
            log.warning("  Sin datos en colección curada. Omitiendo métricas.")
            return True
 
        # — Métricas de confianza —
        pipeline_avg = [{"$group": {"_id": None, "avg": {"$avg": "$confidence"}}}]
        avg_result   = list(clean_col.aggregate(pipeline_avg))
        avg_conf     = avg_result[0]["avg"] if avg_result else 0
 
        high   = clean_col.count_documents({"confidence_tier": "high"})
        medium = clean_col.count_documents({"confidence_tier": "medium"})
        low    = clean_col.count_documents({"confidence_tier": "low"})
 
        high_pct   = round(high / total * 100, 1)
        medium_pct = round(medium / total * 100, 1)
        low_pct    = round(low / total * 100, 1)
 
        # — Top 5 plantas más identificadas —
        top_pipeline = [
            {"$group": {"_id": "$scientific_name", "count": {"$sum": 1},
                        "avg_conf": {"$avg": "$confidence"}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        top_plants = list(clean_col.aggregate(top_pipeline))
 
        step_ok(f"Total identificaciones procesadas : {total}")
        step_ok(f"Confianza promedio del modelo     : {round(avg_conf * 100, 2)}%")
        step_ok(f"Distribución de confianza:")
        log.info(f"      Alta   (>=80%) : {high:>4} registros  ({high_pct}%)")
        log.info(f"      Media  (50-79%): {medium:>4} registros  ({medium_pct}%)")
        log.info(f"      Baja   (<50%)  : {low:>4} registros  ({low_pct}%)")
        step_ok("Top 5 plantas identificadas:")
        for i, p in enumerate(top_plants, 1):
            log.info(
                f"      {i}. {p['_id']:<35} "
                f"count={p['count']}  avg_conf={round(p['avg_conf']*100,1)}%"
            )
 
        return True
 
    except Exception as e:
        step_fail(f"Error en evaluación: {e}")
        return False
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 4 — VERIFICAR APP FLASK
# ══════════════════════════════════════════════════════════════════════════════
def stage_4_check_app() -> bool:
    section("ETAPA 4 — Verificar disponibilidad de la app Flask")
    try:
        import requests
        r = requests.get("http://127.0.0.1:5000/history", timeout=3)
        if r.status_code == 200:
            step_ok("App Flask respondiendo en http://127.0.0.1:5000")
            step_ok(f"Endpoint /history devolvió {len(r.json())} registros")
            return True
        else:
            log.warning(f"  App respondió con status {r.status_code}")
            return False
    except Exception:
        log.warning("  App Flask no está corriendo (levántala con: python app.py)")
        log.warning("  Esto no detiene el pipeline — el ETL ya fue ejecutado.")
        return True  # No es un error crítico del pipeline
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ORQUESTADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def main():
    start = time.time()
 
    log.info("")
    log.info(SEPARATOR)
    log.info("  PLANT LENS — PIPELINE COMPLETO DE DATOS")
    log.info(f"  Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(SEPARATOR)
    log.info("")
 
    stages = [
        ("Conexión DB",     stage_1_check_db),
        ("ETL",             stage_2_etl),
        ("Evaluación IA",   stage_3_evaluate_model),
        ("Verificar App",   stage_4_check_app),
    ]
 
    results = {}
 
    for name, fn in stages:
        ok = fn()
        results[name] = ok
        log.info("")
        if not ok and name in ("Conexión DB", "ETL"):
            step_fail(f"Etapa crítica '{name}' falló. Abortando pipeline.")
            sys.exit(1)
 
    # — Resumen final —
    elapsed = round(time.time() - start, 2)
    section("RESUMEN DEL PIPELINE")
    for name, ok in results.items():
        status = "OK  " if ok else "FAIL"
        log.info(f"  [{status}]  {name}")
    log.info(f"\n  Tiempo total de ejecución: {elapsed}s")
    log.info(SEPARATOR)
    log.info("")
 
    all_ok = all(results.values())
    if all_ok:
        log.info("  Pipeline completado exitosamente.")
    else:
        log.warning("  Pipeline completado con advertencias.")
 
    return 0 if all_ok else 1
 
 
if __name__ == "__main__":
    sys.exit(main())
 