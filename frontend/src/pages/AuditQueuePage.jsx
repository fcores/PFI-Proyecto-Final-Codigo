import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import TopBar from "../components/TopBar";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchAuditQueue } from "../api/audit";
import { ESTADO_VARIANT, ESTADO_LABEL } from "../constants/estadoVariant";
import { formatDate } from "../utils/formatDate";

const TABLE_COLUMNS = [
  "Código",
  "Paciente ID",
  "Diagnóstico",
  "Estadio",
  "Esquema",
  "Veredicto ML",
  "Confianza",
  "Fecha",
];

const TABS = [
  { estado: "PENDIENTE_AUDITORIA", label: "Pendientes" },
  { estado: "EN_REVISION", label: "En revisión" },
];

export default function AuditQueuePage() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState("PENDIENTE_AUDITORIA");
  const [items, setItems] = useState([]);
  const [bookmark, setBookmark] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  const load = useCallback(
    async (targetEstado, currentBookmark = "", append = false) => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchAuditQueue({ estado: targetEstado, bookmark: currentBookmark });
        setItems((prev) => (append ? [...prev, ...data.prescriptions] : data.prescriptions));
        setBookmark(data.bookmark);
      } catch (err) {
        setError(err.message || "No se pudo leer la cola desde la red blockchain.");
        if (!append) setItems([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    load(estado);
  }, [estado, load]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((presc) => {
      const clinical = presc.clinical || {};
      const searchable = [
        presc.prescription_code,
        String(clinical.patient_id || ""),
        clinical.diagnostico_cie10,
        clinical.esquema,
        clinical.id_regimen,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return searchable.includes(normalized);
    });
  }, [items, query]);

  function formatConfianza(presc) {
    const p = presc.ml?.probabilidad_concordante;
    if (p == null) return "—";
    return `${(Number(p) * 100).toFixed(0)}%`;
  }

  function renderRow(presc) {
    const clinical = presc.clinical || {};
    return (
      <tr
        key={presc.prescription_id}
        onClick={() => navigate(`/auditoria/caso/${presc.prescription_id}`)}
        style={{ cursor: "pointer" }}
      >
        <td>{presc.prescription_code}</td>
        <td>{clinical.patient_id}</td>
        <td>{clinical.diagnostico_cie10}</td>
        <td>{clinical.estadio}</td>
        <td>{clinical.esquema}</td>
        <td>
          <StatusChip
            variant={ESTADO_VARIANT[presc.ml?.estado] || "neutral"}
            label={presc.ml?.estado || "—"}
          />
        </td>
        <td>{formatConfianza(presc)}</td>
        <td>{formatDate(presc.created_at)}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Cola de Auditoría"
        subtitle="Toda prescripción nace pendiente de auditoría en la blockchain; el veredicto del modelo es soporte de decisión."
        badge="Auditoría"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Auditoría</span>
                <h2>{ESTADO_LABEL[estado]}</h2>
                <p className="muted">
                  Prescripciones en estado {ESTADO_LABEL[estado].toLowerCase()} leídas de la red Fabric (FIFO).
                </p>
              </div>
              <PanelStat count={filtered.length} singular="caso" plural="casos" />
            </header>

            <div className="history-toolbar">
              <div className="form-grid history-filters">
                <FormField label="Cola" htmlFor="audit_queue_tab" span={4}>
                  <select
                    id="audit_queue_tab"
                    value={estado}
                    onChange={(event) => setEstado(event.target.value)}
                  >
                    {TABS.map((tab) => (
                      <option key={tab.estado} value={tab.estado}>{tab.label}</option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Buscar" htmlFor="audit_queue_query" span={6}>
                  <input
                    id="audit_queue_query"
                    type="text"
                    placeholder="Código, paciente, diagnóstico o régimen"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </FormField>
                <FormField label=" " htmlFor="audit_queue_reload" span={2}>
                  <button
                    id="audit_queue_reload"
                    type="button"
                    className="btn-secondary"
                    onClick={() => load(estado)}
                    disabled={loading}
                  >
                    Actualizar
                  </button>
                </FormField>
              </div>
            </div>

            {error && <p className="status error">{error}</p>}

            <DataTable
              columns={TABLE_COLUMNS}
              rows={filtered}
              renderRow={renderRow}
              emptyText={loading ? "Cargando desde la red Fabric..." : "No hay prescripciones en esta cola."}
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
