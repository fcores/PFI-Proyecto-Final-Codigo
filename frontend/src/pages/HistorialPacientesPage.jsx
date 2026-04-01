import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchPatients } from "../api/patients";

const TABLE_COLUMNS = [
  "ID",
  "Paciente",
  "Diagnóstico",
  "Prestador",
  "Tipo Emp.",
  "Inicio",
  "1ra Toma",
  "Cadencia",
  "Estado",
];

const EMPADRONAMIENTO_OPTIONS = [
  { value: "tipo-a", label: "Tipo A" },
  { value: "tipo-b", label: "Tipo B" },
];

function formatDate(value) {
  if (!value) return "-";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

export default function HistorialPacientesPage() {
  const [patients, setPatients] = useState([]);
  const [filters, setFilters] = useState({
    query: "",
    provider: "",
    tipo_empadronamiento: "",
  });

  const loadPatients = useCallback(async () => {
    try {
      setPatients(await fetchPatients());
    } catch {
      setPatients([]);
    }
  }, []);

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  const providerOptions = useMemo(() => {
    const uniqueProviders = new Set(
      patients.map((patient) => patient.provider).filter(Boolean),
    );
    return Array.from(uniqueProviders).sort((a, b) => a.localeCompare(b));
  }, [patients]);

  const filteredPatients = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();

    return patients.filter((patient) => {
      const searchableText = [
        patient.sap_id,
        patient.first_name,
        patient.last_name,
        patient.provider,
        patient.treatment,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery
        ? searchableText.includes(normalizedQuery)
        : true;
      const matchesProvider = filters.provider
        ? patient.provider === filters.provider
        : true;
      const matchesTipo = filters.tipo_empadronamiento
        ? patient.tipo_empadronamiento === filters.tipo_empadronamiento
        : true;

      return matchesQuery && matchesProvider && matchesTipo;
    });
  }, [filters, patients]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      query: "",
      provider: "",
      tipo_empadronamiento: "",
    });
  }

  function renderPatientRow(patient) {
    const fullName = `${patient.last_name ?? ""} ${patient.first_name ?? ""}`.trim();
    const tipoEmp = patient.tipo_empadronamiento
      ? patient.tipo_empadronamiento.toUpperCase().replace("TIPO-", "")
      : "-";

    return (
      <tr key={patient.id}>
        <td>{patient.id}</td>
        <td>{fullName || "-"}</td>
        <td>{patient.treatment || "-"}</td>
        <td>{patient.provider || "-"}</td>
        <td>
          <span className="enrollment-code-chip">{tipoEmp}</span>
        </td>
        <td>{formatDate(patient.fecha_inicio)}</td>
        <td>{formatDate(patient.fecha_primera_toma)}</td>
        <td>{patient.cadencia_estimada_toma ? `${patient.cadencia_estimada_toma} días` : "-"}</td>
        <td>
          <StatusChip variant="success" label="Activo" />
        </td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de pacientes"
        subtitle="Consultá el historial operativo y aplicá filtros generales por paciente, prestador o tipo de empadronamiento."
        badge="Pacientes"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header agreements-header--modern">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>📋 Pacientes cargados</h2>
                <p className="muted">
                  Usá los filtros para realizar consultas generales sobre el historial de pacientes.
                </p>
              </div>
              <PanelStat count={filteredPatients.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros generales"
                description="Filtrá por nombre, ID SAP, diagnóstico, prestador o tipo de empadronamiento."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_query" span={5}>
                  <input
                    id="history_query"
                    name="history_query"
                    type="text"
                    placeholder="Nombre, apellido, ID SAP o diagnóstico"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Prestador" htmlFor="history_provider" span={4}>
                  <select
                    id="history_provider"
                    name="history_provider"
                    value={filters.provider}
                    onChange={(event) => updateFilter("provider", event.target.value)}
                  >
                    <option value="">Todos</option>
                    {providerOptions.map((provider) => (
                      <option key={provider} value={provider}>
                        {provider}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField label="Tipo empadronamiento" htmlFor="history_tipo_empadronamiento" span={3}>
                  <select
                    id="history_tipo_empadronamiento"
                    name="history_tipo_empadronamiento"
                    value={filters.tipo_empadronamiento}
                    onChange={(event) => updateFilter("tipo_empadronamiento", event.target.value)}
                  >
                    <option value="">Todos</option>
                    {EMPADRONAMIENTO_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </FormField>
              </div>

              <div className="history-toolbar-actions">
                <button type="button" className="btn-secondary" onClick={clearFilters}>
                  Limpiar filtros
                </button>
              </div>
            </div>

            <DataTable
              columns={TABLE_COLUMNS}
              rows={filteredPatients}
              renderRow={renderPatientRow}
              emptyText="No hay pacientes que coincidan con los filtros."
            />
          </section>
        </section>
      </main>
    </>
  );
}
