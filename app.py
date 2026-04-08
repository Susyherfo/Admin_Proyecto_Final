from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

client = MongoClient("mongodb+srv://elenaherfo_db_user:dhnRUXL98MGlkO8u@plant-lens-app.ju0hslr.mongodb.net/?retryWrites=true&w=majority")
db = client["plant_lens"]
collection = db["identifications"]

print("Mongo Atlas conectado")

API_KEY = "2b10R0dEY03ODrW4YUjHGGpyu"


@app.route("/identify", methods=["POST"])
def identify():
    if "image" not in request.files:
        return {"error": "No image provided"}, 400

    file = request.files["image"]

    url = f"https://my-api.plantnet.org/v2/identify/all?api-key={API_KEY}"

    files = {
        "images": file
    }

    data = {
        "organs": "leaf"
    }

    print("Enviando imagen a API...")
    response = requests.post(url, files=files, data=data)

    print("Respuesta recibida:", response.status_code)
    result = response.json()
    print(result)

    if "results" not in result or len(result["results"]) == 0:
        return {"error": "No se pudo identificar la planta"}, 400

    results = result["results"][:3]
    top_results = []

    for r in results:
        species = r.get("species", {})

        top_results.append({
            "name": species.get("scientificNameWithoutAuthor", "Unknown"),
            "score": r.get("score", 0),
            "common": species.get("commonNames", []),
            "family": species.get("family", {}).get("scientificName", "Unknown")
        })

    best = top_results[0]

    mongo_data = {
        "scientific_name": best["name"],
        "confidence": best["score"],
        "common_names": best["common"],
        "family": best["family"],
        "image_name": file.filename,
        "timestamp": datetime.now()
    }

    collection.insert_one(mongo_data)

    return jsonify({
        "best": best,
        "results": top_results
    })


@app.route("/stats", methods=["GET"])
def stats():
    pipeline = [
        {
            "$group": {
                "_id": "$scientific_name",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence"}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]

    results = list(collection.aggregate(pipeline))

    for r in results:
        r["plant"] = r["_id"]
        del r["_id"]

    return jsonify(results)


@app.route("/history", methods=["GET"])
def history():
    data = list(
        collection.find({}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(20)
    )
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)