import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const PACIENTES_SUBTYPES = [
  { to: "/pacientes/alta", label: "Alta de Pacientes" },
  { to: "/pacientes/historial", label: "Historial de Pacientes" },
];

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

const ROLE_LABEL = {
  super_admin: "Super Admin",
  administrador: "Administrativo",
  prescriptor: "Prescriptor",
  auditor: "Auditor",
};

function NavGroup({ emoji, label, active, open, onToggle, subtypes }) {
  return (
    <div className="nav-group">
      <button
        className={`nav-group-toggle${active ? " active" : ""}`}
        onClick={onToggle}
        type="button"
      >
        <span className="nav-emoji">{emoji}</span>
        <span className="nav-group-label">{label}</span>
        <span className={`nav-group-chevron${open ? " open" : ""}`}>›</span>
      </button>

      {open && (
        <div className="nav-subnav">
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
  const { user, logout } = useAuth();
  const role = user?.role;

  const esSuperAdmin = role === "super_admin";
  const vePrescripciones = esSuperAdmin || role === "prescriptor" || role === "auditor";
  const creaPrescripciones = esSuperAdmin || role === "prescriptor";
  const vePacientes = esSuperAdmin || role === "administrador" || role === "prescriptor";
  const veDatosMaestros = esSuperAdmin || role === "administrador";
  const veAuditorias = esSuperAdmin || role === "auditor";

  const prescripcionesSubtypes = [
    ...(creaPrescripciones ? [{ to: "/prescripciones/alta", label: "Alta de Prescripciones" }] : []),
    { to: "/prescripciones/historial", label: "Historial de Prescripciones" },
  ];

  const pacientesActive = location.pathname.startsWith("/pacientes");
  const medicamentosActive = location.pathname.startsWith("/medicamentos");
  const monodrogasActive = location.pathname.startsWith("/monodrogas");
  const prescripcionesActive = location.pathname.startsWith("/prescripciones");
  const auditoriasActive =
    location.pathname.startsWith("/auditoria") || location.pathname.startsWith("/trazabilidad");
  const [pacientesOpen, setPacientesOpen] = useState(pacientesActive);
  const [medicamentosOpen, setMedicamentosOpen] = useState(medicamentosActive);
  const [monodrogasOpen, setMonodrogasOpen] = useState(monodrogasActive);
  const [prescripcionesOpen, setPrescripcionesOpen] = useState(prescripcionesActive);
  const [auditoriasOpen, setAuditoriasOpen] = useState(auditoriasActive);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <NavLink to="/">
          <img src="/medchain-logo.svg" alt="MedChain AI" className="logo-img" />
        </NavLink>
        <span className="sidebar-brand">MedChain AI</span>
      </div>

      <nav className="sidebar-nav">
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
            subtypes={PACIENTES_SUBTYPES}
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

        {esSuperAdmin && (
          <div className="nav-group">
            <NavLink
              to="/usuarios"
              className={({ isActive }) => `nav-group-toggle${isActive ? " active" : ""}`}
            >
              <span className="nav-emoji">{"\u{1F464}"}</span>
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
              <span className="nav-emoji">{"\u{1FA7A}"}</span>
              <span className="nav-group-label">Salud del sistema</span>
            </NavLink>
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {(user?.display_name || user?.username || "U").charAt(0).toUpperCase()}
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">{user?.display_name || user?.username || "Usuario"}</span>
            <span className="sidebar-user-role">{ROLE_LABEL[role] || role || "Sesión activa"}</span>
          </div>
          <button className="icon-btn" title="Cerrar sesión" onClick={logout}>
            ⎋
          </button>
        </div>
      </div>
    </aside>
  );
}
