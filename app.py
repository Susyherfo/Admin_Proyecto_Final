from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime


app = Flask(__name__)
CORS(app)
client = MongoClient("mongodb+srv://elenaherfo_db_user:<dhnRUXL98MGlkO8u>@plant-lens-app.ju0hslr.mongodb.net/?appName=Plant-Lens-App")
db = client["plant_lens"]
collection = db["identifications"]


API_KEY = "2b10R0dEY03ODrW4YUjHGGpyu" 

@app.route("/identify", methods=["POST"])
def identify():
    file = request.files["image"]

    url = f"https://my-api.plantnet.org/v2/identify/all?api-key={API_KEY}"

    files = {
        "images": file
    }

    data = {
        "organs": ["leaf"]
    }

    response = requests.post(url, files=files, data=data)
    result = response.json()

    best = result["results"][0]

    data = {
    "scientific_name": best["species"]["scientificNameWithoutAuthor"],
    "confidence": best["score"],
    "timestamp": datetime.now()
    }

    collection.insert_one(data)

    return jsonify({
        "name": best["species"]["scientificNameWithoutAuthor"],
        "score": best["score"]
    })

@app.route("/stats", methods=["GET"])
def stats():
    data = list(collection.find({}, {"_id": 0}))
    return jsonify(data)




if __name__ == "__main__":
    app.run()