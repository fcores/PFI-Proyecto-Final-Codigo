import { Navigate, useLocation } from "react-router-dom";
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
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h2>Acceso denegado</h2>
        <p>No tenés permisos para acceder a esta sección.</p>
      </div>
    );
  }

  return children;
}
