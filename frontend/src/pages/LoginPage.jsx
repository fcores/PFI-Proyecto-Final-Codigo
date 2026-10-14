import { useState } from "react";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { LOGOUT_REASON, useAuth } from "../auth/AuthContext";
import { defaultRouteFor } from "../constants/roles";

const LOGOUT_MESSAGES = {
  [LOGOUT_REASON.MANUAL]: "Cerraste sesión correctamente.",
  [LOGOUT_REASON.EXPIRED]: "Tu sesión expiró. Volvé a ingresar.",
};

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
          <div className="login-aside-top">
            <div className="login-brand">
              <img src="/medchain-logo.svg" alt="MedChain AI" className="login-logo" />
              <span className="login-brand-name">MedChain AI</span>
            </div>
          </div>

          <div className="login-aside-body">
            <h2 className="login-aside-title">
              Plataforma para la gestión de prescripciones
            </h2>
            <p className="login-aside-text">
              Auditoría de prescripciones de alta complejidad,
              con validación asistida y trazabilidad inmutable en blockchain.
            </p>
            <ul className="login-aside-features">
              <li>🧬 Prescripciones oncológicas de alta complejidad</li>
              <li>🔍 Validación y auditoría de concordancia</li>
              <li>🔗 Trazabilidad inmutable en blockchain</li>
            </ul>
          </div>

          <div className="login-aside-footer">
            Salud, Tecnología e Inteligencia Artificial
          </div>
        </aside>

        <section className="login-panel">
          <div className="login-panel-inner">
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
              <span className="login-hint-icon">🔒</span>
              <p>
                Tu sesión se protege con un token temporal. Al finalizar, usá el botón
                "Cerrar sesión".
              </p>
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
