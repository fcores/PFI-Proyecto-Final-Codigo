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

const PRESCRIPCIONES_SUBTYPES = [
  { to: "/prescripciones/alta", label: "Alta de Prescripciones" },
  { to: "/prescripciones/historial", label: "Historial de Prescripciones" },
];

const AUDITORIAS_SUBTYPES = [
  { to: "/auditoria/cola", label: "Cola de Auditoría" },
  { to: "/trazabilidad", label: "Trazabilidad" },
];

export default function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const role = user?.role;
  const pacientesActive = location.pathname.startsWith("/pacientes");
  const medicamentosActive = location.pathname.startsWith("/medicamentos");
  const monodrogasActive = location.pathname.startsWith("/monodrogas");
  const prescripcionesActive = location.pathname.startsWith("/prescripciones");
  const auditoriasActive = location.pathname.startsWith("/auditoria") || location.pathname.startsWith("/trazabilidad");
  const [pacientesOpen, setPacientesOpen] = useState(pacientesActive);
  const [medicamentosOpen, setMedicamentosOpen] = useState(medicamentosActive);
  const [monodrogasOpen, setMonodrogasOpen] = useState(monodrogasActive);
  const [prescripcionesOpen, setPrescripcionesOpen] = useState(prescripcionesActive);
  const [auditoriasOpen, setAuditoriasOpen] = useState(auditoriasActive);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <NavLink to="/pacientes/alta">
          <img
            src="/medchain-logo.svg"
            alt="MedChain AI"
            className="logo-img"
          />
        </NavLink>
        <span className="sidebar-brand">MedChain AI</span>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group">
          <button
            className={`nav-group-toggle${prescripcionesActive ? " active" : ""}`}
            onClick={() => setPrescripcionesOpen((o) => !o)}
            type="button"
          >
            <span className="nav-emoji">&#x1F9EC;</span>
            <span className="nav-group-label">Prescripciones</span>
            <span className={`nav-group-chevron${prescripcionesOpen ? " open" : ""}`}>
              ›
            </span>
          </button>

          {prescripcionesOpen && (
            <div className="nav-subnav">
              {PRESCRIPCIONES_SUBTYPES.map((sub) => (
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

        {(role === "administrador" || role === "prescriptor") && (
          <div className="nav-group">
            <button
              className={`nav-group-toggle${pacientesActive ? " active" : ""}`}
              onClick={() => setPacientesOpen((open) => !open)}
              type="button"
            >
              <span className="nav-emoji">&#x1F465;</span>
              <span className="nav-group-label">Pacientes</span>
              <span className={`nav-group-chevron${pacientesOpen ? " open" : ""}`}>
                ›
              </span>
            </button>

            {pacientesOpen && (
              <div className="nav-subnav">
                {PACIENTES_SUBTYPES.map((sub) => (
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
        )}

        {role === "administrador" && (
          <div className="nav-group">
            <button
              className={`nav-group-toggle${medicamentosActive ? " active" : ""}`}
              onClick={() => setMedicamentosOpen((open) => !open)}
              type="button"
            >
              <span className="nav-emoji">&#x1F48A;</span>
              <span className="nav-group-label">Medicamentos</span>
              <span className={`nav-group-chevron${medicamentosOpen ? " open" : ""}`}>
                ›
              </span>
            </button>

            {medicamentosOpen && (
              <div className="nav-subnav">
                {MEDICAMENTOS_SUBTYPES.map((sub) => (
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
        )}

        {role === "administrador" && (
          <div className="nav-group">
            <button
              className={`nav-group-toggle${monodrogasActive ? " active" : ""}`}
              onClick={() => setMonodrogasOpen((open) => !open)}
              type="button"
            >
              <span className="nav-emoji">&#x1F9EA;</span>
              <span className="nav-group-label">Monodrogas</span>
              <span className={`nav-group-chevron${monodrogasOpen ? " open" : ""}`}>
                ›
              </span>
            </button>

            {monodrogasOpen && (
              <div className="nav-subnav">
                {MONODROGAS_SUBTYPES.map((sub) => (
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
        )}

        {(role === "administrador" || role === "auditor") && (
          <div className="nav-group">
            <button
              className={`nav-group-toggle${auditoriasActive ? " active" : ""}`}
              onClick={() => setAuditoriasOpen((open) => !open)}
              type="button"
            >
              <span className="nav-emoji">&#x1F517;</span>
              <span className="nav-group-label">Auditorías</span>
              <span className={`nav-group-chevron${auditoriasOpen ? " open" : ""}`}>
                ›
              </span>
            </button>

            {auditoriasOpen && (
              <div className="nav-subnav">
                {AUDITORIAS_SUBTYPES.map((sub) => (
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
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {(user?.display_name || user?.username || "U").charAt(0).toUpperCase()}
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">{user?.display_name || user?.username || "Usuario"}</span>
            <span className="sidebar-user-role">{role || "Sesión activa"}</span>
          </div>
          <button className="icon-btn" title="Cerrar sesión" onClick={logout}>
            ⎋
          </button>
        </div>
      </div>
    </aside>
  );
}
