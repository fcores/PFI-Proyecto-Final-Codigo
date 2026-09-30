import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import StatusChip from "../components/StatusChip";
import { fetchAuditDetail, postAuditAction } from "../api/audit";
import ConfidenceBar from "../components/ConfidenceBar";
import { ESTADO_VARIANT, ESTADO_LABEL } from "../constants/estadoVariant";
import { formatDate } from "../utils/formatDate";
import { shortHash } from "../utils/shortHash";

const ACCIONES = [
  { value: "aprobar", label: "APROBAR", variant: "success" },
  { value: "rechazar", label: "RECHAZAR", variant: "error" },
  { value: "revision", label: "REVISIÓN", variant: "warning" },
];

const ESTADOS_TERMINALES = ["APROBADA", "RECHAZADA"];

export default function AuditCasePage() {
  const { prescriptionId } = useParams();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [accionForm, setAccionForm] = useState({ accion: "", justificacion: "" });
  const [accionStatus, setAccionStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const loadDetail = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setDetail(await fetchAuditDetail(prescriptionId));
    } catch (err) {
      setError(err.message || "Error al leer la prescripción desde la red.");
    } finally {
      setLoading(false);
    }
  }, [prescriptionId]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  async function handleAccionSubmit(event) {
    event.preventDefault();
    setAccionStatus(null);
    setSubmitting(true);
    try {
      await postAuditAction(prescriptionId, accionForm.accion, accionForm.justificacion);
      setAccionStatus({
        type: "success",
        message: "Acción registrada en la blockchain (endosada por las 3 organizaciones).",
      });
      setAccionForm({ accion: "", justificacion: "" });
      await loadDetail();
    } catch (err) {
      setAccionStatus({ type: "error", message: err.message || "Error al registrar la acción." });
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <>
        <TopBar title="Auditoría de prescripción" subtitle="Cargando..." badge="Auditoría" />
        <main className="page page--wide">
          <p className="muted" style={{ textAlign: "center", padding: "3rem" }}>
            Leyendo la prescripción desde la red Fabric...
          </p>
        </main>
      </>
    );
  }

  if (error) {
    return (
      <>
        <TopBar title="Auditoría de prescripción" subtitle="Error" badge="Auditoría" />
        <main className="page page--wide">
          <section className="card" style={{ textAlign: "center", padding: "3rem" }}>
            <p className="status error">{error}</p>
          </section>
        </main>
      </>
    );
  }

  if (!detail) return null;

  const presc = detail.prescription;
  const clinical = presc.clinical || {};
  const ml = presc.ml || {};
  const esTerminal = ESTADOS_TERMINALES.includes(presc.estado);

  return (
    <>
      <TopBar
        title={`Prescripción ${presc.prescription_code}`}
        subtitle={`Paciente #${clinical.patient_id ?? ""} — estado on-chain: ${ESTADO_LABEL[presc.estado] || presc.estado}`}
        badge="Auditoría"
      />

      <main className="page page--wide">
        <section className="audit-case-detail">
          <section className="card card-form">
            <CardHeader
              split
              eyebrow="Asset on-chain"
              title={`Prescripción ${presc.prescription_code}`}
              description="Información clínica leída del world state de Fabric (inmutable, endosada por las 3 organizaciones)."
              badge={clinical.estadio ? `Estadio ${clinical.estadio}` : undefined}
            />

            <div className="form-grid">
              <FormField label="Estado del ciclo" htmlFor="case_estado_chain" span={4}>
                <div style={{ paddingTop: "8px" }}>
                  <StatusChip
                    variant={ESTADO_VARIANT[presc.estado] || "neutral"}
                    label={ESTADO_LABEL[presc.estado] || presc.estado}
                  />
                </div>
              </FormField>
              <FormField label="Paciente ID" htmlFor="case_patient" span={4}>
                <input id="case_patient" type="text" value={clinical.patient_id ?? ""} readOnly />
              </FormField>
              <FormField label="Diagnóstico (CIE-10)" htmlFor="case_diag" span={4}>
                <input id="case_diag" type="text" value={clinical.diagnostico_cie10 || ""} readOnly />
              </FormField>
              <FormField label="Estadio" htmlFor="case_estadio" span={3}>
                <input id="case_estadio" type="text" value={clinical.estadio || ""} readOnly />
              </FormField>
              <FormField label="TNM" htmlFor="case_tnm" span={3}>
                <input id="case_tnm" type="text" value={`${clinical.t || "-"} ${clinical.n || "-"} ${clinical.m || "-"}`} readOnly />
              </FormField>
              <FormField label="Esquema" htmlFor="case_esquema" span={6}>
                <input id="case_esquema" type="text" value={clinical.esquema || ""} readOnly />
              </FormField>
              <FormField label="Dosis (mg/m²)" htmlFor="case_dosis" span={3}>
                <input id="case_dosis" type="text" value={clinical.dosis_mg_m2 ?? ""} readOnly />
              </FormField>
              <FormField label="Superficie corporal (m²)" htmlFor="case_bsa" span={3}>
                <input id="case_bsa" type="text" value={clinical.superficie_corporal_m2 ?? ""} readOnly />
              </FormField>
              <FormField label="Médico prescriptor" htmlFor="case_medico" span={3}>
                <input id="case_medico" type="text" value={clinical.medico_prescriptor || ""} readOnly />
              </FormField>
              <FormField label="Matrícula" htmlFor="case_matricula" span={3}>
                <input id="case_matricula" type="text" value={clinical.matricula || ""} readOnly />
              </FormField>
              {clinical.justificacion_costo ? (
                <FormField
                  label="Justificación económica del prescriptor"
                  htmlFor="case_justificacion_costo"
                  span={12}
                >
                  <textarea
                    id="case_justificacion_costo"
                    rows={3}
                    value={clinical.justificacion_costo}
                    readOnly
                  />
                </FormField>
              ) : null}
              <FormField label="Hash del contenido" htmlFor="case_payload_hash" span={6}>
                <input id="case_payload_hash" type="text" value={presc.payload_hash || ""} readOnly title={presc.payload_hash} />
              </FormField>
              <FormField label="Hash actual (cadena)" htmlFor="case_current_hash" span={6}>
                <input id="case_current_hash" type="text" value={presc.current_hash || ""} readOnly title={presc.current_hash} />
              </FormField>
            </div>

            <CardHeader
              eyebrow="Soporte de decisión"
              title="Veredicto del motor reglas + ML"
              description="El modelo no cierra el ciclo: la decisión final es siempre del auditor."
            />
            <div className="form-grid">
              <FormField label="Veredicto" htmlFor="case_val_estado" span={4}>
                <div style={{ paddingTop: "8px" }}>
                  <StatusChip
                    variant={ESTADO_VARIANT[ml.estado] || "neutral"}
                    label={ml.estado || "—"}
                  />
                </div>
              </FormField>
              <FormField label="Origen" htmlFor="case_val_origen" span={4}>
                <input id="case_val_origen" type="text" value={ml.origen || "—"} readOnly />
              </FormField>
              <FormField label="Versión modelo" htmlFor="case_val_version" span={4}>
                <input id="case_val_version" type="text" value={ml.version_modelo || "—"} readOnly />
              </FormField>
              <FormField label="Confianza del modelo" htmlFor="case_val_confianza" span={12}>
                <ConfidenceBar
                  value={ml.probabilidad_concordante}
                  low={ml.umbral_bajo}
                  high={ml.umbral_alto}
                  label={`Nivel: ${ml.nivel_confianza || "—"}`}
                />
              </FormField>
              <FormField label="Motivos" htmlFor="case_val_motivos" span={12}>
                {ml.motivos && ml.motivos.length > 0 ? (
                  <ul className="muted" style={{ paddingLeft: "18px", margin: 0 }}>
                    {ml.motivos.map((motivo, idx) => (
                      <li key={idx}>{motivo}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">Sin motivos registrados.</p>
                )}
              </FormField>
              {ml.features_relevantes?.length > 0 && (
                <FormField label="Aportes principales" htmlFor="case_val_aportes" span={12}>
                  <ul className="muted" style={{ paddingLeft: "18px", margin: 0 }}>
                    {ml.features_relevantes.map((item) => (
                      <li key={item.feature}>
                        {item.feature}: {item.aporte}
                      </li>
                    ))}
                  </ul>
                </FormField>
              )}
              {ml.alternativas_economicas?.length > 0 && (
                <FormField
                  label="Alternativas terapéuticas de menor costo"
                  htmlFor="case_val_alternativas"
                  span={12}
                >
                  <div id="case_val_alternativas">
                    <p className="muted" style={{ margin: "0 0 0.4em" }}>
                      Esquema prescrito: $
                      {ml.costo_tratamiento?.toLocaleString("es-AR", { minimumFractionDigits: 2 })} por
                      tratamiento completo
                    </p>
                    <table className="dosis-table" style={{ marginTop: "0.25em" }}>
                      <thead>
                        <tr>
                          <th>Régimen</th>
                          <th>Ciclos</th>
                          <th>Costo del tratamiento</th>
                          <th>Ahorro</th>
                          <th>%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ml.alternativas_economicas.map((alt) => (
                          <tr key={alt.id_regimen}>
                            <td>
                              {alt.id_regimen} — {alt.nombre}
                            </td>
                            <td>{alt.ciclos}</td>
                            <td>
                              ${alt.costo_tratamiento.toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                            </td>
                            <td>${alt.ahorro.toLocaleString("es-AR", { minimumFractionDigits: 2 })}</td>
                            <td>{alt.pct_ahorro}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </FormField>
              )}
              {ml.costo_total != null && (
                <FormField label="Costo estimado" htmlFor="case_val_costo" span={12}>
                  <div>
                    <p style={{ fontWeight: 600, margin: "0 0 0.4em" }}>
                      Total por ciclo: ${ml.costo_total.toLocaleString("es-AR", { minimumFractionDigits: 2 })}
                    </p>
                    {ml.costo_por_farmaco?.length > 0 && (
                      <table className="dosis-table" style={{ marginTop: "0.25em" }}>
                        <thead>
                          <tr>
                            <th>Fármaco</th>
                            <th>Dosis (mg)</th>
                            <th>Costo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ml.costo_por_farmaco.map((item) => (
                            <tr key={item.monodroga}>
                              <td>{item.monodroga}</td>
                              <td>{item.dosis_mg}</td>
                              <td>{item.costo != null ? `$${item.costo.toLocaleString("es-AR", { minimumFractionDigits: 2 })}` : "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </FormField>
              )}
            </div>
          </section>

          <section className="card card-form">
            {esTerminal ? (
              <CardHeader
                split
                eyebrow="Dictamen"
                title={`Prescripción ${ESTADO_LABEL[presc.estado]?.toLowerCase() || presc.estado}`}
                description="El ciclo de auditoría está cerrado; el dictamen quedó asentado de forma inmutable en la blockchain."
              />
            ) : (
              <>
                <CardHeader
                  eyebrow="Acción de auditoría"
                  title="Registrar acción"
                  description="Aprobar o rechazar cierran el ciclo. Revisión marca la prescripción en revisión. Cada acción genera un nuevo hash encadenado on-chain."
                />
                <form onSubmit={handleAccionSubmit}>
                  <div className="form-grid">
                    <FormField label="Acción" htmlFor="accion_radio" span={12}>
                      <div className="dictamen-radio-group">
                        {ACCIONES.filter(
                          (a) => !(a.value === "revision" && presc.estado === "EN_REVISION")
                        ).map((accion) => (
                          <label key={accion.value} className="dictamen-radio-option">
                            <input
                              type="radio"
                              name="accion_radio"
                              value={accion.value}
                              checked={accionForm.accion === accion.value}
                              onChange={(e) =>
                                setAccionForm((f) => ({ ...f, accion: e.target.value }))
                              }
                            />
                            <StatusChip variant={accion.variant} label={accion.label} />
                          </label>
                        ))}
                      </div>
                    </FormField>
                    <FormField label="Justificación" htmlFor="accion_justificacion" span={12}>
                      <textarea
                        id="accion_justificacion"
                        name="accion_justificacion"
                        placeholder="Detallá los motivos de la acción (mínimo 5 caracteres)..."
                        value={accionForm.justificacion}
                        onChange={(e) =>
                          setAccionForm((f) => ({ ...f, justificacion: e.target.value }))
                        }
                        required
                        minLength={5}
                      />
                    </FormField>
                  </div>
                  <div className="form-actions">
                    {accionStatus && (
                      <span className={`status ${accionStatus.type}`}>{accionStatus.message}</span>
                    )}
                    <div className="buttons">
                      <button
                        type="submit"
                        className="btn-primary"
                        disabled={submitting || !accionForm.accion || accionForm.justificacion.length < 5}
                      >
                        {submitting ? "Registrando en blockchain..." : "Registrar acción"}
                      </button>
                    </div>
                  </div>
                </form>
              </>
            )}

            <div style={{ marginTop: "28px", borderTop: "1px solid rgba(213,219,229,0.9)", paddingTop: "24px" }}>
              <CardHeader
                eyebrow="Cadena de auditoría"
                title="Eventos registrados"
                description="Cada acción encadena un hash nuevo sobre el anterior; las tres organizaciones ven el mismo historial."
              />
              {presc.audit_events?.length > 0 ? (
                <table className="dosis-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Acción</th>
                      <th>Estado resultante</th>
                      <th>Auditor</th>
                      <th>Justificación</th>
                      <th>Fecha</th>
                      <th>Tx</th>
                      <th>Hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {presc.audit_events.map((event) => (
                      <tr key={event.seq}>
                        <td>{event.seq}</td>
                        <td>{event.accion}</td>
                        <td>
                          <StatusChip
                            variant={ESTADO_VARIANT[event.estado_resultante] || "neutral"}
                            label={ESTADO_LABEL[event.estado_resultante] || event.estado_resultante}
                          />
                        </td>
                        <td>{event.auditor}</td>
                        <td>{event.justificacion}</td>
                        <td>{formatDate(event.timestamp)}</td>
                        <td title={event.tx_id}><code>{shortHash(event.tx_id)}</code></td>
                        <td title={event.event_hash}><code>{shortHash(event.event_hash)}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="muted">Sin acciones de auditoría todavía.</p>
              )}
            </div>
          </section>
        </section>
      </main>
    </>
  );
}
