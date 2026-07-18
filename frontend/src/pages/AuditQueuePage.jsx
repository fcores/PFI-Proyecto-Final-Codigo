import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchAuditQueue } from "../api/audit";

const TABLE_COLUMNS = [
  "ID Caso",
  "Código Prescripción",
  "Paciente SAP",
  "Diagnóstico",
  "Estadio",
  "Esquema",
  "Estado Validación",
  "Fecha",
];

const ESTADO_VARIANT = {
  APROBADO: "success",
  RECHAZADO: "error",
  PENDIENTE_DOCS: "warning",
  REVISION: "info",
  pendiente: "neutral",
};

function formatDate(raw) {
  if (!raw) return "—";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export default function AuditQueuePage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [filters, setFilters] = useState({ query: "", estado: "" });

  const load = useCallback(async () => {
    try {
      setCases(await fetchAuditQueue());
    } catch {
      setCases([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();
    const normalizedEstado = filters.estado.trim();

    return cases.filter((item) => {
      const searchableText = [
        item.prescription_code,
        item.patient_sap_id,
        item.diagnostico_cie10,
        item.esquema,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery
        ? searchableText.includes(normalizedQuery)
        : true;
      const matchesEstado = normalizedEstado
        ? item.estado_validacion === normalizedEstado
        : true;

      return matchesQuery && matchesEstado;
    });
  }, [filters, cases]);

  const stats = useMemo(() => {
    const total = cases.length;
    const pending = cases.filter(
      (c) => c.estado_validacion === "pendiente" || c.estado_validacion === "REVISION"
    ).length;
    const reviewed = cases.filter(
      (c) => c.estado_validacion === "APROBADO" || c.estado_validacion === "RECHAZADO"
    ).length;
    return { total, pending, reviewed };
  }, [cases]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({ query: "", estado: "" });
  }

  function handleRowClick(caseId) {
    navigate(`/auditoria/caso/${caseId}`);
  }

  function renderRow(item) {
    return (
      <tr
        key={item.id}
        onClick={() => handleRowClick(item.id)}
        style={{ cursor: "pointer" }}
      >
        <td>{item.id}</td>
        <td>{item.prescription_code}</td>
        <td>{item.patient_sap_id}</td>
        <td>{item.diagnostico_cie10}</td>
        <td>{item.estadio}</td>
        <td>{item.esquema}</td>
        <td>
          <StatusChip
            variant={ESTADO_VARIANT[item.estado_validacion] || "neutral"}
            label={item.estado_validacion}
          />
        </td>
        <td>{formatDate(item.fecha)}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Cola de Auditoría"
        subtitle="Revisá las prescripciones pendientes de dictamen por el equipo auditor."
        badge="Auditoría"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header agreements-header--modern">
              <div>
                <span className="card-eyebrow">Auditoría</span>
                <h2>Casos pendientes de revisión</h2>
                <p className="muted">
                  Filtrá por paciente SAP, código de prescripción o estado de validación.
                </p>
              </div>
              <div style={{ display: "flex", gap: "12px" }}>
                <PanelStat count={stats.total} singular="total" />
                <PanelStat count={stats.pending} singular="pendiente" plural="pendientes" />
                <PanelStat count={stats.reviewed} singular="revisado" plural="revisados" />
              </div>
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Filtros"
                title="Buscar casos"
                description="Buscá por paciente SAP, código de prescripción o filtrá por estado."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="audit_queue_query" span={8}>
                  <input
                    id="audit_queue_query"
                    name="audit_queue_query"
                    type="text"
                    placeholder="Paciente SAP o código de prescripción"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Estado" htmlFor="audit_queue_estado" span={4}>
                  <select
                    id="audit_queue_estado"
                    name="audit_queue_estado"
                    value={filters.estado}
                    onChange={(event) => updateFilter("estado", event.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="pendiente">Pendiente</option>
                    <option value="REVISION">Revisión</option>
                    <option value="APROBADO">Aprobado</option>
                    <option value="RECHAZADO">Rechazado</option>
                    <option value="PENDIENTE_DOCS">Pendiente Docs</option>
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
              emptyText="No hay casos de auditoría que coincidan con los filtros."
            />
          </section>
        </section>
      </main>
    </>
  );
}
