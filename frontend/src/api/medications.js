import { get, postForm } from "./client";

export async function fetchMedications() {
  const data = await get("/medications");
  return data.medications ?? [];
}

export async function createMedication(formData) {
  return postForm("/medications", formData);
}

export async function bulkImportMedications(formData) {
  return postForm("/medications/bulk-import", formData);
}
