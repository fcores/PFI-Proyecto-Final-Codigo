import { get, postJson } from "./client";

export async function fetchPrescriptions() {
  const data = await get("/prescriptions");
  return data.prescriptions ?? [];
}

export async function createPrescription(body) {
  return postJson("/prescriptions", body);
}
