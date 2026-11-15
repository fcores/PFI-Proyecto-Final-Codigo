import { get, postJson } from "./client";

// La cola de auditoria son los assets de Fabric por estado
// (PENDIENTE_AUDITORIA | EN_REVISION), paginados por bookmark.
export async function fetchAuditQueue({ estado = "PENDIENTE_AUDITORIA", bookmark = "", pageSize = 50 } = {}) {
  const params = new URLSearchParams({ estado, page_size: String(pageSize) });
  if (bookmark) params.set("bookmark", bookmark);
  const data = await get(`/audit/queue?${params.toString()}`);
  return {
    prescriptions: data.prescriptions ?? [],
    bookmark: data.bookmark ?? null,
  };
}

export async function fetchAuditDetail(prescriptionId) {
  return get(`/audit/${prescriptionId}`);
}

// accion: "revision" | "aprobar" | "rechazar"
export async function postAuditAction(prescriptionId, accion, justificacion) {
  return postJson(`/audit/${prescriptionId}/accion`, { accion, justificacion });
}
