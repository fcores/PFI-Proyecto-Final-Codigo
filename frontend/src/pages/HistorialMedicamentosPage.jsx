import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchMedications } from "../api/medications";

const TABLE_COLUMNS = [
  "ID",
  "Descripción",
  "EAN",
  "Alfabeta",
  "Conservación",
  "ID SAP",
  "ID Monodroga",
  "Descripción Monodroga",
  "Tamaño / dimensión",
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
    sap_id: "",
    monodroga_id: "",
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
        medication.descripcion,
        medication.ean,
        medication.codigo_alfabeta,
        medication.sap_id,
        medication.monodroga_id,
        medication.monodroga_descripcion,
        medication.tamano_dimension,
        medication.tipo_conservacion,
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
      const matchesSap = filters.sap_id
        ? medication.sap_id.toLowerCase().includes(filters.sap_id.trim().toLowerCase())
        : true;
      const matchesMonodroga = filters.monodroga_id
        ? medication.monodroga_id.toLowerCase().includes(filters.monodroga_id.trim().toLowerCase())
        : true;

      return matchesQuery && matchesConservacion && matchesSap && matchesMonodroga;
    });
  }, [filters, medications]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      query: "",
      tipo_conservacion: "",
      sap_id: "",
      monodroga_id: "",
    });
  }

  function renderMedicationRow(medication) {
    return (
      <tr key={medication.id}>
        <td>{medication.id}</td>
        <td>{medication.descripcion}</td>
        <td>{medication.ean}</td>
        <td>{medication.codigo_alfabeta}</td>
        <td>{formatConservation(medication.tipo_conservacion)}</td>
        <td>{medication.sap_id}</td>
        <td>{medication.monodroga_id}</td>
        <td>{medication.monodroga_descripcion || "-"}</td>
        <td>{medication.tamano_dimension}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de medicamentos"
        subtitle="Consultá el maestro de materiales y filtrá medicamentos por distintos identificadores operativos."
        badge="Medicamentos"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header agreements-header--modern">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>💊 Medicamentos cargados</h2>
                <p className="muted">
                  Usá los filtros para buscar materiales por descripción, códigos, monodroga asociada y condiciones de conservación.
                </p>
              </div>
              <PanelStat count={filteredMedications.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros generales"
                description="Buscá por descripción, EAN, Alfabeta, SAP, ID de monodroga, descripción de monodroga o conservación."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_medication_query" span={6}>
                  <input
                    id="history_medication_query"
                    name="history_medication_query"
                    type="text"
                    placeholder="Descripción, EAN, Alfabeta o dimensión"
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

                <FormField label="ID SAP" htmlFor="history_medication_sap" span={2}>
                  <input
                    id="history_medication_sap"
                    name="history_medication_sap"
                    type="text"
                    placeholder="SAP..."
                    value={filters.sap_id}
                    onChange={(event) => updateFilter("sap_id", event.target.value)}
                  />
                </FormField>

                <FormField label="Monodroga" htmlFor="history_medication_monodroga" span={2}>
                  <input
                    id="history_medication_monodroga"
                    name="history_medication_monodroga"
                    type="text"
                    placeholder="MONO..."
                    value={filters.monodroga_id}
                    onChange={(event) => updateFilter("monodroga_id", event.target.value)}
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
