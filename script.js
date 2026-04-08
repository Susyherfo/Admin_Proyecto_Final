const imageInput = document.getElementById("imageInput");
const previewImage = document.getElementById("previewImage");

imageInput.addEventListener("change", function() {
    const file = this.files[0];
    if (file) {
        previewImage.src = URL.createObjectURL(file);
    }
});

async function identifyPlant() {
    const file = imageInput.files[0];
    if (!file) return;

    document.getElementById("result").innerHTML = "Analizando...";

    const formData = new FormData();
    formData.append("image", file);

    const response = await fetch("http://127.0.0.1:5000/identify", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    const best = data.best;

    let html = `
        <h2>🌿 ${best.name}</h2>
        <p>Confianza: ${(best.score * 100).toFixed(2)}%</p>
        <p>Familia: ${best.family}</p>
        <hr>
        <h3>Otras coincidencias:</h3>
    `;

    data.results.slice(0, 3).forEach(r => {
        html += `
            <div style="margin-bottom:10px">
                <strong>${r.name}</strong><br>
                Confianza: ${(r.score * 100).toFixed(2)}%<br>
                Familia: ${r.family}
            </div>
        `;
    });

    document.getElementById("result").innerHTML = html;
}

function savePlant() {
    const name = document.getElementById("plantName").value;
    const description = document.getElementById("plantDescription").value;
    const care = document.getElementById("plantCare").value;

    const plant = {
        name,
        description,
        care
    };

    let plants = JSON.parse(localStorage.getItem("plants")) || [];
    plants.push(plant);

    localStorage.setItem("plants", JSON.stringify(plants));

    alert("Información guardada");
}

async function loadStats() {
    const response = await fetch("http://127.0.0.1:5000/stats");
    const data = await response.json();

    console.log(data);
}