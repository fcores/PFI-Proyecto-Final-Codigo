import { useAuth } from "../auth/AuthContext";
import { ROLE_LABEL } from "../constants/roles";

export default function TopBar({ title, subtitle, badge }) {
  const { user, logout, loggingOut } = useAuth();
  const displayName = user?.display_name || user?.username || "Usuario";
  const roleLabel = ROLE_LABEL[user?.role] || user?.role || "";

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
        <span
          className="icon-btn user-initial"
          title={roleLabel ? `${displayName} · ${roleLabel}` : displayName}
        >
          {displayName.charAt(0).toUpperCase()}
        </span>
        <button
          type="button"
          className="logout-btn"
          title="Cerrar sesión"
          onClick={logout}
          disabled={loggingOut}
        >
          <span aria-hidden="true">⎋</span>
          <span className="logout-btn-label">{loggingOut ? "Cerrando…" : "Cerrar sesión"}</span>
        </button>
      </div>
    </header>
  );
}
