export const ESTADO_VARIANT = {
  // Ciclo de vida on-chain de la prescripcion (chaincode)
  PENDIENTE_AUDITORIA: "warning",
  EN_REVISION: "info",
  APROBADA: "success",
  RECHAZADA: "error",
  // Veredicto del motor reglas + ML (soporte de decision)
  APROBADO: "success",
  REVISION: "warning",
  RECHAZADO: "error",
  pendiente: "neutral",
  info: "info",
};

export const ESTADO_LABEL = {
  PENDIENTE_AUDITORIA: "Pendiente de auditoría",
  EN_REVISION: "En revisión",
  APROBADA: "Aprobada",
  RECHAZADA: "Rechazada",
};

// El veredicto del motor es una recomendación: se rotula como sugerencia para
// no confundirlo con el dictamen del auditor.
export const ML_LABEL = {
  APROBADO: "Sugiere aprobar",
  REVISION: "Sugiere revisar",
  RECHAZADO: "Sugiere rechazar",
};

export const ACCION_LABEL = {
  revision: "Revisión",
  aprobar: "Aprobación",
  rechazar: "Rechazo",
};

export function estadoLabel(estado) {
  return ESTADO_LABEL[estado] || estado || "—";
}

export function mlLabel(estado) {
  return ML_LABEL[estado] || estado || "—";
}
