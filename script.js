const BASE_URL = "http://127.0.0.1:5000";

// ── Preview ───────────────────────────────────────────────────────────────────
const imageInput   = document.getElementById("imageInput");
const previewImage = document.getElementById("previewImage");

imageInput.addEventListener("change", function () {
  const file = this.files[0];
  if (file) {
    previewImage.src = URL.createObjectURL(file);
    previewImage.classList.add("visible");
    document.getElementById("uploadPlaceholder").style.display = "none";
    document.getElementById("uploadZone").classList.add("has-image");
  }
});

// ── Identificar planta ────────────────────────────────────────────────────────
async function identifyPlant() {
  const file = imageInput.files[0];
  if (!file) return;

  const btn = document.getElementById("identifyBtn");
  btn.classList.add("loading");
  btn.innerHTML = '<div class="spinner"></div> Analyzing...';

  // Ocultar cards previas
  document.getElementById("unrecognizedCard").style.display = "none";
  document.getElementById("manualFormCard").style.display  = "none";
  document.getElementById("resultsCard").classList.remove("visible");

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch(`${BASE_URL}/identify`, {
      method: "POST",
      body: formData,
    });

    if (response.status === 404) {
      // Pl@ntNet no reconoció la planta
      showUnrecognized();
    } else {
      const data = await response.json();
      renderResults(data);
    }
  } catch (err) {
    renderResults(null, true);
  }

  btn.classList.remove("loading");
  btn.innerHTML = `
    <svg viewBox="0 0 24 24" style="width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
    Identify again`;
}

// ── Renderizar resultados ─────────────────────────────────────────────────────
function renderResults(data, error = false) {
  const card = document.getElementById("resultsCard");
  card.classList.add("visible");

  if (error || !data) {
    document.getElementById("plantName").textContent = "Could not identify";
    document.getElementById("plantFamily").textContent = "Try a clearer photo";
    document.getElementById("confidenceLabel").textContent = "No match";
    document.getElementById("barFill").style.width = "0%";
    document.getElementById("altList").innerHTML = "";
    document.getElementById("commonNamesWrap").style.display = "none";

    // Ocultar formulario de notas
    const noteCard = document.getElementById("noteCard");
    if (noteCard) noteCard.style.display = "none";
    return;
  }

  const best = data.best;
  const pct  = (best.score * 100).toFixed(1);

  document.getElementById("confidenceLabel").textContent = `${pct}% match`;
  document.getElementById("plantName").textContent = best.name;
  document.getElementById("plantFamily").textContent = best.family;

  setTimeout(() => {
    document.getElementById("barFill").style.width = `${pct}%`;
  }, 80);

  const commonWrap = document.getElementById("commonNamesWrap");
  const commonEl   = document.getElementById("commonNames");
  if (best.common && best.common.length > 0) {
    commonEl.innerHTML = best.common.slice(0, 4)
      .map((n) => `<span class="name-tag">${n}</span>`)
      .join("");
    commonWrap.style.display = "block";
  } else {
    commonWrap.style.display = "none";
  }

  const altList = document.getElementById("altList");
  altList.innerHTML = data.results.slice(1, 3).map((r) => `
    <div class="alt-item">
      <span class="alt-name">${r.name}</span>
      <span class="alt-score">${(r.score * 100).toFixed(1)}%</span>
    </div>
  `).join("");

  // Pre-llenar el nombre en el formulario de notas
  const nameInput = document.getElementById("plantNameInput");
  if (nameInput) nameInput.value = best.name;

  const noteCard = document.getElementById("noteCard");
  if (noteCard) noteCard.style.display = "block";

  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ── Guardar nota (ahora en MongoDB, no localStorage) ─────────────────────────
async function savePlant() {
  const name        = document.getElementById("plantNameInput")?.value || "";
  const description = document.getElementById("plantDescription")?.value || "";
  const care        = document.getElementById("plantCare")?.value || "";

  if (!name) {
    alert("El nombre de la planta es requerido.");
    return;
  }

  try {
    const response = await fetch(`${BASE_URL}/save-note`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description, care }),
    });

    const result = await response.json();
    if (result.ok) {
      alert("Nota guardada correctamente.");
      document.getElementById("plantDescription").value = "";
      document.getElementById("plantCare").value = "";
    }
  } catch (err) {
    alert("Error al guardar. Verifica que el servidor Flask esté corriendo.");
  }
}

// ── Cargar estadísticas ───────────────────────────────────────────────────────
async function loadStats() {
  const container = document.getElementById("statsContainer");
  if (!container) return;

  try {
    const response = await fetch(`${BASE_URL}/stats`);
    const data     = await response.json();

    if (!data || data.length === 0) {
      container.innerHTML = `<p class="empty-msg">No hay estadísticas aún. Identifica algunas plantas primero.</p>`;
      return;
    }

    container.innerHTML = data.map((item, i) => `
      <div class="stat-item">
        <div class="stat-rank">${i + 1}</div>
        <div class="stat-info">
          <span class="stat-name">${item.plant}</span>
          <span class="stat-family">${item.family}</span>
        </div>
        <div class="stat-meta">
          <span class="stat-count">${item.count}x</span>
          <span class="stat-conf">${item.avg_confidence}% avg</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<p class="empty-msg">No se pudo conectar al servidor.</p>`;
  }
}

// ── Cargar historial ──────────────────────────────────────────────────────────
async function loadHistory() {
  const container = document.getElementById("historyContainer");
  if (!container) return;

  try {
    const response = await fetch(`${BASE_URL}/history`);
    const data     = await response.json();

    if (!data || data.length === 0) {
      container.innerHTML = `<p class="empty-msg">Sin historial aún.</p>`;
      return;
    }

    container.innerHTML = data.map((item) => {
      const date = item.timestamp
        ? new Date(item.timestamp).toLocaleDateString("es-CR", {
            day: "2-digit", month: "short", year: "numeric"
          })
        : "—";
      const tier = item.confidence_tier || "—";
      return `
        <div class="history-item">
          <div class="history-info">
            <span class="history-name">${item.scientific_name}</span>
            <span class="history-family">${item.family || "—"}</span>
          </div>
          <div class="history-meta">
            <span class="tier-badge tier-${tier}">${tier}</span>
            <span class="history-date">${date}</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<p class="empty-msg">No se pudo conectar al servidor.</p>`;
  }
}

// ── Planta no reconocida ──────────────────────────────────────────────────────
function showUnrecognized() {
  document.getElementById("unrecognizedCard").style.display = "flex";
  document.getElementById("unrecognizedCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function showManualForm() {
  document.getElementById("unrecognizedCard").style.display = "none";
  document.getElementById("manualFormCard").style.display   = "block";
  document.getElementById("manualFormCard").scrollIntoView({ behavior: "smooth", block: "nearest" });
  document.getElementById("manualFeedback").style.display   = "none";
}

function hideManualForm() {
  document.getElementById("manualFormCard").style.display   = "none";
  document.getElementById("unrecognizedCard").style.display = "flex";
}

async function submitManualPlant() {
  const scientific = document.getElementById("manualScientific").value.trim();
  if (!scientific) {
    showManualFeedback("Scientific name is required.", "error");
    return;
  }

  const rawCommon = document.getElementById("manualCommon").value;
  const commonArr = rawCommon
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const payload = {
    scientific_name: scientific,
    common_names:    commonArr,
    family:          document.getElementById("manualFamily").value.trim(),
    description:     document.getElementById("manualDescription").value.trim(),
    habitat:         document.getElementById("manualHabitat").value.trim(),
  };

  try {
    const response = await fetch(`${BASE_URL}/manual-plant`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });

    const result = await response.json();

    if (result.duplicate) {
      showManualFeedback(`'${scientific}' already exists in the database.`, "warning");
      return;
    }

    if (result.ok) {
      showManualFeedback(result.message, "success");
      // Limpiar campos
      ["manualScientific","manualCommon","manualFamily","manualDescription","manualHabitat"]
        .forEach((id) => { document.getElementById(id).value = ""; });
    }
  } catch (err) {
    showManualFeedback("Could not connect to the server.", "error");
  }
}

function showManualFeedback(msg, type) {
  const el = document.getElementById("manualFeedback");
  el.textContent  = msg;
  el.className    = `manual-feedback feedback-${type}`;
  el.style.display = "block";
}

// ── Cargar plantas manuales ───────────────────────────────────────────────────
async function loadManualPlants() {
  const container = document.getElementById("manualContainer");
  if (!container) return;

  try {
    const response = await fetch(`${BASE_URL}/manual-plants`);
    const data     = await response.json();

    if (!data || data.length === 0) {
      container.innerHTML = `<p class="empty-msg">No plants added yet. When a plant is not recognized, you can add it manually.</p>`;
      return;
    }

    container.innerHTML = data.map((item) => {
      const common = item.common_names?.length
        ? item.common_names.slice(0, 2).join(", ")
        : "—";
      const date = item.added_at
        ? new Date(item.added_at).toLocaleDateString("es-CR", {
            day: "2-digit", month: "short", year: "numeric"
          })
        : "—";
      return `
        <div class="manual-item">
          <div class="manual-badge">
            <svg viewBox="0 0 24 24" style="width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            manual
          </div>
          <div class="manual-info">
            <span class="manual-name">${item.scientific_name}</span>
            <span class="manual-common">${common}</span>
          </div>
          <div class="manual-meta">
            <span class="manual-family">${item.family || "—"}</span>
            <span class="history-date">${date}</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<p class="empty-msg">Could not connect to the server.</p>`;
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

  document.getElementById(`tab-${tab}`).classList.add("active");
  document.getElementById(`panel-${tab}`).classList.add("active");

  if (tab === "stats")   loadStats();
  if (tab === "history") loadHistory();
  if (tab === "manual")  loadManualPlants();
}

document.addEventListener("DOMContentLoaded", () => {
  const activePanel = document.querySelector(".tab-panel.active");
  if (!activePanel) switchTab("identify");
});