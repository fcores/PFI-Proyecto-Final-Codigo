import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import PacientesPage from "./pages/PacientesPage";
import HistorialPacientesPage from "./pages/HistorialPacientesPage";
import AltaMedicamentosPage from "./pages/AltaMedicamentosPage";
import HistorialMedicamentosPage from "./pages/HistorialMedicamentosPage";
import MonodrogasPage from "./pages/MonodrogasPage";
import HistorialMonodrogasPage from "./pages/HistorialMonodrogasPage";
import AcuerdoPage from "./pages/AcuerdoPage";
import EmpadronamientoPage from "./pages/EmpadronamientoPage";
import HistorialEmpadronamientosPage from "./pages/HistorialEmpadronamientosPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/pacientes/alta" replace />} />
        <Route path="/pacientes" element={<Navigate to="/pacientes/alta" replace />} />
        <Route path="/pacientes/alta" element={<PacientesPage />} />
        <Route path="/pacientes/historial" element={<HistorialPacientesPage />} />
        <Route path="/medicamentos" element={<Navigate to="/medicamentos/alta" replace />} />
        <Route path="/medicamentos/alta" element={<AltaMedicamentosPage />} />
        <Route path="/medicamentos/historial" element={<HistorialMedicamentosPage />} />
        <Route path="/monodrogas" element={<Navigate to="/monodrogas/alta" replace />} />
        <Route path="/monodrogas/alta" element={<MonodrogasPage />} />
        <Route path="/monodrogas/historial" element={<HistorialMonodrogasPage />} />
        <Route path="/acuerdos" element={<AcuerdoPage />} />
        <Route path="/empadronamientos/historial" element={<HistorialEmpadronamientosPage />} />
        <Route path="/empadronamientos/tipo-c" element={<Navigate to="/empadronamientos/tipo-a" replace />} />
        <Route path="/empadronamientos/:tipo" element={<EmpadronamientoPage />} />
        <Route path="/empadronamientos" element={<Navigate to="/empadronamientos/tipo-a" replace />} />
      </Route>
    </Routes>
  );
}
