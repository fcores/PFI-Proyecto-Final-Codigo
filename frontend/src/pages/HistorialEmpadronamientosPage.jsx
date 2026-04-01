import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchEnrollments } from "../api/enrollments";

const TABLE_COLUMNS = [
  "ID Emp.",
  "Tipo",
  "Fecha carga",
  "Diagnóstico",
  "Medicamentos",
];

const ENROLLMENT_OPTIONS = [
  { value: "tipo-a", label: "Tipo A" },
  { value: "tipo-b", label: "Tipo B" },
];

function getTipoLabel(tipo) {
  return ENROLLMENT_OPTIONS.find((option) => option.value === tipo)?.label ?? tipo;
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  return date.toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getDateOnly(value) {
  return value ? String(value).slice(0, 10) : "";
}

export default function HistorialEmpadronamientosPage() {
  const [enrollments, setEnrollments] = useState([]);
  const [filters, setFilters] = useState({
    query: "",
    tipo: "",
    medication: "",
    fecha_desde: "",
    fecha_hasta: "",
  });

  const loadEnrollments = useCallback(async () => {
    try {
      const [tipoA, tipoB] = await Promise.all([
        fetchEnrollments("tipo-a"),
        fetchEnrollments("tipo-b"),
      ]);

      setEnrollments([
        ...tipoA.map((item) => ({ ...item, tipo: "tipo-a" })),
        ...tipoB.map((item) => ({ ...item, tipo: "tipo-b" })),
      ]);
    } catch {
      setEnrollments([]);
    }
  }, []);

  useEffect(() => {
    loadEnrollments();
  }, [loadEnrollments]);

  const filteredEnrollments = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();
    const normalizedMedication = filters.medication.trim().toLowerCase();

    return enrollments.filter((enrollment) => {
      const createdAt = getDateOnly(enrollment.created_at);
      const searchableText = [
        enrollment.enrollment_code,
        enrollment.diagnostico,
        enrollment.tipo,
        ...(enrollment.medications ?? []),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery
        ? searchableText.includes(normalizedQuery)
        : true;
      const matchesTipo = filters.tipo ? enrollment.tipo === filters.tipo : true;
      const matchesMedication = normalizedMedication
        ? (enrollment.medications ?? []).some((medication) =>
            medication.toLowerCase().includes(normalizedMedication),
          )
        : true;
      const matchesFechaDesde = filters.fecha_desde
        ? createdAt >= filters.fecha_desde
        : true;
      const matchesFechaHasta = filters.fecha_hasta
        ? createdAt <= filters.fecha_hasta
        : true;

      return (
        matchesQuery &&
        matchesTipo &&
        matchesMedication &&
        matchesFechaDesde &&
        matchesFechaHasta
      );
    });
  }, [enrollments, filters]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      query: "",
      tipo: "",
      medication: "",
      fecha_desde: "",
      fecha_hasta: "",
    });
  }

  async function exportToExcel() {
    const XLSX = await import("xlsx");
    const rows = filteredEnrollments.map((enrollment) => ({
      "ID Empadronamiento": enrollment.enrollment_code,
      Tipo: getTipoLabel(enrollment.tipo),
      "Fecha carga": formatDateTime(enrollment.created_at),
      Diagnóstico: enrollment.diagnostico,
      Medicamentos: (enrollment.medications ?? []).join(", "),
    }));

    const worksheet = XLSX.utils.json_to_sheet(rows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Empadronamientos");
    XLSX.writeFile(workbook, "historial-empadronamientos.xlsx");
  }

  function renderEnrollmentRow(enrollment) {
    return (
      <tr key={`${enrollment.tipo}-${enrollment.id}`}>
        <td>
          <span className="enrollment-code-chip">{enrollment.enrollment_code}</span>
        </td>
        <td>{getTipoLabel(enrollment.tipo)}</td>
        <td>{formatDateTime(enrollment.created_at)}</td>
        <td>{enrollment.diagnostico}</td>
        <td>
          <div className="med-tags">
            {(enrollment.medications ?? []).map((medication) => (
              <span key={`${enrollment.enrollment_code}-${medication}`} className="med-tag">
                {medication}
              </span>
            ))}
          </div>
        </td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de empadronamientos"
        subtitle="Consultá los empadronamientos cargados y aplicá filtros por tipo, fecha, diagnóstico o medicamento."
        badge="Empadronamientos"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header agreements-header--modern">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>📝 Empadronamientos cargados</h2>
                <p className="muted">
                  Usá los filtros para realizar consultas generales sobre los registros de Tipo A y Tipo B.
                </p>
              </div>
              <PanelStat count={filteredEnrollments.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros generales"
                description="Filtrá por código, tipo, rango de fechas, diagnóstico o medicamento."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_enrollment_query" span={4}>
                  <input
                    id="history_enrollment_query"
                    name="history_enrollment_query"
                    type="text"
                    placeholder="Código, diagnóstico o texto general"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Tipo empadronamiento" htmlFor="history_enrollment_tipo" span={2}>
                  <select
                    id="history_enrollment_tipo"
                    name="history_enrollment_tipo"
                    value={filters.tipo}
                    onChange={(event) => updateFilter("tipo", event.target.value)}
                  >
                    <option value="">Todos</option>
                    {ENROLLMENT_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField label="Medicamento" htmlFor="history_enrollment_medication" span={2}>
                  <input
                    id="history_enrollment_medication"
                    name="history_enrollment_medication"
                    type="text"
                    placeholder="Filtrar por medicamento"
                    value={filters.medication}
                    onChange={(event) => updateFilter("medication", event.target.value)}
                  />
                </FormField>

                <FormField label="Fecha desde" htmlFor="history_enrollment_date_from" span={2}>
                  <input
                    id="history_enrollment_date_from"
                    name="history_enrollment_date_from"
                    type="date"
                    value={filters.fecha_desde}
                    onChange={(event) => updateFilter("fecha_desde", event.target.value)}
                  />
                </FormField>

                <FormField label="Fecha hasta" htmlFor="history_enrollment_date_to" span={2}>
                  <input
                    id="history_enrollment_date_to"
                    name="history_enrollment_date_to"
                    type="date"
                    value={filters.fecha_hasta}
                    onChange={(event) => updateFilter("fecha_hasta", event.target.value)}
                  />
                </FormField>
              </div>

              <div className="history-toolbar-actions">
                <button type="button" className="btn-secondary" onClick={() => void exportToExcel()}>
                  Exportar Excel
                </button>
                <button type="button" className="btn-secondary" onClick={clearFilters}>
                  Limpiar filtros
                </button>
              </div>
            </div>

            <DataTable
              columns={TABLE_COLUMNS}
              rows={filteredEnrollments}
              renderRow={renderEnrollmentRow}
              emptyText="No hay empadronamientos que coincidan con los filtros."
            />
          </section>
        </section>
      </main>
    </>
  );
}
