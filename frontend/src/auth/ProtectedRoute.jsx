import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, user, logoutReason } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    // Tras un cierre de sesión (manual o por expiración) no se recuerda la ruta:
    // el próximo usuario puede tener otro rol y no tener acceso a ella.
    const state = logoutReason ? { reason: logoutReason } : { from: location };
    return <Navigate to="/login" replace state={state} />;
  }

  if (roles && !roles.includes(user?.role)) {
    return (
      <main className="page">
        <section className="card state-card" role="alert">
          <h2>Acceso denegado</h2>
          <p className="muted">Tu rol no tiene permisos para acceder a esta sección.</p>
          <div className="state-card__actions">
            <Link to="/" className="btn-primary btn-as-link">
              Ir a mi pantalla principal
            </Link>
          </div>
        </section>
      </main>
    );
  }

  return children;
}
