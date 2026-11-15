repo: fcores/PFI-Proyecto-Final-Codigo
branch: desarrollo
path: frontend/src

## Last sync
date: 2026-08-16T15:32:11Z

### Updated in this project
- Mockups de alta fidelidad de las 12 pantallas del frontend (MedChain AI).
- Sistema visual del repo conservado; densidad compacta y jerarquía revisada.
- Estados de Prescripción y Caso de auditoría; variantes por rol y 3 tratamientos de IA.
- Logo real `medchain-logo.svg` copiado del repo y usado en login, sidebars y encabezado.

## Sync history
- 2026-08-16T15:16:20Z — lectura inicial de `frontend/src` y construcción de las 12 pantallas.

## Screen map
| Pantalla del mockup | Archivos del repo |
| --- | --- |
| 01 Login | frontend/src/pages/LoginPage.jsx, frontend/src/index.css |
| 02 Alta de prescripción | frontend/src/pages/PrescripcionPage.jsx, components/FormField.jsx, components/ConfidenceBar.jsx |
| 03 Historial de prescripciones | frontend/src/pages/HistorialPrescripcionesPage.jsx, components/DataTable.jsx |
| 04 Cola de auditoría | frontend/src/pages/AuditQueuePage.jsx, constants/estadoVariant.js |
| 05 Caso de auditoría | frontend/src/pages/AuditCasePage.jsx |
| 06 Alta de pacientes | frontend/src/pages/PacientesPage.jsx, components/Accordion.jsx, components/BulkImportCard.jsx |
| 07 Historial de pacientes | frontend/src/pages/HistorialPacientesPage.jsx |
| 08 Alta de medicamentos | frontend/src/pages/AltaMedicamentosPage.jsx |
| 09 Historial de medicamentos | frontend/src/pages/HistorialMedicamentosPage.jsx |
| 10 Alta de monodrogas | frontend/src/pages/MonodrogasPage.jsx |
| 11 Historial de monodrogas | frontend/src/pages/HistorialMonodrogasPage.jsx |
| 12 Trazabilidad | frontend/src/pages/TrazabilidadPage.jsx |
| Variantes por rol | frontend/src/components/Sidebar.jsx, auth/ProtectedRoute.jsx, App.jsx |
| Chrome (sidebar / topbar) | frontend/src/components/Sidebar.jsx, TopBar.jsx, Layout.jsx |
| Logo (todas las pantallas) | frontend/public/medchain-logo.svg |
