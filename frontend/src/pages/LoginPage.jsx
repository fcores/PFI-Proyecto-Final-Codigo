import { useState } from "react";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { LOGOUT_REASON, useAuth } from "../auth/AuthContext";
import { defaultRouteFor } from "../constants/roles";

const LOGOUT_MESSAGES = {
  [LOGOUT_REASON.MANUAL]: "Cerraste sesión correctamente.",
  [LOGOUT_REASON.EXPIRED]: "Tu sesión expiró. Volvé a ingresar.",
};

// Iconos de trazo (24x24) que heredan el color del texto; reemplazan a los
// emojis, que en Windows se ven chicos y desparejos.
const PROPS_ICONO = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

const ICONOS = {
  adn: (
    <svg {...PROPS_ICONO}>
      <path d="M7 3c0 6 10 6 10 12s-10 4-10 6" />
      <path d="M17 3c0 6-10 6-10 12s10 4 10 6" />
      <path d="M8.5 7h7M8.5 17h7M10 12h4" />
    </svg>
  ),
  auditoria: (
    <svg {...PROPS_ICONO}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 5 5" />
      <path d="m7.8 10.6 1.9 1.9 3.5-3.6" />
    </svg>
  ),
  cadena: (
    <svg {...PROPS_ICONO}>
      <path d="M10 13.5a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1.2 1.2" />
      <path d="M14 10.5a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.2-1.2" />
    </svg>
  ),
  candado: (
    <svg {...PROPS_ICONO}>
      <rect x="5" y="10.5" width="14" height="10" rx="2.2" />
      <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
      <path d="M12 14.5v2.5" />
    </svg>
  ),
};

const VENTAJAS = [
  { icono: "adn", texto: "Prescripciones oncológicas de alta complejidad" },
  { icono: "auditoria", texto: "Validación y auditoría de concordancia" },
  { icono: "cadena", texto: "Trazabilidad inmutable en blockchain" },
];

// Isotipo del logo (el hexagono de public/medchain-logo.svg) en linea. El
// nombre va como texto HTML: dentro de un <img>, el SVG no puede usar la
// fuente web y las palabras, que tienen posiciones fijas, se pisan.
function MarcaMedChain() {
  return (
    <svg className="login-logo" viewBox="4 2 48 52" fill="none" aria-hidden="true">
      <path d="M28 4L48 15.5V38.5L28 50L8 38.5V15.5L28 4Z" fill="rgba(255,255,255,0.15)" stroke="white" strokeWidth="1.5" />
      <rect x="23" y="14" width="10" height="28" rx="2" fill="white" />
      <rect x="16" y="21" width="24" height="10" rx="2" fill="white" />
      <circle cx="28" cy="28" r="2.5" fill="rgba(0,210,180,0.9)" />
      <circle cx="28" cy="6" r="1.5" fill="rgba(0,210,180,0.7)" />
      <circle cx="28" cy="50" r="1.5" fill="rgba(0,210,180,0.7)" />
    </svg>
  );
}

export default function LoginPage() {
  const { isAuthenticated, login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const savedRedirect = location.state?.from?.pathname;
  const logoutMessage = LOGOUT_MESSAGES[location.state?.reason];

  if (isAuthenticated) {
    return <Navigate to={savedRedirect || defaultRouteFor(user?.role)} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(username.trim(), password);
      const destination = savedRedirect || defaultRouteFor(data.user?.role);
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err.message || "No se pudo iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-split">
        <aside className="login-aside">
          <div className="login-aside-inner">
            <div className="login-brand" role="img" aria-label="MedChain AI">
              <MarcaMedChain />
              <span className="login-brand-name" aria-hidden="true">
                Med<span className="login-brand-accent">Chain</span>
                <span className="login-brand-ai">AI</span>
              </span>
            </div>

            <div className="login-aside-body">
              <h2 className="login-aside-title">Plataforma para la gestión de prescripciones</h2>
              <p className="login-aside-text">
                Auditoría de prescripciones de alta complejidad, con validación asistida y trazabilidad
                inmutable en blockchain.
              </p>
              <ul className="login-aside-features">
                {VENTAJAS.map(({ icono, texto }) => (
                  <li key={texto}>
                    <span className="login-feature-icon" aria-hidden="true">
                      {ICONOS[icono]}
                    </span>
                    <span>{texto}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="login-aside-footer">Salud, Tecnología e Inteligencia Artificial</div>
          </div>
        </aside>

        <section className="login-panel">
          <div className="login-panel-inner">
            <div className="login-card">
              <div className="login-heading">
                <span className="login-eyebrow">Bienvenido</span>
                <h1>Iniciar sesión</h1>
                <p>Ingresá tus credenciales para acceder a la plataforma.</p>
              </div>

              <form className="login-form" onSubmit={handleSubmit}>
                <div className="login-field">
                  <label htmlFor="login_username">Usuario</label>
                  <input
                    id="login_username"
                    type="text"
                    autoComplete="username"
                    placeholder="Ingresá tu usuario"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    required
                  />
                </div>

                <div className="login-field">
                  <label htmlFor="login_password">Contraseña</label>
                  <input
                    id="login_password"
                    type="password"
                    autoComplete="current-password"
                    placeholder="Ingresá tu contraseña"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                </div>

                {error ? (
                  <div className="login-error">{error}</div>
                ) : (
                  logoutMessage && <div className="login-info" role="status">{logoutMessage}</div>
                )}

                <button type="submit" className="btn-primary login-submit" disabled={loading}>
                  {loading ? "Ingresando..." : "Ingresar"}
                </button>
              </form>

              <div className="login-divider"><span>Acceso seguro</span></div>

              <div className="login-hint">
                <span className="login-hint-icon" aria-hidden="true">
                  {ICONOS.candado}
                </span>
                <p>
                  Tu sesión se protege con un token temporal. Al finalizar, usá el botón
                  "Cerrar sesión".
                </p>
              </div>
            </div>

            <p className="login-footer">
              © {new Date().getFullYear()} MedChain AI — Salud, Tecnología e IA
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
