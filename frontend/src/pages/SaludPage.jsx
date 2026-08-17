import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import StatusChip from "../components/StatusChip";
import { get } from "../api/client";

function chipFor(ok) {
  return <StatusChip variant={ok ? "success" : "error"} label={ok ? "OK" : "Caído"} />;
}

export default function SaludPage() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setHealth(await get("/health"));
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
              title="🩺 Componentes"
              description="La red Fabric es la fuente de verdad de las prescripciones: si un peer está caído, las escrituras se bloquean (endorsement AND de las 3 orgs)."
            />

            <div className="history-toolbar-actions" style={{ marginBottom: "16px" }}>
              <button type="button" className="btn-secondary" onClick={load} disabled={loading}>
                {loading ? "Consultando..." : "Actualizar"}
              </button>
            </div>

            {error && <p className="status error">{error}</p>}

            {health && (
              <table className="dosis-table">
                <thead>
                  <tr>
                    <th>Componente</th>
                    <th>Estado</th>
                    <th>Detalle</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Base de datos (RDS)</td>
                    <td>{chipFor(health.database === "connected")}</td>
                    <td>{health.database}</td>
                  </tr>
                  <tr>
                    <td>Modelo ML</td>
                    <td>{chipFor(health.modelo_disponible)}</td>
                    <td>{health.modelo_version ? `v${health.modelo_version}` : "no disponible"}</td>
                  </tr>
                  <tr>
                    <td>Puente Fabric (gateway)</td>
                    <td>{chipFor(fabric.status === "ok")}</td>
                    <td>
                      {fabric.status || "sin configurar"}
                      {fabric.channel ? ` · canal ${fabric.channel} · chaincode ${fabric.chaincode}` : ""}
                    </td>
                  </tr>
                  {Object.entries(orgs).map(([actor, org]) => (
                    <tr key={actor}>
                      <td>Peer {org.msp_id || actor}</td>
                      <td>{chipFor(org.status === "ok")}</td>
                      <td>
                        {org.peer}
                        {org.error ? ` — ${org.error}` : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
