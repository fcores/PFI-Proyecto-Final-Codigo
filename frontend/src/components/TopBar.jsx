export default function TopBar({ title, subtitle, badge }) {
  return (
    <header className="top-bar">
      <div className="page-heading">
        <div className="page-heading-copy">
          {badge ? <span className="page-badge">{badge}</span> : null}
          <h1 className="page-title">{title}</h1>
          {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
        </div>
      </div>
      <div className="user-actions">
        <div className="user-chip">
          <span className="user-chip-dot" />
          <span>Online</span>
        </div>
        <button className="icon-btn" title="Configuración">
          ⚙
        </button>
        <button className="icon-btn" title="Usuario">
          G
        </button>
      </div>
    </header>
  );
}
