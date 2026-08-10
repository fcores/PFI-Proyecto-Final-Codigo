import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchLedger, verifyLedger } from "../api/ledger";
import { shortHash } from "../utils/shortHash";

const TABLE_COLUMNS = ["#", "Tipo", "Fecha", "Contenido", "Hash", "Hash anterior"];

function formatPayload(payload) {
  const keys = Object.keys(payload || {});
  if (keys.length === 0) return "—";
  return keys.map((key) => `${key}: ${payload[key]}`).join(" · ");
}

export default function TrazabilidadPage() {
  const [blocks, setBlocks] = useState([]);
  const [verification, setVerification] = useState(null);

  const load = useCallback(async () => {
    try {
      const [chain, verif] = await Promise.all([fetchLedger(), verifyLedger()]);
      setBlocks(chain);
      setVerification(verif);
    } catch {
      setBlocks([]);
      setVerification(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function renderRow(block) {
    return (
      <tr key={block.index}>
        <td>{block.index}</td>
        <td>{block.tx_type}</td>
        <td>{new Date(block.timestamp).toLocaleString()}</td>
        <td>{formatPayload(block.payload)}</td>
        <td title={block.hash}><code>{shortHash(block.hash)}</code></td>
        <td title={block.prev_hash}><code>{shortHash(block.prev_hash)}</code></td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Trazabilidad en blockchain"
        subtitle="Registro inmutable y auditable del circuito. Cada operación se encadena por hash SHA-256 (blockchain simulada)."
        badge="Auditorías"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Integridad</span>
                <h2>🔗 Cadena de bloques</h2>
                <p className="muted">
                  Verificación de la integridad de la cadena recomputando los hashes de cada bloque.
                </p>
              </div>
              <div className="history-toolbar-actions" style={{ gap: "0.75rem", alignItems: "center", display: "flex" }}>
                {verification && (
                  <StatusChip
                    variant={verification.valido ? "success" : "error"}
                    label={verification.valido ? "Cadena íntegra" : `Cadena comprometida (bloque ${verification.roto_en})`}
                  />
                )}
                <PanelStat count={blocks.length} singular="bloque" plural="bloques" />
              </div>
            </header>

            <div className="history-toolbar">
              <CardHeader
                eyebrow="Ledger"
                title="Bloques registrados"
                description="Bloque 0 = génesis. Cada nueva prescripción agrega un bloque enlazado al anterior."
              />
              <div className="history-toolbar-actions">
                <button type="button" className="btn-secondary" onClick={load}>
                  Actualizar
                </button>
              </div>
            </div>

            <DataTable
              columns={TABLE_COLUMNS}
              rows={blocks}
              renderRow={renderRow}
              emptyText="Aún no hay bloques en el ledger."
            />
          </section>
        </section>
      </main>
    </>
  );
}
