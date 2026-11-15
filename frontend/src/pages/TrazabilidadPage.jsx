import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import ReadOnlyField from "../components/ReadOnlyField";
import SimpleTable from "../components/SimpleTable";
import StatusChip from "../components/StatusChip";
import {
  fetchPrescription,
  fetchPrescriptionHistory,
  verifyPrescription,
  verifyPrescriptionSignature,
} from "../api/prescriptions";
import { ACCION_LABEL, ESTADO_VARIANT, estadoLabel } from "../constants/estadoVariant";
import { shortHash } from "../utils/shortHash";
import { formatDate } from "../utils/formatDate";

function normalizarId(raw) {
  return (raw || "").trim().replace(/^PRESC-/i, "");
}

export default function TrazabilidadPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const idEnUrl = searchParams.get("id") || "";
  const [searchId, setSearchId] = useState(idEnUrl);
  const [prescription, setPrescription] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState(null);
  const [verification, setVerification] = useState(null);
  const [verificationError, setVerificationError] = useState(null);
  const [signature, setSignature] = useState(null);
  const [signatureError, setSignatureError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const consultar = useCallback(async (rawId) => {
    const id = normalizarId(rawId);
    if (!id) return;
    setLoading(true);
    setError(null);
    setPrescription(null);
    setHistory([]);
    setHistoryError(null);
    setVerification(null);
    setVerificationError(null);
    setSignature(null);
    setSignatureError(null);

    // Si falla la verificación o el historial, el asset igual se muestra.
    const [presc, hist, verif, firma] = await Promise.allSettled([
      fetchPrescription(id),
      fetchPrescriptionHistory(id),
      verifyPrescription(id),
      verifyPrescriptionSignature(id),
    ]);

    if (presc.status === "rejected") {
      setError(presc.reason?.message || "No se encontró la prescripción en la red.");
    } else {
      setPrescription(presc.value);
      if (hist.status === "fulfilled") setHistory(hist.value);
      else setHistoryError(hist.reason?.message || "No se pudo leer el historial de transacciones.");
      if (verif.status === "fulfilled") setVerification(verif.value);
      else setVerificationError(verif.reason?.message || "No se pudo verificar la cadena de hashes.");
      if (firma.status === "fulfilled") setSignature(firma.value);
      else setSignatureError(firma.reason?.message || "No se pudo verificar la firma electrónica.");
    }
    setLoading(false);
  }, []);

  // Llegada desde el historial (/trazabilidad?id=...): consulta automática.
  useEffect(() => {
    if (idEnUrl) {
      setSearchId(idEnUrl);
      consultar(idEnUrl);
    }
  }, [idEnUrl, consultar]);

  function handleSearch(event) {
    event.preventDefault();
    const id = normalizarId(searchId);
    if (!id) return;
    if (id === normalizarId(idEnUrl)) consultar(id);
    else setSearchParams({ id });
  }

  const clinical = prescription?.clinical || {};

  return (
    <>
      <TopBar
        title="Trazabilidad en blockchain"
        subtitle="Historial inmutable de cada prescripción en Hyperledger Fabric: transacciones reales endosadas por las tres organizaciones."
        badge="Trazabilidad"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-form">
            <CardHeader
              eyebrow="Consulta"
              title="Buscar prescripción"
              description="Ingresá el ID o el código (PRESC-…) para ver su historial de transacciones y verificar la cadena de hashes."
            />

            <form onSubmit={handleSearch}>
              <div className="form-grid">
                <FormField label="ID / Código de prescripción" htmlFor="traza_id" span={8}>
                  <input
                    id="traza_id"
                    type="search"
                    placeholder="PRESC-01JXXXXXXXXXXXXXXXXXXXXXXXXX"
                    value={searchId}
                    onChange={(event) => setSearchId(event.target.value)}
                  />
                </FormField>
                <div className="form-group form-group--action field-span-4">
                  <button type="submit" className="btn-primary" disabled={loading || !searchId.trim()}>
                    {loading ? "Consultando la red…" : "Consultar"}
                  </button>
                </div>
              </div>
            </form>

            {error && (
              <p className="status error status--block" role="alert">
                {error}
              </p>
            )}
          </section>

          {prescription && (
            <section className="card card-form">
              <CardHeader
                split
                eyebrow="Asset on-chain"
                title={`Prescripción ${prescription.prescription_code}`}
                description={`Creada el ${formatDate(prescription.created_at)} por ${
                  clinical.prescriptor_username || "—"
                } (${prescription.created_by_msp || "—"}).`}
                badge={estadoLabel(prescription.estado)}
              />

              <div className="form-grid">
                <ReadOnlyField label="Estado" span={4}>
                  <StatusChip
                    variant={ESTADO_VARIANT[prescription.estado] || "neutral"}
                    label={estadoLabel(prescription.estado)}
                  />
                </ReadOnlyField>
                <ReadOnlyField label="Paciente ID" value={clinical.patient_id} span={4} />
                <ReadOnlyField label="Régimen" value={clinical.esquema || clinical.id_regimen} span={4} />
                <ReadOnlyField label="Hash del contenido (payload_hash)" value={prescription.payload_hash} span={12} mono copyable />
                <ReadOnlyField label="Hash actual (último eslabón)" value={prescription.current_hash} span={12} mono copyable />
              </div>

              <div className="verify-box">
                <h3 className="ml-panel__title">Verificación de integridad</h3>
                {verification ? (
                  verification.valido ? (
                    <div className="alert alert--success" role="status">
                      Cadena de hashes verificada: el contenido y cada dictamen reproducen los hashes on-chain.
                    </div>
                  ) : (
                    <div className="alert alert--error" role="alert">
                      <strong>Cadena comprometida.</strong>
                      <ul>
                        {verification.errores.map((err) => (
                          <li key={err}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )
                ) : (
                  <div className="alert alert--warning" role="status">
                    {verificationError || "Verificación no disponible."}
                  </div>
                )}
              </div>

              <div className="verify-box">
                <h3 className="ml-panel__title">Firma electrónica del prescriptor</h3>
                {signature?.estado === "valida" && (
                  <div className="alert alert--success" role="status">
                    Firmada por {signature.firmante} (matrícula {signature.matricula || "—"}) el{" "}
                    {formatDate(signature.firmado_en)}. {signature.algoritmo}, clave{" "}
                    <code title={signature.huella_clave}>{shortHash(signature.huella_clave)}</code>.
                  </div>
                )}
                {signature?.estado === "invalida" && (
                  <div className="alert alert--error" role="alert">
                    <strong>Firma inválida.</strong> {signature.detalle}
                  </div>
                )}
                {signature?.estado === "sin_firma" && (
                  <div className="alert alert--warning" role="status">
                    {signature.detalle}
                  </div>
                )}
                {!signature && (
                  <div className="alert alert--warning" role="status">
                    {signatureError || "Verificación de firma no disponible."}
                  </div>
                )}
              </div>

              <CardHeader
                eyebrow="Historial Fabric"
                title="Transacciones sobre el asset"
                description="Una entrada por transacción que modificó la prescripción: creación y cada acción de auditoría, con su TxID real."
              />
              {historyError ? (
                <p className="status error status--block">{historyError}</p>
              ) : history.length > 0 ? (
                <SimpleTable
                  caption="Transacciones sobre el asset"
                  columns={["#", "TxID", "Fecha", "Estado resultante", "Hash de la cadena"]}
                  rows={history}
                  renderRow={(entry, idx) => (
                    <tr key={entry.tx_id || idx}>
                      <td className="num">{idx + 1}</td>
                      <td title={entry.tx_id}>
                        <code>{shortHash(entry.tx_id)}</code>
                      </td>
                      <td className="cell-nowrap">{formatDate(entry.timestamp)}</td>
                      <td>
                        <StatusChip
                          variant={ESTADO_VARIANT[entry.value?.estado] || "neutral"}
                          label={estadoLabel(entry.value?.estado)}
                        />
                      </td>
                      <td title={entry.value?.current_hash || ""}>
                        <code>{shortHash(entry.value?.current_hash)}</code>
                      </td>
                    </tr>
                  )}
                />
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
                  <SimpleTable
                    caption="Eventos de auditoría"
                    columns={["#", "Acción", "Auditor", "Justificación", "Fecha", "prev_hash", "event_hash"]}
                    rows={prescription.audit_events}
                    renderRow={(event) => (
                      <tr key={event.seq}>
                        <td className="num">{event.seq}</td>
                        <td>{ACCION_LABEL[event.accion] || event.accion}</td>
                        <td>{event.auditor}</td>
                        <td className="cell-text">{event.justificacion}</td>
                        <td className="cell-nowrap">{formatDate(event.timestamp)}</td>
                        <td title={event.prev_hash}>
                          <code>{shortHash(event.prev_hash)}</code>
                        </td>
                        <td title={event.event_hash}>
                          <code>{shortHash(event.event_hash)}</code>
                        </td>
                      </tr>
                    )}
                  />
                </>
              )}
            </section>
          )}
        </section>
      </main>
    </>
  );
}
