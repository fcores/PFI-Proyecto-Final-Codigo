import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchPatients } from "../api/patients";
import { capitalize, formatDay } from "../utils/format";

const PAGE_SIZE = 200;

const TABLE_COLUMNS = ["ID", "Paciente", "Nacimiento", "Género", "Diagnóstico", "Prestador", "Documentación"];

const ADJUNTO_CAMPOS = [
  ["hc_filename", "Historia clínica"],
  ["ap_filename", "Anatomía patológica"],
  ["img_filename", "Imágenes"],
  ["lab_filename", "Laboratorios"],
  ["receta_filename", "Receta"],
  ["otros_filename", "Otros"],
];

function adjuntosDe(patient) {
  return ADJUNTO_CAMPOS.filter(([campo]) => patient[campo]).map(([campo, label]) => `${label}: ${patient[campo]}`);
}

export default function HistorialPacientesPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [filters, setFilters] = useState({ query: "", provider: "" });

  const loadPatients = useCallback(async (offset = 0) => {
    try {
      setLoading(true);
      setError(null);
      const page = await fetchPatients({ limit: PAGE_SIZE, offset });
      setPatients((prev) => (offset === 0 ? page : [...prev, ...page]));
      setHasMore(page.length === PAGE_SIZE);
    } catch (err) {
      setError(err.message || "No se pudo cargar el padrón de pacientes.");
      if (offset === 0) setPatients([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  const providerOptions = useMemo(() => {
    const uniqueProviders = new Set(patients.map((patient) => patient.provider).filter(Boolean));
    return Array.from(uniqueProviders).sort((a, b) => a.localeCompare(b));
  }, [patients]);

  const filteredPatients = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();

    return patients.filter((patient) => {
      const searchableText = [String(patient.id), patient.first_name, patient.last_name, patient.provider, patient.treatment]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery ? searchableText.includes(normalizedQuery) : true;
      const matchesProvider = filters.provider ? patient.provider === filters.provider : true;
      return matchesQuery && matchesProvider;
    });
  }, [filters, patients]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function renderPatientRow(patient) {
    const fullName = [patient.last_name, patient.first_name].filter(Boolean).join(", ");
    const adjuntos = adjuntosDe(patient);

    return (
      <tr key={patient.id}>
        <td className="num">{patient.id}</td>
        <td>{fullName || "—"}</td>
        <td className="cell-nowrap">{formatDay(patient.birth_date)}</td>
        <td>{capitalize(patient.gender) || "—"}</td>
        <td>{patient.treatment || "—"}</td>
        <td>{patient.provider || "—"}</td>
        <td title={adjuntos.join("\n")}>
          <span className={`attach-pill${adjuntos.length === ADJUNTO_CAMPOS.length ? " is-complete" : ""}`}>
            {adjuntos.length}/{ADJUNTO_CAMPOS.length}
          </span>
        </td>
      </tr>
    );
  }

  const hayFiltros = Boolean(filters.query || filters.provider);
  const emptyText = loading
    ? "Cargando pacientes…"
    : error
      ? "No se pudo cargar el padrón."
      : hayFiltros
        ? "No hay pacientes que coincidan con los filtros."
        : "Todavía no hay pacientes registrados.";

  return (
    <>
      <TopBar
        title="Historial de pacientes"
        subtitle="Consultá el padrón y filtrá por paciente, diagnóstico o prestador."
        badge="Pacientes"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Padrón</span>
                <h2>Pacientes registrados</h2>
                <p className="muted">El ID es el que se usa al registrar una prescripción.</p>
              </div>
              <PanelStat
                count={filteredPatients.length}
                singular={hasMore ? "resultado cargado" : "resultado"}
                plural={hasMore ? "resultados cargados" : "resultados"}
              />
            </header>

            <div className="history-toolbar">
              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_query" span={6}>
                  <input
                    id="history_query"
                    name="history_query"
                    type="search"
                    placeholder="Nombre, apellido, ID o diagnóstico"
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

                <div className="form-group form-group--action field-span-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={!hayFiltros}
                    onClick={() => setFilters({ query: "", provider: "" })}
                  >
                    Limpiar
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <p className="status error status--block" role="alert">
                {error}{" "}
                <button type="button" className="btn-link" onClick={() => loadPatients(0)}>
                  Reintentar
                </button>
              </p>
            )}

            <DataTable columns={TABLE_COLUMNS} rows={filteredPatients} renderRow={renderPatientRow} emptyText={emptyText} />

            {hasMore && (
              <div className="load-more">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => loadPatients(patients.length)}
                  disabled={loading}
                >
                  {loading ? "Cargando…" : "Cargar más"}
                </button>
              </div>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
