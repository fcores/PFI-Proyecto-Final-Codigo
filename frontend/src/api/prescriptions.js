import { get, postJson } from "./client";

export async function fetchPrescriptions() {
  const data = await get("/prescriptions");
  return data.prescriptions ?? [];
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
