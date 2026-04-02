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

    document.getElementById("result").innerHTML =
        `🌿 ${data.name} <br> Confianza: ${(data.score * 100).toFixed(2)}%`;
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

    alert("Información guardada 🌿");
}