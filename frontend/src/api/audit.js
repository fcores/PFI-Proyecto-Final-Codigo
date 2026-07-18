import { get, postJson } from "./client";

export async function fetchAuditQueue() {
  return get("/audit/queue");
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
  return get(`/audit/cases/${caseId}/history`);
}
