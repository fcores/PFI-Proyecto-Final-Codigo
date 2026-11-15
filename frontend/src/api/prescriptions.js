import { get, postJson } from "./client";

// Las prescripciones viven en Fabric: los listados se paginan por bookmark
// ("Cargar más"), no por offset.
export async function fetchPrescriptions({ estado = "", bookmark = "", pageSize = 50 } = {}) {
  const params = new URLSearchParams({ page_size: String(pageSize) });
  if (estado) params.set("estado", estado);
  if (bookmark) params.set("bookmark", bookmark);
  const data = await get(`/prescriptions?${params.toString()}`);
  return {
    prescriptions: data.prescriptions ?? [],
    bookmark: data.bookmark ?? null,
  };
}

export async function fetchPrescription(prescriptionId) {
  return get(`/prescriptions/${prescriptionId}`);
}

export async function fetchPrescriptionHistory(prescriptionId) {
  const data = await get(`/prescriptions/${prescriptionId}/history`);
  return data.history ?? [];
}

export async function verifyPrescription(prescriptionId) {
  return get(`/prescriptions/${prescriptionId}/verify`);
}

export async function verifyPrescriptionSignature(prescriptionId) {
  return get(`/prescriptions/${prescriptionId}/firma/verificacion`);
}

export async function createPrescription(body) {
  return postJson("/prescriptions", body);
}

export async function fetchRegimenes() {
  const data = await get("/prescriptions/regimenes");
  return data.regimenes ?? [];
}

export async function fetchDosisReferencia(idRegimen, pesoKg, tallaCm) {
  const params = new URLSearchParams({
    id_regimen: idRegimen,
    peso_kg: String(pesoKg),
    talla_cm: String(tallaCm),
  });
  return get(`/prescriptions/dosis-referencia?${params.toString()}`);
}

export async function recomendarRegimen(body) {
  return postJson("/prescriptions/recomendacion", body);
}
