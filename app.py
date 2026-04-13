"""
app.py — Plant Lens Flask API
------------------------------
Endpoints:
  POST /identify      — Identifica una planta con Pl@ntNet y guarda en raw
                        Si Pl@ntNet no reconoce la imagen, busca en manual_plants
  GET  /stats         — Top 5 plantas desde colección CURADA (post-ETL)
  GET  /history       — Últimas 20 identificaciones desde colección CURADA
  POST /save-note     — Guarda nota del usuario en MongoDB
  POST /manual-plant  — Registra manualmente una planta no reconocida
  GET  /manual-plants — Lista todas las plantas ingresadas manualmente
"""

from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ─── Conexión ─────────────────────────────────────────────────────────────────
MONGO_URI = (
    "mongodb+srv://Usuario:Contraseña" # Reemplaza con Usuario y Contraseña reales
    "@plant-lens-app.ju0hslr.mongodb.net/?retryWrites=true&w=majority"
)
client     = MongoClient(MONGO_URI)
db         = client["plant_lens"]
raw_col      = db["identifications"]          # datos crudos
clean_col    = db["identifications_clean"]    # datos curados (post-ETL)
notes_col    = db["plant_notes"]              # notas del usuario
manual_col   = db["manual_plants"]            # plantas ingresadas manualmente

print("[OK] Mongo Atlas conectado")

API_KEY = "Your-PlantNet-API-Key-Here"  # Reemplaza con tu clave real de Pl@ntNet


# ══════════════════════════════════════════════════════════════════════════════
# POST /identify
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/identify", methods=["POST"])
def identify():
    if "image" not in request.files:
        return {"error": "No image provided"}, 400

    file = request.files["image"]

    url = f"https://my-api.plantnet.org/v2/identify/all?api-key={API_KEY}"

    print(f"[identify] Enviando imagen '{file.filename}' a Pl@ntNet...")
    response = requests.post(url, files={"images": file}, data={"organs": "leaf"})
    print(f"[identify] Respuesta: {response.status_code}")

    result = response.json()

    if "results" not in result or len(result["results"]) == 0:
        # ── Buscar en plantas ingresadas manualmente ──────────────────────────
        manual = manual_col.find_one(
            {},
            {"_id": 0},
            sort=[("added_at", -1)]   # placeholder: en producción filtrarías por hash de imagen
        )
        return jsonify({
            "error":        "not_recognized",
            "message":      "Pl@ntNet no pudo identificar esta planta.",
            "has_manual":   manual_col.count_documents({}) > 0
        }), 404

    top_results = []
    for r in result["results"][:3]:
        species = r.get("species", {})
        top_results.append({
            "name":   species.get("scientificNameWithoutAuthor", "Unknown"),
            "score":  r.get("score", 0),
            "common": species.get("commonNames", []),
            "family": species.get("family", {}).get("scientificName", "Unknown")
        })

    best = top_results[0]

    # Guardar en colección RAW
    raw_col.insert_one({
        "scientific_name": best["name"],
        "confidence":      best["score"],
        "common_names":    best["common"],
        "family":          best["family"],
        "image_name":      file.filename,
        "timestamp":       datetime.utcnow()
    })

    print(f"[identify] Guardado: {best['name']} ({round(best['score']*100,1)}%)")

    return jsonify({"best": best, "results": top_results})


# ══════════════════════════════════════════════════════════════════════════════
# GET /stats  — desde colección CURADA
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/stats", methods=["GET"])
def stats():
    pipeline = [
        {
            "$group": {
                "_id":          "$scientific_name",
                "count":        {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence"},
                "family":       {"$first": "$family"}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]

    results = list(clean_col.aggregate(pipeline))

    output = []
    for r in results:
        output.append({
            "plant":          r["_id"],
            "count":          r["count"],
            "avg_confidence": round(r["avg_confidence"] * 100, 1),
            "family":         r.get("family", "Unknown")
        })

    return jsonify(output)


# ══════════════════════════════════════════════════════════════════════════════
# GET /history  — desde colección CURADA
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/history", methods=["GET"])
def history():
    data = list(
        clean_col.find({}, {"_id": 0, "source_id": 0, "etl_processed_at": 0})
        .sort("timestamp", -1)
        .limit(20)
    )

    # Serializar datetime a string
    for doc in data:
        if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
            doc["timestamp"] = doc["timestamp"].isoformat()

    return jsonify(data)


# ══════════════════════════════════════════════════════════════════════════════
# POST /save-note  — reemplaza localStorage del frontend
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/save-note", methods=["POST"])
def save_note():
    body = request.get_json()
    if not body:
        return {"error": "No data provided"}, 400

    note = {
        "plant_name":  body.get("name", ""),
        "description": body.get("description", ""),
        "care":        body.get("care", ""),
        "saved_at":    datetime.utcnow()
    }

    notes_col.insert_one(note)
    print(f"[save-note] Nota guardada para: {note['plant_name']}")
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# GET /notes
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/notes", methods=["GET"])
def get_notes():
    data = list(
        notes_col.find({}, {"_id": 0})
        .sort("saved_at", -1)
        .limit(20)
    )
    for doc in data:
        if "saved_at" in doc and hasattr(doc["saved_at"], "isoformat"):
            doc["saved_at"] = doc["saved_at"].isoformat()
    return jsonify(data)




# ══════════════════════════════════════════════════════════════════════════════
# POST /manual-plant  — Registrar planta no reconocida manualmente
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/manual-plant", methods=["POST"])
def manual_plant():
    body = request.get_json()
    if not body:
        return {"error": "No data provided"}, 400

    scientific_name = body.get("scientific_name", "").strip()
    if not scientific_name:
        return {"error": "scientific_name is required"}, 400

    # Evitar duplicados por nombre científico
    existing = manual_col.find_one(
        {"scientific_name": {"$regex": f"^{scientific_name}$", "$options": "i"}}
    )
    if existing:
        return jsonify({"ok": True, "duplicate": True,
                        "message": f"'{scientific_name}' ya existe en la base de datos."}), 200

    doc = {
        "scientific_name": scientific_name,
        "common_names":    [n.strip() for n in body.get("common_names", []) if n.strip()],
        "family":          body.get("family", "").strip() or "Unknown",
        "description":     body.get("description", "").strip(),
        "habitat":         body.get("habitat", "").strip(),
        "added_by":        "user",
        "source":          "manual",
        "confidence":      1.0,        # entrada manual = confianza total del usuario
        "added_at":        datetime.utcnow()
    }

    manual_col.insert_one(doc)

    # También insertar en raw para que el ETL lo procese
    raw_col.insert_one({
        "scientific_name": doc["scientific_name"],
        "confidence":      doc["confidence"],
        "common_names":    doc["common_names"],
        "family":          doc["family"],
        "image_name":      "manual_entry",
        "source":          "manual",
        "timestamp":       datetime.utcnow()
    })

    print(f"[manual-plant] Nueva planta registrada: {scientific_name}")
    return jsonify({"ok": True, "duplicate": False,
                    "message": f"'{scientific_name}' guardada exitosamente."}), 201


# ══════════════════════════════════════════════════════════════════════════════
# GET /manual-plants  — Listar plantas ingresadas manualmente
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/manual-plants", methods=["GET"])
def get_manual_plants():
    data = list(
        manual_col.find({}, {"_id": 0})
        .sort("added_at", -1)
        .limit(50)
    )
    for doc in data:
        if "added_at" in doc and hasattr(doc["added_at"], "isoformat"):
            doc["added_at"] = doc["added_at"].isoformat()
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)