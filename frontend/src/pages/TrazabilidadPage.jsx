import { useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import StatusChip from "../components/StatusChip";
import {
  fetchPrescription,
  fetchPrescriptionHistory,
  verifyPrescription,
} from "../api/prescriptions";
import { ESTADO_VARIANT, ESTADO_LABEL } from "../constants/estadoVariant";
import { shortHash } from "../utils/shortHash";
import { formatDate } from "../utils/formatDate";

export default function TrazabilidadPage() {
  const [searchId, setSearchId] = useState("");
  const [prescription, setPrescription] = useState(null);
  const [history, setHistory] = useState([]);
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSearch(event) {
    event.preventDefault();
    const id = searchId.trim().replace(/^PRESC-/i, "");
    if (!id) return;
    setLoading(true);
    setError(null);
    setPrescription(null);
    setHistory([]);
    setVerification(null);
    try {
      const [presc, hist, verif] = await Promise.all([
        fetchPrescription(id),
        fetchPrescriptionHistory(id),
        verifyPrescription(id),
      ]);
      setPrescription(presc);
      setHistory(hist);
      setVerification(verif);
    } catch (err) {
      setError(err.message || "No se encontró la prescripción en la red.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <TopBar
        title="Trazabilidad en blockchain"
        subtitle="Historial inmutable de cada prescripción en Hyperledger Fabric: transacciones reales endosadas por las tres organizaciones."
        badge="Auditorías"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-form">
            <CardHeader
              eyebrow="Consulta"
              title="🔗 Buscar prescripción"
              description="Ingresá el ID o el código (PRESC-...) para ver su historial de transacciones y verificar la cadena de hashes."
            />

            <form onSubmit={handleSearch}>
              <div className="form-grid">
                <FormField label="ID / Código de prescripción" htmlFor="traza_id" span={8}>
                  <input
                    id="traza_id"
                    type="text"
                    placeholder="PRESC-01JXXXXXXXXXXXXXXXXXXXXXXXXX"
                    value={searchId}
                    onChange={(event) => setSearchId(event.target.value)}
                  />
                </FormField>
                <FormField label=" " htmlFor="traza_buscar" span={4}>
                  <button id="traza_buscar" type="submit" className="btn-primary" disabled={loading || !searchId.trim()}>
                    {loading ? "Consultando la red..." : "Consultar"}
                  </button>
                </FormField>
              </div>
            </form>

            {error && <p className="status error">{error}</p>}
          </section>

          {prescription && (
            <section className="card card-form">
              <CardHeader
                split
                eyebrow="Asset on-chain"
                title={`Prescripción ${prescription.prescription_code}`}
                description={`Creada por ${prescription.created_by_msp || "—"} · ${formatDate(prescription.created_at)}`}
                badge={ESTADO_LABEL[prescription.estado] || prescription.estado}
              />

              <div className="form-grid">
                <FormField label="Estado" htmlFor="traza_estado" span={3}>
                  <div style={{ paddingTop: "8px" }}>
                    <StatusChip
                      variant={ESTADO_VARIANT[prescription.estado] || "neutral"}
                      label={ESTADO_LABEL[prescription.estado] || prescription.estado}
                    />
                  </div>
                </FormField>
                <FormField label="Verificación de integridad" htmlFor="traza_verif" span={9}>
                  <div style={{ paddingTop: "8px" }}>
                    {verification && (
                      <StatusChip
                        variant={verification.valido ? "success" : "error"}
                        label={
                          verification.valido
                            ? "Cadena de hashes verificada"
                            : `Cadena comprometida: ${verification.errores.join("; ")}`
                        }
                      />
                    )}
                  </div>
                </FormField>
                <FormField label="Hash del contenido (payload_hash)" htmlFor="traza_payload_hash" span={6}>
                  <input id="traza_payload_hash" type="text" value={prescription.payload_hash || ""} readOnly />
                </FormField>
                <FormField label="Hash actual (último eslabón)" htmlFor="traza_current_hash" span={6}>
                  <input id="traza_current_hash" type="text" value={prescription.current_hash || ""} readOnly />
                </FormField>
              </div>

              <CardHeader
                eyebrow="Historial Fabric"
                title="Transacciones sobre el asset"
                description="Una entrada por transacción que modificó la prescripción: creación y cada acción de auditoría, con su TxID real."
              />
              {history.length > 0 ? (
                <table className="dosis-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>TxID</th>
                      <th>Fecha</th>
                      <th>Estado resultante</th>
                      <th>Hash de la cadena</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((entry, idx) => (
                      <tr key={entry.tx_id || idx}>
                        <td>{idx + 1}</td>
                        <td title={entry.tx_id}><code>{shortHash(entry.tx_id)}</code></td>
                        <td>{formatDate(entry.timestamp)}</td>
                        <td>
                          <StatusChip
                            variant={ESTADO_VARIANT[entry.value?.estado] || "neutral"}
                            label={ESTADO_LABEL[entry.value?.estado] || entry.value?.estado || "—"}
                          />
                        </td>
                        <td title={entry.value?.current_hash || ""}>
                          <code>{shortHash(entry.value?.current_hash)}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="muted">Sin transacciones registradas.</p>
              )}

              {prescription.audit_events?.length > 0 && (
                <>
                  <CardHeader
                    eyebrow="Cadena de auditoría"
                    title="Eventos de auditoría"
                    description="Cada acción del auditor encadena un hash nuevo sobre el anterior."
                  />
                  <table className="dosis-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Acción</th>
                        <th>Auditor</th>
                        <th>Fecha</th>
                        <th>prev_hash</th>
                        <th>event_hash</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prescription.audit_events.map((event) => (
                        <tr key={event.seq}>
                          <td>{event.seq}</td>
                          <td>{event.accion}</td>
                          <td>{event.auditor}</td>
                          <td>{formatDate(event.timestamp)}</td>
                          <td title={event.prev_hash}><code>{shortHash(event.prev_hash)}</code></td>
                          <td title={event.event_hash}><code>{shortHash(event.event_hash)}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </section>
          )}
        </section>
      </main>
    </>
  );
}
