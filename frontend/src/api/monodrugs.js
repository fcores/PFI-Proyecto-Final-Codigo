import { get, postForm } from "./client";

export async function fetchMonodrugs() {
  const data = await get("/monodrugs");
  return data.monodrugs ?? [];
}

export async function createMonodrug(formData) {
  return postForm("/monodrugs", formData);
}

export async function bulkImportMonodrugs(formData) {
  return postForm("/monodrugs/bulk-import", formData);
}
