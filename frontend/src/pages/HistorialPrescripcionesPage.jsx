import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchPrescriptions } from "../api/prescriptions";
import { ESTADO_VARIANT, ESTADO_LABEL } from "../constants/estadoVariant";
import { shortHash } from "../utils/shortHash";

const TABLE_COLUMNS = [
  "Código",
  "Paciente ID",
  "Diagnóstico",
  "Estadio",
  "Régimen",
  "Estado on-chain",
  "Veredicto ML",
  "Confianza",
  "Hash",
];

const ESTADOS_FILTRO = ["PENDIENTE_AUDITORIA", "EN_REVISION", "APROBADA", "RECHAZADA"];

export default function HistorialPrescripcionesPage() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [bookmark, setBookmark] = useState(null);
  const [estado, setEstado] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (targetEstado, currentBookmark = "", append = false) => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchPrescriptions({ estado: targetEstado, bookmark: currentBookmark });
      setPrescriptions((prev) => (append ? [...prev, ...data.prescriptions] : data.prescriptions));
      setBookmark(data.bookmark);
    } catch (err) {
      setError(err.message || "No se pudo leer el historial desde la red blockchain.");
      if (!append) setPrescriptions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(estado);
  }, [estado, load]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return prescriptions;
    return prescriptions.filter((presc) => {
      const clinical = presc.clinical || {};
      const searchableText = [
        presc.prescription_code,
        String(clinical.patient_id || ""),
        clinical.diagnostico_cie10,
        clinical.esquema,
        clinical.id_regimen,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return searchableText.includes(normalizedQuery);
    });
  }, [query, prescriptions]);

  function formatConfianza(presc) {
    const p = presc.ml?.probabilidad_concordante;
    if (p == null) return "—";
    const nivel = presc.ml?.nivel_confianza || "";
    return `${(Number(p) * 100).toFixed(0)}%${nivel ? ` (${nivel})` : ""}`;
  }

  function renderRow(presc) {
    const clinical = presc.clinical || {};
    return (
      <tr key={presc.prescription_id}>
        <td>{presc.prescription_code}</td>
        <td>{clinical.patient_id}</td>
        <td>{clinical.diagnostico_cie10}</td>
        <td>{clinical.estadio}</td>
        <td>{clinical.id_regimen || clinical.esquema}</td>
        <td>
          <StatusChip
            variant={ESTADO_VARIANT[presc.estado] || "neutral"}
            label={ESTADO_LABEL[presc.estado] || presc.estado}
          />
        </td>
        <td>
          <StatusChip
            variant={ESTADO_VARIANT[presc.ml?.estado] || "neutral"}
            label={presc.ml?.estado || "—"}
          />
        </td>
        <td>{formatConfianza(presc)}</td>
        <td title={presc.current_hash || ""}>
          <code>{shortHash(presc.current_hash)}</code>
        </td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de prescripciones"
        subtitle="Prescripciones leídas del world state de Hyperledger Fabric: inmutables y visibles para las tres organizaciones."
        badge="Prescripciones"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>🧬 Prescripciones en la blockchain</h2>
                <p className="muted">
                  Filtrá por estado del ciclo de auditoría o buscá dentro de los resultados cargados.
                </p>
              </div>
              <PanelStat count={filtered.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros"
                description="El filtro por estado consulta la red; la búsqueda por texto filtra los resultados ya cargados."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_presc_query" span={6}>
                  <input
                    id="history_presc_query"
                    type="text"
                    placeholder="Código, paciente, diagnóstico..."
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </FormField>
                <FormField label="Estado on-chain" htmlFor="history_presc_estado" span={3}>
                  <select
                    id="history_presc_estado"
                    value={estado}
                    onChange={(event) => setEstado(event.target.value)}
                  >
                    <option value="">Todos</option>
                    {ESTADOS_FILTRO.map((value) => (
                      <option key={value} value={value}>{ESTADO_LABEL[value]}</option>
                    ))}
                  </select>
                </FormField>
                <FormField label=" " htmlFor="history_presc_clear" span={3}>
                  <button
                    id="history_presc_clear"
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setQuery("");
                      setEstado("");
                    }}
                  >
                    Limpiar
                  </button>
                </FormField>
              </div>
            </div>

            {error && <p className="status error">{error}</p>}

            <DataTable
              columns={TABLE_COLUMNS}
              rows={filtered}
              renderRow={renderRow}
              emptyMessage={loading ? "Cargando desde la red Fabric..." : "Sin prescripciones."}
            />

            {bookmark && (
              <div style={{ textAlign: "center", padding: "12px" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => load(estado, bookmark, true)}
                  disabled={loading}
                >
                  {loading ? "Cargando..." : "Cargar más"}
                </button>
              </div>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
