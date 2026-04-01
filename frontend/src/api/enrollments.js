import { get, postForm } from "./client";

export async function fetchEnrollments(tipo) {
  const data = await get(`/enrollments/${tipo}`);
  return data.enrollments ?? [];
}

export async function createEnrollment(tipo, formData) {
  return postForm(`/enrollments/${tipo}`, formData);
}

export async function bulkImportEnrollments(tipo, formData) {
  return postForm(`/enrollments/${tipo}/bulk-import`, formData);
}
