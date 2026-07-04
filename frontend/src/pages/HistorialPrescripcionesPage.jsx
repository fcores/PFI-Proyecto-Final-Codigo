import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchPrescriptions } from "../api/prescriptions";

const TABLE_COLUMNS = [
  "Código",
  "Paciente SAP",
  "Diagnóstico",
  "Estadio",
  "Esquema",
  "Dosis (mg/m²)",
  "Estado",
  "Hash (tx)",
];

const ESTADO_VARIANT = {
  APROBADO: "success",
  REVISION: "warning",
  RECHAZADO: "error",
};

function shortHash(hash) {
  if (!hash) return "—";
  return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

export default function HistorialPrescripcionesPage() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [filters, setFilters] = useState({ query: "", estado: "" });

  const load = useCallback(async () => {
    try {
      setPrescriptions(await fetchPrescriptions());
    } catch {
      setPrescriptions([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();
    const normalizedEstado = filters.estado.trim().toUpperCase();

    return prescriptions.filter((presc) => {
      const searchableText = [
        presc.prescription_code,
        presc.patient_sap_id,
        presc.diagnostico_cie10,
        presc.esquema,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery ? searchableText.includes(normalizedQuery) : true;
      const matchesEstado = normalizedEstado ? presc.validacion.estado === normalizedEstado : true;

      return matchesQuery && matchesEstado;
    });
  }, [filters, prescriptions]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({ query: "", estado: "" });
  }

  function renderRow(presc) {
    return (
      <tr key={presc.id}>
        <td>{presc.prescription_code}</td>
        <td>{presc.patient_sap_id}</td>
        <td>{presc.diagnostico_cie10}</td>
        <td>{presc.estadio}</td>
        <td>{presc.esquema}</td>
        <td>{presc.dosis_mg_m2}</td>
        <td>
          <StatusChip
            variant={ESTADO_VARIANT[presc.validacion.estado] || "neutral"}
            label={presc.validacion.estado}
          />
        </td>
        <td title={presc.blockchain_tx_id || ""}>
          <code>{shortHash(presc.blockchain_tx_id)}</code>
        </td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de prescripciones"
        subtitle="Consultá las prescripciones registradas, su resultado de validación y su transacción en blockchain."
        badge="Prescripciones"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header agreements-header--modern">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>🧬 Prescripciones registradas</h2>
                <p className="muted">
                  Filtrá por texto o por estado de validación (APROBADO, REVISION, RECHAZADO).
                </p>
              </div>
              <PanelStat count={filtered.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros generales"
                description="Buscá por código, paciente, diagnóstico o esquema; o filtrá por estado."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_presc_query" span={8}>
                  <input
                    id="history_presc_query"
                    name="history_presc_query"
                    type="text"
                    placeholder="Código, paciente, diagnóstico o esquema"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Estado" htmlFor="history_presc_estado" span={4}>
                  <select
                    id="history_presc_estado"
                    name="history_presc_estado"
                    value={filters.estado}
                    onChange={(event) => updateFilter("estado", event.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="APROBADO">Aprobado</option>
                    <option value="REVISION">Revisión</option>
                    <option value="RECHAZADO">Rechazado</option>
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
              rows={filtered}
              renderRow={renderRow}
              emptyText="No hay prescripciones que coincidan con los filtros."
            />
          </section>
        </section>
      </main>
    </>
  );
}
