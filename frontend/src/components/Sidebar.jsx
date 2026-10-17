import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ROLE_LABEL } from "../constants/roles";
import { useLayout } from "./layoutContext";

const MEDICAMENTOS_SUBTYPES = [
  { to: "/medicamentos/alta", label: "Alta de Medicamentos" },
  { to: "/medicamentos/historial", label: "Historial de Medicamentos" },
];

const MONODROGAS_SUBTYPES = [
  { to: "/monodrogas/alta", label: "Alta de Monodrogas" },
  { to: "/monodrogas/historial", label: "Historial de Monodrogas" },
];

const AUDITORIAS_SUBTYPES = [
  { to: "/auditoria/cola", label: "Cola de Auditoría" },
  { to: "/trazabilidad", label: "Trazabilidad" },
];

function NavGroup({ emoji, label, active, open, onToggle, subtypes }) {
  const subnavId = `subnav-${label.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <div className="nav-group">
      <button
        className={`nav-group-toggle${active ? " active" : ""}`}
        onClick={onToggle}
        type="button"
        aria-expanded={open}
        aria-controls={subnavId}
      >
        <span className="nav-emoji" aria-hidden="true">{emoji}</span>
        <span className="nav-group-label">{label}</span>
        <span className={`nav-group-chevron${open ? " open" : ""}`} aria-hidden="true">›</span>
      </button>

      {open && (
        <div className="nav-subnav" id={subnavId}>
          {subtypes.map((sub) => (
            <NavLink
              key={sub.to}
              to={sub.to}
              className={({ isActive }) => `nav-subitem${isActive ? " active" : ""}`}
            >
              {sub.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Sidebar() {
  const location = useLocation();
  const { user, logout, loggingOut } = useAuth();
  const { navOpen, setNavOpen } = useLayout();
  const role = user?.role;

  const esSuperAdmin = role === "super_admin";
  const vePrescripciones = esSuperAdmin || role === "prescriptor" || role === "auditor";
  const creaPrescripciones = esSuperAdmin || role === "prescriptor";
  const vePacientes = esSuperAdmin || role === "administrador" || role === "prescriptor";
  const veDatosMaestros = esSuperAdmin || role === "administrador";
  const veAuditorias = esSuperAdmin || role === "auditor";
  const vePanelFinanciador = esSuperAdmin || role === "financiador";

  const prescripcionesSubtypes = [
    ...(creaPrescripciones ? [{ to: "/prescripciones/alta", label: "Alta de Prescripciones" }] : []),
    { to: "/prescripciones/historial", label: "Historial de Prescripciones" },
    // El auditor llega a Trazabilidad desde Auditorías; el prescriptor, desde acá.
    ...(role === "prescriptor" ? [{ to: "/trazabilidad", label: "Trazabilidad" }] : []),
  ];

  const pacientesSubtypes = [
    ...(veDatosMaestros ? [{ to: "/pacientes/alta", label: "Alta de Pacientes" }] : []),
    { to: "/pacientes/historial", label: "Historial de Pacientes" },
  ];

  const pacientesActive = location.pathname.startsWith("/pacientes");
  const medicamentosActive = location.pathname.startsWith("/medicamentos");
  const monodrogasActive = location.pathname.startsWith("/monodrogas");
  const prescripcionesActive =
    location.pathname.startsWith("/prescripciones") ||
    (role === "prescriptor" && location.pathname.startsWith("/trazabilidad"));
  const auditoriasActive =
    location.pathname.startsWith("/auditoria") || location.pathname.startsWith("/trazabilidad");
  const [pacientesOpen, setPacientesOpen] = useState(pacientesActive);
  const [medicamentosOpen, setMedicamentosOpen] = useState(medicamentosActive);
  const [monodrogasOpen, setMonodrogasOpen] = useState(monodrogasActive);
  const [prescripcionesOpen, setPrescripcionesOpen] = useState(prescripcionesActive);
  const [auditoriasOpen, setAuditoriasOpen] = useState(auditoriasActive);

  // Al llegar a una pantalla por un link interno (p. ej. desde el historial),
  // se despliega el grupo que la contiene para que el usuario vea dónde está.
  useEffect(() => {
    if (pacientesActive) setPacientesOpen(true);
    if (medicamentosActive) setMedicamentosOpen(true);
    if (monodrogasActive) setMonodrogasOpen(true);
    if (prescripcionesActive) setPrescripcionesOpen(true);
    if (auditoriasActive) setAuditoriasOpen(true);
  }, [pacientesActive, medicamentosActive, monodrogasActive, prescripcionesActive, auditoriasActive]);

  return (
    <aside id="app-sidebar" className={`sidebar${navOpen ? " sidebar--open" : ""}`}>
      <div className="sidebar-logo">
        <NavLink to="/" aria-label="Inicio">
          <img src="/medchain-logo.svg" alt="MedChain AI" className="logo-img" />
        </NavLink>
        <span className="sidebar-brand">Gestión de prescripciones</span>
        <button
          type="button"
          className="sidebar-close"
          aria-label="Cerrar menú"
          onClick={() => setNavOpen(false)}
        >
          ×
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Navegación principal">
        {vePrescripciones && (
          <NavGroup
            emoji={"\u{1F9EC}"}
            label="Prescripciones"
            active={prescripcionesActive}
            open={prescripcionesOpen}
            onToggle={() => setPrescripcionesOpen((o) => !o)}
            subtypes={prescripcionesSubtypes}
          />
        )}

        {vePacientes && (
          <NavGroup
            emoji={"\u{1F465}"}
            label="Pacientes"
            active={pacientesActive}
            open={pacientesOpen}
            onToggle={() => setPacientesOpen((o) => !o)}
            subtypes={pacientesSubtypes}
          />
        )}

        {veDatosMaestros && (
          <NavGroup
            emoji={"\u{1F48A}"}
            label="Medicamentos"
            active={medicamentosActive}
            open={medicamentosOpen}
            onToggle={() => setMedicamentosOpen((o) => !o)}
            subtypes={MEDICAMENTOS_SUBTYPES}
          />
        )}

        {veDatosMaestros && (
          <NavGroup
            emoji={"\u{1F9EA}"}
            label="Monodrogas"
            active={monodrogasActive}
            open={monodrogasOpen}
            onToggle={() => setMonodrogasOpen((o) => !o)}
            subtypes={MONODROGAS_SUBTYPES}
          />
        )}

        {veAuditorias && (
          <NavGroup
            emoji={"\u{1F517}"}
            label="Auditorías"
            active={auditoriasActive}
            open={auditoriasOpen}
            onToggle={() => setAuditoriasOpen((o) => !o)}
            subtypes={AUDITORIAS_SUBTYPES}
          />
        )}

        {vePanelFinanciador && (
          <div className="nav-group">
            <NavLink
              to="/financiador/panel"
              className={({ isActive }) => `nav-group-toggle${isActive ? " active" : ""}`}
            >
              <span className="nav-emoji" aria-hidden="true">{"\u{1F4CA}"}</span>
              <span className="nav-group-label">Panel del financiador</span>
            </NavLink>
          </div>
        )}

        {esSuperAdmin && (
          <div className="nav-group">
            <NavLink
              to="/usuarios"
              className={({ isActive }) => `nav-group-toggle${isActive ? " active" : ""}`}
            >
              <span className="nav-emoji" aria-hidden="true">{"\u{1F464}"}</span>
              <span className="nav-group-label">Usuarios</span>
            </NavLink>
          </div>
        )}

        {esSuperAdmin && (
          <div className="nav-group">
            <NavLink
              to="/salud"
              className={({ isActive }) => `nav-group-toggle${isActive ? " active" : ""}`}
            >
              <span className="nav-emoji" aria-hidden="true">{"\u{1FA7A}"}</span>
              <span className="nav-group-label">Salud del sistema</span>
            </NavLink>
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar" aria-hidden="true">
            {(user?.display_name || user?.username || "U").charAt(0).toUpperCase()}
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">{user?.display_name || user?.username || "Usuario"}</span>
            <span className="sidebar-user-role">{ROLE_LABEL[role] || role || "Sesión activa"}</span>
          </div>
        </div>
        <button
          type="button"
          className="sidebar-logout-btn"
          title="Cerrar sesión"
          onClick={logout}
          disabled={loggingOut}
        >
          <span aria-hidden="true">⎋</span>
          <span className="sidebar-logout-label">{loggingOut ? "Cerrando…" : "Cerrar sesión"}</span>
        </button>
      </div>
    </aside>
  );
}
