import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchMonodrugs } from "../api/monodrugs";

const TABLE_COLUMNS = [
  "ID",
  "Código",
  "Descripción",
];

export default function HistorialMonodrogasPage() {
  const [monodrugs, setMonodrugs] = useState([]);
  const [filters, setFilters] = useState({
    query: "",
    codigo: "",
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
    const normalizedCodigo = filters.codigo.trim().toLowerCase();

    return monodrugs.filter((monodrug) => {
      const searchableText = [
        monodrug.descripcion,
        monodrug.codigo,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = normalizedQuery
        ? searchableText.includes(normalizedQuery)
        : true;
      const matchesCodigo = normalizedCodigo
        ? (monodrug.codigo || "").toLowerCase().includes(normalizedCodigo)
        : true;

      return matchesQuery && matchesCodigo;
    });
  }, [filters, monodrugs]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      query: "",
      codigo: "",
    });
  }

  function renderMonodrugRow(monodrug) {
    return (
      <tr key={monodrug.id}>
        <td>{monodrug.id}</td>
        <td>{monodrug.codigo}</td>
        <td>{monodrug.descripcion}</td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Historial de monodrogas"
        subtitle="Consultá el maestro de monodrogas y aplicá filtros por descripción o código."
        badge="Monodrogas"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Actividad</span>
                <h2>Monodrogas cargadas</h2>
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
                description="Buscá por descripción o por código autogenerado (MONO-XXXX)."
              />

              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_monodrug_query" span={8}>
                  <input
                    id="history_monodrug_query"
                    name="history_monodrug_query"
                    type="text"
                    placeholder="Descripción o código"
                    value={filters.query}
                    onChange={(event) => updateFilter("query", event.target.value)}
                  />
                </FormField>

                <FormField label="Código" htmlFor="history_monodrug_codigo" span={4}>
                  <input
                    id="history_monodrug_codigo"
                    name="history_monodrug_codigo"
                    type="text"
                    placeholder="MONO-0001"
                    value={filters.codigo}
                    onChange={(event) => updateFilter("codigo", event.target.value)}
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
