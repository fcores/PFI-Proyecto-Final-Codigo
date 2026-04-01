/**
 * Reusable status chip (success, warning, error, neutral).
 *
 * @param {"success"|"warning"|"error"|"neutral"} variant
 * @param {string} label
 */
export default function StatusChip({ variant = "neutral", label }) {
  return <span className={`status-chip status-chip--${variant}`}>{label}</span>;
}
