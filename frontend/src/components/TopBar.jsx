import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { ROLE_LABEL } from "../constants/roles";
import ChangePasswordDialog from "./ChangePasswordDialog";
import { useLayout } from "./layoutContext";

function UserMenu() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const ref = useRef(null);
  const displayName = user?.display_name || user?.username || "Usuario";
  const roleLabel = ROLE_LABEL[user?.role] || user?.role || "";

  useEffect(() => {
    if (!open) return undefined;
    function onPointer(event) {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    }
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="user-menu" ref={ref}>
      <button
        type="button"
        className="user-menu__trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="user-menu__avatar" aria-hidden="true">
          {displayName.charAt(0).toUpperCase()}
        </span>
        <span className="user-menu__name">{displayName}</span>
        <span className="user-menu__chevron" aria-hidden="true">
          ▾
        </span>
      </button>
      {open ? (
        <div className="user-menu__panel" role="menu">
          <div className="user-menu__info">
            <strong>{displayName}</strong>
            <span>
              {user?.username}
              {roleLabel ? ` · ${roleLabel}` : ""}
            </span>
          </div>
          <button
            type="button"
            role="menuitem"
            className="user-menu__item"
            onClick={() => {
              setOpen(false);
              setPasswordOpen(true);
            }}
          >
            Cambiar contraseña
          </button>
        </div>
      ) : null}
      <ChangePasswordDialog open={passwordOpen} onClose={() => setPasswordOpen(false)} />
    </div>
  );
}

export default function TopBar({ title, subtitle, badge, actions }) {
  const { navOpen, setNavOpen } = useLayout();

  return (
    <header className="top-bar">
      <button
        type="button"
        className="nav-toggle"
        aria-label={navOpen ? "Cerrar menú" : "Abrir menú"}
        aria-expanded={navOpen}
        aria-controls="app-sidebar"
        onClick={() => setNavOpen(!navOpen)}
      >
        ☰
      </button>
      <div className="page-heading">
        <div className="page-heading-copy">
          {badge ? <span className="page-badge">{badge}</span> : null}
          <h1 className="page-title">{title}</h1>
          {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
        </div>
      </div>
      <div className="user-actions">
        {actions}
        <UserMenu />
      </div>
    </header>
  );
}
