import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchMonodrugs } from "../api/monodrugs";

const TABLE_COLUMNS = [
  "ID",
  "Descripción",
  "ID SAP",
];

export default function HistorialMonodrogasPage() {
  const [monodrugs, setMonodrugs] = useState([]);
  const [filters, setFilters] = useState({
    query: "",
    sap_id: "",
  });

  const loadMonodrugs = useCallback(async () => {
    try {
      setMonodrugs(await fetchMonodrugs());
    } catch {
      setMonodrugs([]);
    }
  }, []);

  useEffect(() => {
    loadMonodrugs();
  }, [loadMonodrugs]);

  const filteredMonodrugs = useMemo(() => {
    const normalizedQuery = filters.query.trim().toLowerCase();
    const normalizedSap = filters.sap_id.trim().toLowerCase();

    return monodrugs.filter((monodrug) => {
      const searchableText = [
        monodrug.descripcion,
        monodrug.sap_id,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery
        ? searchableText.includes(normalizedQuery)
        : true;
      const matchesSap = normalizedSap
        ? monodrug.sap_id.toLowerCase().includes(normalizedSap)
        : true;

      return matchesQuery && matchesSap;
    });
  }, [filters, monodrugs]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      query: "",
      sap_id: "",
    });
  }

  function renderMonodrugRow(monodrug) {
    return (
      <tr key={monodrug.id}>
        <td>{monodrug.id}</td>
        <td>{monodrug.descripcion}</td>
        <td>{monodrug.sap_id}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de monodrogas"
        subtitle="Consultá el maestro de monodrogas y aplicá filtros por descripción o ID SAP."
        badge="Monodrogas"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header agreements-header--modern">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>🧪 Monodrogas cargadas</h2>
                <p className="muted">
                  Usá los filtros para consultar las monodrogas cargadas en el maestro farmacológico.
                </p>
              </div>
              <PanelStat count={filteredMonodrugs.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Consultas"
                title="Filtros generales"
                description="Buscá por descripción o por ID SAP de la monodroga."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_monodrug_query" span={8}>
                  <input
                    id="history_monodrug_query"
                    name="history_monodrug_query"
                    type="text"
                    placeholder="Descripción o ID SAP"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="ID SAP" htmlFor="history_monodrug_sap_id" span={4}>
                  <input
                    id="history_monodrug_sap_id"
                    name="history_monodrug_sap_id"
                    type="text"
                    placeholder="MONO-SAP..."
                    value={filters.sap_id}
                    onChange={(event) => updateFilter("sap_id", event.target.value)}
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
              rows={filteredMonodrugs}
              renderRow={renderMonodrugRow}
              emptyText="No hay monodrogas que coincidan con los filtros."
            />
          </section>
        </section>
      </main>
    </>
  );
}
