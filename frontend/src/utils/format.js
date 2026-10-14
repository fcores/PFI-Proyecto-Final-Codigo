const currencyFormatter = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  minimumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

// Tolera null/undefined/no numéricos: el veredicto ML puede venir sin costos
// cuando el catálogo no tiene precio para algún fármaco.
export function formatCurrency(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? currencyFormatter.format(n) : "—";
}

export function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? numberFormatter.format(n) : String(value);
}

export function formatDay(raw) {
  if (!raw) return "—";
  // Las fechas "YYYY-MM-DD" se interpretan como día calendario, sin corrimiento por zona horaria.
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(raw));
  if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? String(raw) : date.toLocaleDateString("es-AR");
}

export function capitalize(text) {
  if (!text) return "";
  return text.charAt(0).toUpperCase() + text.slice(1);
}
