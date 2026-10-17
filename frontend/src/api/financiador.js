import { get } from "./client";

// Panel de lectura del financiador (RF-40): indicadores agregados y
// expedientes leídos de Fabric con la identidad de PrepagaMSP.
export async function fetchResumenFinanciador() {
  return get("/financiador/resumen");
}

// Filtros opcionales: surge (true/false), plazo (en_plazo | por_vencer |
// vencido | cumplido | cumplido_fuera_de_plazo) y alternativa (alerta | adoptada).
export async function fetchExpedientesFinanciador({ surge, plazo, alternativa } = {}) {
  const params = new URLSearchParams();
  if (surge != null && surge !== "") params.set("surge", String(surge));
  if (plazo) params.set("plazo", plazo);
  if (alternativa) params.set("alternativa", alternativa);
  const query = params.toString();
  const data = await get(`/financiador/expedientes${query ? `?${query}` : ""}`);
  return {
    expedientes: data.expedientes ?? [],
    total: data.total ?? 0,
    alcanzoTope: Boolean(data.alcanzo_tope),
  };
}
