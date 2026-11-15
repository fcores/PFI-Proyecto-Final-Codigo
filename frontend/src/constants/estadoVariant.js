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

// Semáforo de plazos de la Res. SSSalud 951/2025 (calculado por el backend).
export const PLAZO_VARIANT = {
  en_plazo: "success",
  por_vencer: "warning",
  vencido: "error",
  cumplido: "success",
  cumplido_fuera_de_plazo: "error",
};

export const PLAZO_LABEL = {
  en_plazo: "En plazo",
  por_vencer: "Por vencer",
  vencido: "Vencido",
  cumplido: "Cumplido",
  cumplido_fuera_de_plazo: "Cumplido fuera de plazo",
};

/**
 * Plazo que corresponde mirar: el de respuesta mientras el auditor no actuó,
 * y el de resolución después.
 */
export function plazoVigente(plazos) {
  if (!plazos) return null;
  if (plazos.respuesta && !plazos.respuesta.cumplido_en) {
    return { ...plazos.respuesta, tipo: "Respuesta (5 días corridos)" };
  }
  if (plazos.resolucion) {
    return { ...plazos.resolucion, tipo: "Resolución (30 días hábiles)" };
  }
  return null;
}

export function plazoTexto(plazo) {
  if (!plazo) return "—";
  const etiqueta = PLAZO_LABEL[plazo.estado] || plazo.estado;
  if (plazo.dias_restantes == null) return etiqueta;
  if (plazo.dias_restantes < 0) return `${etiqueta} (hace ${Math.abs(plazo.dias_restantes)} d)`;
  return `${etiqueta} (${plazo.dias_restantes} d)`;
}

export function estadoLabel(estado) {
  return ESTADO_LABEL[estado] || estado || "—";
}

export function mlLabel(estado) {
  return ML_LABEL[estado] || estado || "—";
}
