import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import TopBar from "../components/TopBar";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { useAuth } from "../auth/AuthContext";
import { fetchPrescriptions } from "../api/prescriptions";
import { ESTADO_VARIANT, ESTADO_LABEL, estadoLabel, mlLabel } from "../constants/estadoVariant";
import { formatDate } from "../utils/formatDate";

const TABLE_COLUMNS = [
  "Código",
  "Fecha",
  "Paciente ID",
  "Diagnóstico",
  "Estadio",
  "Régimen",
  "Estado",
  "Veredicto ML",
  "Confianza",
];

const ESTADOS_FILTRO = ["PENDIENTE_AUDITORIA", "EN_REVISION", "APROBADA", "RECHAZADA"];
const ROLES_AUDITORIA = ["auditor", "super_admin"];

export default function HistorialPrescripcionesPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [prescriptions, setPrescriptions] = useState([]);
  const [bookmark, setBookmark] = useState(null);
  const [estado, setEstado] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // El auditor abre el caso (puede dictaminar); el prescriptor, la trazabilidad.
  const detalleDe = useCallback(
    (presc) =>
      ROLES_AUDITORIA.includes(user?.role)
        ? `/auditoria/caso/${presc.prescription_id}`
        : `/trazabilidad?id=${encodeURIComponent(presc.prescription_id)}`,
    [user?.role],
  );

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
        clinical.medico_prescriptor,
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
    const destino = detalleDe(presc);
    return (
      <tr key={presc.prescription_id} className="row-link" onClick={() => navigate(destino)}>
        <td>
          <Link to={destino} className="cell-link" onClick={(e) => e.stopPropagation()}>
            {presc.prescription_code}
          </Link>
        </td>
        <td className="cell-nowrap">{formatDate(presc.created_at)}</td>
        <td className="num">{clinical.patient_id}</td>
        <td>{clinical.diagnostico_cie10}</td>
        <td>{clinical.estadio}</td>
        <td title={clinical.esquema || ""}>{clinical.id_regimen || clinical.esquema}</td>
        <td>
          <StatusChip variant={ESTADO_VARIANT[presc.estado] || "neutral"} label={estadoLabel(presc.estado)} />
        </td>
        <td>
          <StatusChip variant={ESTADO_VARIANT[presc.ml?.estado] || "neutral"} label={mlLabel(presc.ml?.estado)} />
        </td>
        <td className="cell-nowrap">{formatConfianza(presc)}</td>
      </tr>
    );
  }

  const emptyText = loading
    ? "Cargando desde la red Fabric…"
    : error
      ? "No se pudieron cargar las prescripciones."
      : query || estado
        ? "No hay prescripciones que coincidan con los filtros."
        : "Todavía no hay prescripciones registradas.";

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
                <h2>Prescripciones en la blockchain</h2>
                <p className="muted">
                  El filtro por estado consulta la red; la búsqueda filtra los resultados ya cargados. Hacé clic en
                  una fila para ver el detalle.
                </p>
              </div>
              <PanelStat
                count={filtered.length}
                singular={bookmark ? "resultado cargado" : "resultado"}
                plural={bookmark ? "resultados cargados" : "resultados"}
              />
            </header>

            <div className="history-toolbar">
              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_presc_query" span={6}>
                  <input
                    id="history_presc_query"
                    type="search"
                    placeholder="Código, paciente, diagnóstico, régimen o médico"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </FormField>
                <FormField label="Estado" htmlFor="history_presc_estado" span={4}>
                  <select id="history_presc_estado" value={estado} onChange={(event) => setEstado(event.target.value)}>
                    <option value="">Todos</option>
                    {ESTADOS_FILTRO.map((value) => (
                      <option key={value} value={value}>
                        {ESTADO_LABEL[value]}
                      </option>
                    ))}
                  </select>
                </FormField>
                <div className="form-group form-group--action field-span-2">
                  <button
                    type="button"
                    className="btn-secondary"
                    disabled={!query && !estado}
                    onClick={() => {
                      setQuery("");
                      setEstado("");
                    }}
                  >
                    Limpiar
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <p className="status error status--block" role="alert">
                {error}{" "}
                <button type="button" className="btn-link" onClick={() => load(estado)}>
                  Reintentar
                </button>
              </p>
            )}

            <DataTable columns={TABLE_COLUMNS} rows={filtered} renderRow={renderRow} emptyText={emptyText} />

            {bookmark && (
              <div className="load-more">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => load(estado, bookmark, true)}
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
