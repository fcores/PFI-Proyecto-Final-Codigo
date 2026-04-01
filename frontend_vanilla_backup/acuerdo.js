const API_BASE_URL = "http://127.0.0.1:8000";

const form = document.getElementById("agreement-form");
const statusEl = document.getElementById("form-status");
const btnCancel = document.getElementById("btn-cancel");
const contratoInput = document.getElementById("contrato_file");
const contratoFilename = document.getElementById("contrato-filename");

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = "status";
  if (type) statusEl.classList.add(type);
}

contratoInput.addEventListener("change", function () {
  if (this.files.length) {
    contratoFilename.textContent = this.files[0].name;
  } else {
    contratoFilename.textContent = "";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  setStatus("Guardando acuerdo...", "");

  try {
    const res = await fetch(`${API_BASE_URL}/agreements`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al guardar el acuerdo");
    }

    await res.json();
    setStatus("Acuerdo creado correctamente.", "success");
    form.reset();
    contratoFilename.textContent = "";
  } catch (error) {
    console.error(error);
    setStatus(error.message || "Ocurrió un error al guardar el acuerdo.", "error");
  }
});

btnCancel.addEventListener("click", () => {
  form.reset();
  contratoFilename.textContent = "";
  setStatus("Cambios descartados.");
});
