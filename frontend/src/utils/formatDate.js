export function formatDate(raw) {
  if (!raw) return "—";
  try {
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return String(raw);
    return date.toLocaleString("es-AR");
  } catch {
    return String(raw);
  }
}
