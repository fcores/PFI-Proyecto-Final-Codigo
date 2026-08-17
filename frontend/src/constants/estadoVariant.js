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
