export default function ConfidenceBar({ value, low = 0.35, high = 0.65, label }) {
  const pct = Math.max(0, Math.min(100, Number(value ?? 0) * 100));
  const lowPct = Math.max(0, Math.min(100, Number(low) * 100));
  const highPct = Math.max(0, Math.min(100, Number(high) * 100));

  let tone = "confidence-bar__fill--mid";
  if (value != null && value >= high) tone = "confidence-bar__fill--high";
  if (value != null && value <= low) tone = "confidence-bar__fill--low";

  return (
    <div className="confidence-bar" aria-label={label || "Nivel de confianza"}>
      <div className="confidence-bar__track">
        <div className={`confidence-bar__fill ${tone}`} style={{ width: `${pct}%` }} />
        <span className="confidence-bar__mark" style={{ left: `${lowPct}%` }} />
        <span className="confidence-bar__mark confidence-bar__mark--high" style={{ left: `${highPct}%` }} />
      </div>
      <div className="confidence-bar__meta">
        <span>{label || "P(concordante)"}</span>
        <strong>{value == null ? "—" : `${(Number(value) * 100).toFixed(1)}%`}</strong>
      </div>
    </div>
  );
}
