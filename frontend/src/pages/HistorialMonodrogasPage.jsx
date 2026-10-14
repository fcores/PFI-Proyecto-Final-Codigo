import { useCallback, useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import { fetchMonodrugs } from "../api/monodrugs";

const TABLE_COLUMNS = ["Código", "Descripción"];

export default function HistorialMonodrogasPage() {
  const [monodrugs, setMonodrugs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  const loadMonodrugs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setMonodrugs(await fetchMonodrugs());
    } catch (err) {
      setError(err.message || "No se pudo cargar el maestro de monodrogas.");
      setMonodrugs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMonodrugs();
  }, [loadMonodrugs]);

  const filteredMonodrugs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return monodrugs;
    return monodrugs.filter((monodrug) =>
      [monodrug.descripcion, monodrug.codigo].filter(Boolean).join(" ").toLowerCase().includes(normalizedQuery),
    );
  }, [query, monodrugs]);

  function renderMonodrugRow(monodrug) {
    return (
      <tr key={monodrug.id}>
        <td className="cell-nowrap">{monodrug.codigo}</td>
        <td>{monodrug.descripcion}</td>
      </tr>
    );
  }

  const emptyText = loading
    ? "Cargando monodrogas…"
    : error
      ? "No se pudo cargar el maestro."
      : query
        ? "No hay monodrogas que coincidan con la búsqueda."
        : "Todavía no hay monodrogas cargadas.";

  return (
    <>
      <TopBar
        title="Historial de monodrogas"
        subtitle="Consultá el maestro de monodrogas por descripción o código."
        badge="Monodrogas"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Maestro farmacológico</span>
                <h2>Monodrogas cargadas</h2>
              </div>
              <PanelStat count={filteredMonodrugs.length} singular="resultado" plural="resultados" />
            </header>

            <div className="history-toolbar">
              <div className="form-grid history-filters">
                <FormField label="Buscar" htmlFor="history_monodrug_query" span={10}>
                  <input
                    id="history_monodrug_query"
                    type="search"
                    placeholder="Descripción o código (MONO-0001)"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </FormField>
                <div className="form-group form-group--action field-span-2">
                  <button type="button" className="btn-secondary" disabled={!query} onClick={() => setQuery("")}>
                    Limpiar
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <p className="status error status--block" role="alert">
                {error}{" "}
                <button type="button" className="btn-link" onClick={loadMonodrugs}>
                  Reintentar
                </button>
              </p>
            )}

            <DataTable columns={TABLE_COLUMNS} rows={filteredMonodrugs} renderRow={renderMonodrugRow} emptyText={emptyText} />
          </section>
        </section>
      </main>
    </>
  );
}
