import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchPrescriptions } from "../api/prescriptions";
import { ESTADO_VARIANT } from "../constants/estadoVariant";
import { shortHash } from "../utils/shortHash";

const TABLE_COLUMNS = [
  "Código",
  "Paciente SAP",
  "Diagnóstico",
  "Estadio",
  "Régimen",
  "Dosis (mg/m²)",
  "Estado",
  "Confianza",
  "Hash (tx)",
];

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
        presc.id_regimen,
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

  function formatConfianza(presc) {
    const p = presc.validacion?.probabilidad_concordante;
    if (p == null) return "—";
    const nivel = presc.validacion?.nivel_confianza || "";
    return `${(Number(p) * 100).toFixed(0)}%${nivel ? ` (${nivel})` : ""}`;
  }

  function renderRow(presc) {
    return (
      <tr key={presc.id}>
        <td>{presc.prescription_code}</td>
        <td>{presc.patient_sap_id}</td>
        <td>{presc.diagnostico_cie10}</td>
        <td>{presc.estadio}</td>
        <td>{presc.id_regimen || presc.esquema}</td>
        <td>{presc.dosis_mg_m2}</td>
        <td>
          <StatusChip
            variant={ESTADO_VARIANT[presc.validacion.estado] || "neutral"}
            label={presc.validacion.estado}
          />
        </td>
        <td>{formatConfianza(presc)}</td>
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
            <header className="agreements-header">
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
                title="Filtros"
                description="Buscá por código, paciente, diagnóstico o régimen."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_presc_query" span={6}>
                  <input
                    id="history_presc_query"
                    type="text"
                    placeholder="Código, paciente, diagnóstico..."
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>
                <FormField label="Estado" htmlFor="history_presc_estado" span={3}>
                  <select
                    id="history_presc_estado"
                    value={filters.estado}
                    onChange={(event) => updateFilter("estado", event.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="APROBADO">APROBADO</option>
                    <option value="REVISION">REVISION</option>
                    <option value="RECHAZADO">RECHAZADO</option>
                  </select>
                </FormField>
                <FormField label=" " htmlFor="history_presc_clear" span={3}>
                  <button id="history_presc_clear" type="button" className="btn btn-secondary" onClick={clearFilters}>
                    Limpiar
                  </button>
                </FormField>
              </div>
            </div>

            <DataTable columns={TABLE_COLUMNS} rows={filtered} renderRow={renderRow} emptyMessage="Sin prescripciones." />
          </section>
        </section>
      </main>
    </>
  );
}
