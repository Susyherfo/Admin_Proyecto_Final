from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = "Aqui va tu API key de PlantNet"

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

    return jsonify({
        "name": best["species"]["scientificNameWithoutAuthor"],
        "score": best["score"]
    })

if __name__ == "__main__":
    app.run(