/**
 * Reusable card header used in form cards and panel cards.
 *
 * @param {string}  eyebrow  - Small label above the title
 * @param {string}  title    - Main heading
 * @param {string}  [description]
 * @param {string}  [badge]  - Optional badge on the right
 * @param {boolean} [split]  - Use split layout (title left, badge right)
 */
export default function CardHeader({
  eyebrow,
  title,
  description,
  badge,
  split = false,
}) {
  return (
    <header className={`card-header${split ? " card-header--split" : ""}`}>
      <div>
        {eyebrow && <span className="card-eyebrow">{eyebrow}</span>}
        <h2 className="card-title">{title}</h2>
        {description && <p className="card-description">{description}</p>}
      </div>
      {badge && <div className="card-badge">{badge}</div>}
    </header>
  );
}
