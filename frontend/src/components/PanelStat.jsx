/**
 * Small stat badge used in the right-column panels.
 *
 * @param {number} count
 * @param {string} singular
 * @param {string} [plural]
 */
export default function PanelStat({ count, singular, plural }) {
  const label = count === 1 ? singular : (plural ?? `${singular}s`);
  return (
    <div className="panel-stat">
      <strong>{count}</strong>
      <span>{label}</span>
    </div>
  );
}
