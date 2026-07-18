import { get, postForm } from "./client";

export async function fetchAgreements() {
  const data = await get("/agreements");
  return data.agreements ?? [];
}

export async function createAgreement(formData) {
  return postForm("/agreements", formData);
}

export async function bulkImportAgreements(formData) {
  return postForm("/agreements/bulk-import", formData);
}
