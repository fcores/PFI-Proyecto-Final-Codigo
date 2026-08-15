import { get, postJson } from "./client";

export async function fetchAuditQueue() {
  const data = await get("/audit/queue");
  return data.cases ?? [];
}

export async function fetchAuditCase(caseId) {
  return get(`/audit/cases/${caseId}`);
}

export async function createDictamen(caseId, resultado, justificacion) {
  return postJson(`/audit/cases/${caseId}/dictamen`, { resultado, justificacion });
}

export async function createCorrection(caseId, campo, valorNuevo, justificacion) {
  return postJson(`/audit/cases/${caseId}/corrections`, {
    campo,
    valor_nuevo: valorNuevo,
    justificacion,
  });
}

export async function fetchCorrectionHistory(caseId) {
  const data = await get(`/audit/cases/${caseId}/history`);
  return data.corrections ?? [];
}
