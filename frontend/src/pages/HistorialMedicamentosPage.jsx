import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchMedications } from "../api/medications";

const TABLE_COLUMNS = [
  "Código",
  "Descripción",
  "EAN",
  "Troquel",
  "Conservación",
  "Laboratorio",
  "Monodroga",
  "Tamaño",
  "Potencia",
  "Unidad",
  "Precio",
  "Vía",
];

const CONSERVACION_OPTIONS = [
  { value: "seco", label: "Seco" },
  { value: "frio", label: "Frío" },
];

function formatConservation(value) {
  if (!value) return "-";
  return value === "frio" ? "Frío" : "Seco";
}

export default function HistorialMedicamentosPage() {
  const [medications, setMedications] = useState([]);
  const [filters, setFilters] = useState({
    query: "",
    tipo_conservacion: "",
    codigo: "",
    monodroga: "",
  });

  const loadMedications = useCallback(async () => {
    try {
      setMedications(await fetchMedications());
    } catch {
      setMedications([]);
    }
  }, []);

  useEffect(() => {
    loadMedications();
  }, [loadMedications]);

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
        medication.tipo_conservacion,
        medication.unidad_potencia,
        medication.via_administracion,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery
        ? searchableText.includes(normalizedQuery)
        : true;
      const matchesConservacion = filters.tipo_conservacion
        ? medication.tipo_conservacion === filters.tipo_conservacion
        : true;
      const matchesCodigo = filters.codigo
        ? (medication.codigo || "").toLowerCase().includes(filters.codigo.trim().toLowerCase())
        : true;
      const matchesMonodroga = filters.monodroga
        ? (medication.monodroga || "").toLowerCase().includes(filters.monodroga.trim().toLowerCase())
        : true;

      return matchesQuery && matchesConservacion && matchesCodigo && matchesMonodroga;
    });
  }, [filters, medications]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      query: "",
      tipo_conservacion: "",
      codigo: "",
      monodroga: "",
    });
  }

  function renderMedicationRow(medication) {
    return (
      <tr key={medication.id}>
        <td>{medication.codigo}</td>
        <td>{medication.descripcion}</td>
        <td>{medication.ean}</td>
        <td>{medication.codigo_alfabeta}</td>
        <td>{formatConservation(medication.tipo_conservacion)}</td>
        <td>{medication.laboratorio}</td>
        <td>{medication.monodroga}</td>
        <td>{medication.tamano_dimension}</td>
        <td>{medication.potencia_mg ?? "-"}</td>
        <td>{medication.unidad_potencia || "-"}</td>
        <td>{medication.precio ?? "-"}</td>
        <td>{medication.via_administracion || "-"}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de medicamentos"
        subtitle="Consultá el maestro de materiales y filtrá por código, monodroga, laboratorio o conservación."
        badge="Medicamentos"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>Medicamentos cargados</h2>
                <p className="muted">
                  Usá los filtros para buscar materiales por descripción, códigos, monodroga y conservación.
                </p>
              </div>
              <PanelStat count={filteredMedications.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros generales"
                description="Buscá por descripción, EAN, código MED-XXXX, monodroga o laboratorio."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_medication_query" span={6}>
                  <input
                    id="history_medication_query"
                    name="history_medication_query"
                    type="text"
                    placeholder="Descripción, EAN, laboratorio..."
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Conservación" htmlFor="history_medication_conservation" span={2}>
                  <select
                    id="history_medication_conservation"
                    name="history_medication_conservation"
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

                <FormField label="Código" htmlFor="history_medication_codigo" span={2}>
                  <input
                    id="history_medication_codigo"
                    name="history_medication_codigo"
                    type="text"
                    placeholder="MED-0001"
                    value={filters.codigo}
                    onChange={(event) => updateFilter("codigo", event.target.value)}
                  />
                </FormField>

                <FormField label="Monodroga" htmlFor="history_medication_monodroga" span={2}>
                  <input
                    id="history_medication_monodroga"
                    name="history_medication_monodroga"
                    type="text"
                    placeholder="oxaliplatino..."
                    value={filters.monodroga}
                    onChange={(event) => updateFilter("monodroga", event.target.value)}
                  />
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
              rows={filteredMedications}
              renderRow={renderMedicationRow}
              emptyText="No hay medicamentos que coincidan con los filtros."
            />
          </section>
        </section>
      </main>
    </>
  );
}
