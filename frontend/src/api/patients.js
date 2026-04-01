import { get, postForm } from "./client";

export async function fetchPatients() {
  const data = await get("/patients");
  return data.patients ?? [];
}

export async function createPatient(formData) {
  return postForm("/patients", formData);
}

export async function bulkImportPatients(formData) {
  return postForm("/patients/bulk-import", formData);
}
