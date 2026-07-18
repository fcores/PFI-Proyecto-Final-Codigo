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
import AcuerdoPage from "./pages/AcuerdoPage";
import EmpadronamientoPage from "./pages/EmpadronamientoPage";
import HistorialEmpadronamientosPage from "./pages/HistorialEmpadronamientosPage";
import AuditQueuePage from "./pages/AuditQueuePage";
import AuditCasePage from "./pages/AuditCasePage";
import LoginPage from "./pages/LoginPage";
import ProtectedRoute from "./auth/ProtectedRoute";

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
        <Route path="/" element={<Navigate to="/prescripciones/alta" replace />} />

        <Route path="/prescripciones" element={<Navigate to="/prescripciones/alta" replace />} />
        <Route path="/prescripciones/alta" element={<PrescripcionPage />} />
        <Route path="/prescripciones/historial" element={<HistorialPrescripcionesPage />} />

        <Route path="/pacientes" element={<Navigate to="/pacientes/alta" replace />} />
        <Route path="/pacientes/alta" element={
          <ProtectedRoute roles={["administrador", "prescriptor"]}><PacientesPage /></ProtectedRoute>
        } />
        <Route path="/pacientes/historial" element={
          <ProtectedRoute roles={["administrador", "prescriptor"]}><HistorialPacientesPage /></ProtectedRoute>
        } />

        <Route path="/medicamentos" element={<Navigate to="/medicamentos/alta" replace />} />
        <Route path="/medicamentos/alta" element={
          <ProtectedRoute roles={["administrador"]}><AltaMedicamentosPage /></ProtectedRoute>
        } />
        <Route path="/medicamentos/historial" element={
          <ProtectedRoute roles={["administrador"]}><HistorialMedicamentosPage /></ProtectedRoute>
        } />

        <Route path="/monodrogas" element={<Navigate to="/monodrogas/alta" replace />} />
        <Route path="/monodrogas/alta" element={
          <ProtectedRoute roles={["administrador"]}><MonodrogasPage /></ProtectedRoute>
        } />
        <Route path="/monodrogas/historial" element={
          <ProtectedRoute roles={["administrador"]}><HistorialMonodrogasPage /></ProtectedRoute>
        } />

        <Route path="/acuerdos" element={
          <ProtectedRoute roles={["administrador"]}><AcuerdoPage /></ProtectedRoute>
        } />
        <Route path="/empadronamientos/historial" element={
          <ProtectedRoute roles={["administrador"]}><HistorialEmpadronamientosPage /></ProtectedRoute>
        } />
        <Route path="/empadronamientos/tipo-c" element={<Navigate to="/empadronamientos/tipo-a" replace />} />
        <Route path="/empadronamientos/:tipo" element={
          <ProtectedRoute roles={["administrador"]}><EmpadronamientoPage /></ProtectedRoute>
        } />
        <Route path="/empadronamientos" element={<Navigate to="/empadronamientos/tipo-a" replace />} />

        <Route path="/trazabilidad" element={
          <ProtectedRoute roles={["administrador", "auditor"]}><TrazabilidadPage /></ProtectedRoute>
        } />

        <Route path="/auditoria/cola" element={
          <ProtectedRoute roles={["administrador", "auditor"]}><AuditQueuePage /></ProtectedRoute>
        } />
        <Route path="/auditoria/caso/:caseId" element={
          <ProtectedRoute roles={["administrador", "auditor"]}><AuditCasePage /></ProtectedRoute>
        } />
      </Route>
    </Routes>
  );
}
