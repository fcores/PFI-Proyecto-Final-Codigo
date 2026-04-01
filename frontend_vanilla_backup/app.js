const API_BASE_URL = "http://127.0.0.1:8000";

const form = document.getElementById("patient-form");
const statusEl = document.getElementById("form-status");
const tableBody = document.getElementById("patients-table-body");
const btnCancel = document.getElementById("btn-cancel");

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = "status";
  if (type) {
    statusEl.classList.add(type);
  }
}

async function loadPatients() {
  try {
    const res = await fetch(`${API_BASE_URL}/patients`);
    if (!res.ok) {
      throw new Error("No se pudo obtener la lista de pacientes");
    }
    const data = await res.json();
    renderPatients(data.patients || []);
  } catch (error) {
    console.error(error);
    renderPatients([]);
  }
}

function renderPatients(patients) {
  tableBody.innerHTML = "";

  if (!patients.length) {
    const tr = document.createElement("tr");
    tr.className = "empty-row";
    const td = document.createElement("td");
    td.colSpan = 6;
    td.textContent = "No hay datos";
    tr.appendChild(td);
    tableBody.appendChild(tr);
    return;
  }

  for (const p of patients) {
    const tr = document.createElement("tr");

    const fullName = `${p.last_name ?? ""} ${p.first_name ?? ""}`.trim();
    const meds = (p.medications && p.medications.length ? p.medications.join(", ") : "-");

    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${fullName || "-"}</td>
      <td>${p.treatment || "-"}</td>
      <td>${p.provider || "-"}</td>
      <td>${meds}</td>
      <td>Activo</td>
    `;

    tableBody.appendChild(tr);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  setStatus("Guardando paciente...", "");

  try {
    const res = await fetch(`${API_BASE_URL}/patients`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error("Error al guardar el paciente");
    }

    await res.json();
    setStatus("Paciente creado correctamente.", "success");
    form.reset();

    // Volver a cargar la lista
    loadPatients();
  } catch (error) {
    console.error(error);
    setStatus("Ocurrió un error al guardar el paciente.", "error");
  }
});

btnCancel.addEventListener("click", () => {
  form.reset();
  setStatus("Cambios descartados.");
});

// Acordeón de Receta dentro del formulario
document.querySelectorAll(".accordion-header").forEach((btn) => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.accordion;
    const panel = document.getElementById(`panel-${key}`);
    const isOpen = panel.classList.contains("open");

    document.querySelectorAll(".accordion-panel").forEach((p) => p.classList.remove("open"));
    document.querySelectorAll(".accordion-header").forEach((h) => h.classList.remove("active"));

    if (!isOpen) {
      panel.classList.add("open");
      btn.classList.add("active");
    }
  });
});

// Inicialización
loadPatients();

