import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import PacientesPage from "./pages/PacientesPage";
import HistorialPacientesPage from "./pages/HistorialPacientesPage";
import AltaMedicamentosPage from "./pages/AltaMedicamentosPage";
import HistorialMedicamentosPage from "./pages/HistorialMedicamentosPage";
import MonodrogasPage from "./pages/MonodrogasPage";
import HistorialMonodrogasPage from "./pages/HistorialMonodrogasPage";
import PrescripcionPage from "./pages/PrescripcionPage";
import HistorialPrescripcionesPage from "./pages/HistorialPrescripcionesPage";
import TrazabilidadPage from "./pages/TrazabilidadPage";
import AuditQueuePage from "./pages/AuditQueuePage";
import AuditCasePage from "./pages/AuditCasePage";
import UsuariosPage from "./pages/UsuariosPage";
import SaludPage from "./pages/SaludPage";
import LoginPage from "./pages/LoginPage";
import ProtectedRoute from "./auth/ProtectedRoute";
import { useAuth } from "./auth/AuthContext";
import { defaultRouteFor } from "./constants/roles";

// Landing segun rol: cada perfil aterriza en su pantalla principal.
function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={defaultRouteFor(user?.role)} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomeRedirect />} />

        <Route path="/prescripciones" element={<Navigate to="/prescripciones/alta" replace />} />
        <Route path="/prescripciones/alta" element={
          <ProtectedRoute roles={["prescriptor", "super_admin"]}><PrescripcionPage /></ProtectedRoute>
        } />
        <Route path="/prescripciones/historial" element={
          <ProtectedRoute roles={["prescriptor", "auditor", "super_admin"]}><HistorialPrescripcionesPage /></ProtectedRoute>
        } />

        <Route path="/pacientes" element={<Navigate to="/pacientes/historial" replace />} />
        <Route path="/pacientes/alta" element={
          <ProtectedRoute roles={["administrador", "super_admin"]}><PacientesPage /></ProtectedRoute>
        } />
        <Route path="/pacientes/historial" element={
          <ProtectedRoute roles={["administrador", "prescriptor", "super_admin"]}><HistorialPacientesPage /></ProtectedRoute>
        } />

        <Route path="/medicamentos" element={<Navigate to="/medicamentos/alta" replace />} />
        <Route path="/medicamentos/alta" element={
          <ProtectedRoute roles={["administrador", "super_admin"]}><AltaMedicamentosPage /></ProtectedRoute>
        } />
        <Route path="/medicamentos/historial" element={
          <ProtectedRoute roles={["administrador", "super_admin"]}><HistorialMedicamentosPage /></ProtectedRoute>
        } />

        <Route path="/monodrogas" element={<Navigate to="/monodrogas/alta" replace />} />
        <Route path="/monodrogas/alta" element={
          <ProtectedRoute roles={["administrador", "super_admin"]}><MonodrogasPage /></ProtectedRoute>
        } />
        <Route path="/monodrogas/historial" element={
          <ProtectedRoute roles={["administrador", "super_admin"]}><HistorialMonodrogasPage /></ProtectedRoute>
        } />

        <Route path="/trazabilidad" element={
          <ProtectedRoute roles={["prescriptor", "auditor", "super_admin"]}><TrazabilidadPage /></ProtectedRoute>
        } />

        <Route path="/auditoria/cola" element={
          <ProtectedRoute roles={["auditor", "super_admin"]}><AuditQueuePage /></ProtectedRoute>
        } />
        <Route path="/auditoria/caso/:prescriptionId" element={
          <ProtectedRoute roles={["auditor", "super_admin"]}><AuditCasePage /></ProtectedRoute>
        } />

        <Route path="/usuarios" element={
          <ProtectedRoute roles={["super_admin"]}><UsuariosPage /></ProtectedRoute>
        } />
        <Route path="/salud" element={
          <ProtectedRoute roles={["super_admin"]}><SaludPage /></ProtectedRoute>
        } />
      </Route>
    </Routes>
  );
}
