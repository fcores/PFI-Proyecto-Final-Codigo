import { get, postForm } from "./client";

// El backend pagina por limit/offset (máx. 500 por página).
export async function fetchPatients({ limit = 200, offset = 0 } = {}) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const data = await get(`/patients?${params.toString()}`);
  return data.patients ?? [];
}

export async function createPatient(formData) {
  return postForm("/patients", formData);
}

export async function bulkImportPatients(formData) {
  return postForm("/patients/bulk-import", formData);
}

export async function fetchPatient(patientId) {
  return get(`/patients/${patientId}`);
}
