import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchMedications } from "../api/medications";
import { formatCurrency, formatNumber } from "../utils/format";

const TABLE_COLUMNS = [
  "Código",
  "Descripción",
  "Monodroga",
  "Potencia",
  "Presentación",
  "Laboratorio",
  "Conservación",
  "Vía",
  "EAN",
  "Troquel",
  "Precio",
];

const CONSERVACION_OPTIONS = [
  { value: "seco", label: "Seco" },
  { value: "frio", label: "Frío" },
];

function formatConservation(value) {
  if (!value) return "—";
  return value === "frio" ? "Frío" : "Seco";
}

function formatPotencia(medication) {
  if (medication.potencia_mg == null) return "—";
  return `${formatNumber(medication.potencia_mg)} ${medication.unidad_potencia || ""}`.trim();
}

const EMPTY_FILTERS = { query: "", tipo_conservacion: "", monodroga: "" };

export default function HistorialMedicamentosPage() {
  const [medications, setMedications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const loadMedications = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setMedications(await fetchMedications());
    } catch (err) {
      setError(err.message || "No se pudo cargar el catálogo de medicamentos.");
      setMedications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMedications();
  }, [loadMedications]);

  const monodrogaOptions = useMemo(
    () => Array.from(new Set(medications.map((m) => m.monodroga).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
    [medications],
  );

  const filteredMedications = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();

    return medications.filter((medication) => {
      const searchableText = [
        medication.codigo,
        medication.descripcion,
        medication.ean,
        medication.codigo_alfabeta,
        medication.laboratorio,
        medication.monodroga,
        medication.tamano_dimension,
        medication.via_administracion,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery ? searchableText.includes(normalizedQuery) : true;
      const matchesConservacion = filters.tipo_conservacion
        ? medication.tipo_conservacion === filters.tipo_conservacion
        : true;
      const matchesMonodroga = filters.monodroga ? medication.monodroga === filters.monodroga : true;

      return matchesQuery && matchesConservacion && matchesMonodroga;
    });
  }, [filters, medications]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function renderMedicationRow(medication) {
    return (
      <tr key={medication.id}>
        <td className="cell-nowrap">{medication.codigo}</td>
        <td className="cell-text">{medication.descripcion}</td>
        <td>{medication.monodroga}</td>
        <td className="cell-nowrap">{formatPotencia(medication)}</td>
        <td>{medication.tamano_dimension}</td>
        <td>{medication.laboratorio}</td>
        <td>{formatConservation(medication.tipo_conservacion)}</td>
        <td>{medication.via_administracion || "—"}</td>
        <td className="cell-nowrap">{medication.ean}</td>
        <td className="cell-nowrap">{medication.codigo_alfabeta}</td>
        <td className="num cell-nowrap">{formatCurrency(medication.precio)}</td>
      </tr>
    );
  }

  const hayFiltros = Boolean(filters.query || filters.tipo_conservacion || filters.monodroga);
  const emptyText = loading
    ? "Cargando catálogo…"
    : error
      ? "No se pudo cargar el catálogo."
      : hayFiltros
        ? "No hay medicamentos que coincidan con los filtros."
        : "Todavía no hay medicamentos cargados.";

  return (
    <>
      <TopBar
        title="Historial de medicamentos"
        subtitle="Consultá el maestro de materiales y filtrá por descripción, monodroga, laboratorio o conservación."
        badge="Medicamentos"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Catálogo</span>
                <h2>Medicamentos cargados</h2>
                <p className="muted">El precio de venta al público alimenta el costeo de los regímenes.</p>
              </div>
              <PanelStat count={filteredMedications.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_medication_query" span={4}>
                  <input
                    id="history_medication_query"
                    name="history_medication_query"
                    type="search"
                    placeholder="Código, descripción, EAN, laboratorio…"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Monodroga" htmlFor="history_medication_monodroga" span={3}>
                  <select
                    id="history_medication_monodroga"
                    value={filters.monodroga}
                    onChange={(event) => updateFilter("monodroga", event.target.value)}
                  >
                    <option value="">Todas</option>
                    {monodrogaOptions.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField label="Conservación" htmlFor="history_medication_conservation" span={3}>
                  <select
                    id="history_medication_conservation"
                    value={filters.tipo_conservacion}
                    onChange={(event) => updateFilter("tipo_conservacion", event.target.value)}
                  >
                    <option value="">Todas</option>
                    {CONSERVACION_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </FormField>

                <div className="form-group form-group--action field-span-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={!hayFiltros}
                    onClick={() => setFilters(EMPTY_FILTERS)}
                  >
                    Limpiar
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <p className="status error status--block" role="alert">
                {error}{" "}
                <button type="button" className="btn-link" onClick={loadMedications}>
                  Reintentar
                </button>
              </p>
            )}

            <DataTable
              columns={TABLE_COLUMNS}
              rows={filteredMedications}
              renderRow={renderMedicationRow}
              emptyText={emptyText}
            />
          </section>
        </section>
      </main>
    </>
  );
}
