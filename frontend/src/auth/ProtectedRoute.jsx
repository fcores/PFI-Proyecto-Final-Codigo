import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

export default function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
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
