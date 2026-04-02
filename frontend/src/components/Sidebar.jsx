import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

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

const EMPADRONAMIENTO_SUBTYPES = [
  { to: "/empadronamientos/tipo-a", label: "Tipo A" },
  { to: "/empadronamientos/tipo-b", label: "Tipo B" },
  { to: "/empadronamientos/historial", label: "Historial Empadronamientos" },
];

export default function Sidebar() {
  const location = useLocation();
  const pacientesActive = location.pathname.startsWith("/pacientes");
  const medicamentosActive = location.pathname.startsWith("/medicamentos");
  const monodrogasActive = location.pathname.startsWith("/monodrogas");
  const empadronamientoActive = location.pathname.startsWith("/empadronamientos");
  const [pacientesOpen, setPacientesOpen] = useState(pacientesActive);
  const [medicamentosOpen, setMedicamentosOpen] = useState(medicamentosActive);
  const [monodrogasOpen, setMonodrogasOpen] = useState(monodrogasActive);
  const [empadronamientoOpen, setEmpadronamientoOpen] = useState(empadronamientoActive);

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
        <NavLink
          to="/acuerdos"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          <span className="nav-emoji">📋</span> Acuerdos
        </NavLink>

        {/* Empadronamientos con submenú */}
        <div className="nav-group">
          <button
            className={`nav-group-toggle${empadronamientoActive ? " active" : ""}`}
            onClick={() => setEmpadronamientoOpen((o) => !o)}
            type="button"
          >
            <span className="nav-emoji">📝</span>
            <span className="nav-group-label">Empadronamientos</span>
            <span className={`nav-group-chevron${empadronamientoOpen ? " open" : ""}`}>
              ›
            </span>
          </button>

          {empadronamientoOpen && (
            <div className="nav-subnav">
              {EMPADRONAMIENTO_SUBTYPES.map((sub) => (
                <NavLink
                  key={sub.to}
                  to={sub.to}
                  className={({ isActive }) =>
                    `nav-subitem${isActive ? " active" : ""}`
                  }
                >
                  {sub.label}
                </NavLink>
              ))}
            </div>
          )}
        </div>

        <div className="nav-group">
          <button
            className={`nav-group-toggle${pacientesActive ? " active" : ""}`}
            onClick={() => setPacientesOpen((open) => !open)}
            type="button"
          >
            <span className="nav-emoji">👥</span>
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

        <div className="nav-group">
          <button
            className={`nav-group-toggle${medicamentosActive ? " active" : ""}`}
            onClick={() => setMedicamentosOpen((open) => !open)}
            type="button"
          >
            <span className="nav-emoji">💊</span>
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

        <div className="nav-group">
          <button
            className={`nav-group-toggle${monodrogasActive ? " active" : ""}`}
            onClick={() => setMonodrogasOpen((open) => !open)}
            type="button"
          >
            <span className="nav-emoji">🧪</span>
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

        <a href="#">
          <span className="nav-emoji">🔍</span> Auditorías
        </a>
        <a href="#">
          <span className="nav-emoji">📊</span> Reportes
        </a>
        <a href="#">
          <span className="nav-emoji">💬</span> Soporte
        </a>
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">G</div>
          <div className="sidebar-user-info">
            <span className="sidebar-user-name">Usuario</span>
            <span className="sidebar-user-role">Administrador</span>
          </div>
          <button className="icon-btn" title="Configuración">
            ⚙
          </button>
        </div>
      </div>
    </aside>
  );
}
