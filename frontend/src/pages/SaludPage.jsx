import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import SimpleTable from "../components/SimpleTable";
import StatusChip from "../components/StatusChip";
import { get } from "../api/client";

function chipFor(ok) {
  return <StatusChip variant={ok ? "success" : "error"} label={ok ? "OK" : "Caído"} />;
}

export default function SaludPage() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [checkedAt, setCheckedAt] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setHealth(await get("/health"));
      setCheckedAt(new Date());
    } catch (err) {
      setError(err.message || "No se pudo consultar el estado del sistema.");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const fabric = health?.fabric_gateway || {};
  const orgs = fabric.orgs || {};

  const filas = health
    ? [
        {
          key: "db",
          componente: "Base de datos (RDS)",
          ok: health.database === "connected",
          detalle: health.database === "connected" ? "Conectada" : health.database,
        },
        {
          key: "ml",
          componente: "Modelo ML",
          ok: health.modelo_disponible,
          detalle: health.modelo_version ? `v${health.modelo_version}` : "No disponible",
        },
        {
          key: "gateway",
          componente: "Puente Fabric (gateway)",
          ok: fabric.status === "ok",
          detalle: `${fabric.status || "sin configurar"}${
            fabric.channel ? ` · canal ${fabric.channel} · chaincode ${fabric.chaincode}` : ""
          }`,
        },
        ...Object.entries(orgs).map(([actor, org]) => ({
          key: actor,
          componente: `Peer ${org.msp_id || actor}`,
          ok: org.status === "ok",
          detalle: `${org.peer || ""}${org.error ? ` — ${org.error}` : ""}`,
        })),
      ]
    : [];

  return (
    <>
      <TopBar
        title="Salud del sistema"
        subtitle="Estado de la base de datos, el modelo ML, el puente Fabric y los peers de las tres organizaciones."
        badge="Super Admin"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-form">
            <CardHeader
              split
              eyebrow="Monitoreo"
              title="Componentes"
              description="La red Fabric es la fuente de verdad de las prescripciones: si un peer está caído, las escrituras se bloquean (endorsement AND de las 3 orgs)."
            />

            <div className="toolbar-row">
              <span className="muted">
                {checkedAt ? `Última consulta: ${checkedAt.toLocaleTimeString("es-AR")}` : "Consultando…"}
              </span>
              <button type="button" className="btn-secondary" onClick={load} disabled={loading}>
                {loading ? "Consultando…" : "Actualizar"}
              </button>
            </div>

            {error && (
              <p className="status error status--block" role="alert">
                {error}
              </p>
            )}

            {health && (
              <SimpleTable
                caption="Estado de los componentes"
                columns={["Componente", "Estado", "Detalle"]}
                rows={filas}
                renderRow={(fila) => (
                  <tr key={fila.key}>
                    <td>{fila.componente}</td>
                    <td>{chipFor(fila.ok)}</td>
                    <td className="cell-text">{fila.detalle}</td>
                  </tr>
                )}
              />
            )}
          </section>
        </section>
      </main>
    </>
  );
}
