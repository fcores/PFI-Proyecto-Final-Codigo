import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import ReadOnlyField from "../components/ReadOnlyField";
import SimpleTable from "../components/SimpleTable";
import StatusChip from "../components/StatusChip";
import MlVerdictPanel from "../components/MlVerdictPanel";
import { fetchAuditDetail, postAuditAction } from "../api/audit";
import { ACCION_LABEL, ESTADO_VARIANT, estadoLabel } from "../constants/estadoVariant";
import { formatDate } from "../utils/formatDate";
import { formatNumber } from "../utils/format";
import { shortHash } from "../utils/shortHash";

const ACCIONES = [
  { value: "aprobar", label: "Aprobar", variant: "success", hint: "Cierra el ciclo." },
  { value: "rechazar", label: "Rechazar", variant: "error", hint: "Cierra el ciclo." },
  { value: "revision", label: "Pasar a revisión", variant: "warning", hint: "Queda abierta para un dictamen posterior." },
];

const ESTADOS_TERMINALES = ["APROBADA", "RECHAZADA"];
const MIN_JUSTIFICACION = 5;

const EVENT_COLUMNS = ["#", "Acción", "Estado resultante", "Auditor", "Justificación", "Fecha", "Tx", "Hash"];

function BackLink() {
  return (
    <Link to="/auditoria/cola" className="back-link">
      ← Volver a la cola
    </Link>
  );
}

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
    if (submitting) return;
    setAccionStatus(null);
    setSubmitting(true);
    try {
      const actualizada = await postAuditAction(prescriptionId, accionForm.accion, accionForm.justificacion.trim());
      setAccionStatus({
        type: "success",
        message: `${ACCION_LABEL[accionForm.accion] || "Acción"} registrada en la blockchain (endosada por las 3 organizaciones).`,
      });
      setAccionForm({ accion: "", justificacion: "" });
      // El POST ya devuelve el asset actualizado; se conserva el historial cargado.
      setDetail((prev) => (prev ? { ...prev, prescription: actualizada } : prev));
    } catch (err) {
      setAccionStatus({ type: "error", message: err.message || "Error al registrar la acción." });
    } finally {
      setSubmitting(false);
    }
  }

  if (loading && !detail) {
    return (
      <>
        <TopBar title="Auditoría de prescripción" subtitle="Leyendo la prescripción desde la red Fabric…" badge="Auditoría" />
        <main className="page page--wide">
          <BackLink />
          <section className="card state-card">
            <p className="muted">Leyendo la prescripción desde la red Fabric…</p>
          </section>
        </main>
      </>
    );
  }

  if (error || !detail) {
    return (
      <>
        <TopBar title="Auditoría de prescripción" badge="Auditoría" />
        <main className="page page--wide">
          <BackLink />
          <section className="card state-card" role="alert">
            <h2>No se pudo abrir el caso</h2>
            <p className="status error">{error || "La prescripción no está disponible."}</p>
            <div className="state-card__actions">
              <button type="button" className="btn-secondary" onClick={loadDetail}>
                Reintentar
              </button>
            </div>
          </section>
        </main>
      </>
    );
  }

  const presc = detail.prescription;
  const clinical = presc.clinical || {};
  const ml = presc.ml || {};
  const esTerminal = ESTADOS_TERMINALES.includes(presc.estado);
  const eventos = presc.audit_events ?? [];
  const accionesDisponibles = ACCIONES.filter((a) => !(a.value === "revision" && presc.estado === "EN_REVISION"));
  const justificacionValida = accionForm.justificacion.trim().length >= MIN_JUSTIFICACION;

  return (
    <>
      <TopBar
        title={`Prescripción ${presc.prescription_code}`}
        subtitle={`Paciente #${clinical.patient_id ?? "—"} · ${clinical.diagnostico_cie10 || "sin diagnóstico"} · estadio ${clinical.estadio || "—"}`}
        badge="Auditoría"
      />

      <main className="page page--wide">
        <BackLink />

        <section className="audit-case-detail">
          <section className="card card-form">
            <CardHeader
              split
              eyebrow="Asset on-chain"
              title="Datos clínicos"
              description="Leídos del world state de Fabric: inmutables y endosados por las tres organizaciones."
              badge={estadoLabel(presc.estado)}
            />

            <div className="form-grid">
              <ReadOnlyField label="Estado del ciclo" span={4}>
                <StatusChip variant={ESTADO_VARIANT[presc.estado] || "neutral"} label={estadoLabel(presc.estado)} />
              </ReadOnlyField>
              <ReadOnlyField label="Paciente ID" value={clinical.patient_id} span={4} />
              <ReadOnlyField label="Diagnóstico (CIE-10)" value={clinical.diagnostico_cie10} span={4} />
              <ReadOnlyField label="Edad / sexo" value={`${clinical.edad ?? "—"} años · ${clinical.sexo || "—"}`} span={4} />
              <ReadOnlyField
                label="Peso / talla"
                value={`${formatNumber(clinical.peso_kg)} kg · ${formatNumber(clinical.talla_cm)} cm`}
                span={4}
              />
              <ReadOnlyField label="Superficie corporal" value={`${formatNumber(clinical.superficie_corporal_m2)} m²`} span={4} />
              <ReadOnlyField label="Localización" value={clinical.localizacion_tumor} span={4} />
              <ReadOnlyField label="Tipo histológico" value={clinical.tipo_histologico} span={4} />
              <ReadOnlyField
                label="Estadio / TNM"
                value={`${clinical.estadio || "—"} · ${[clinical.t, clinical.n, clinical.m].filter(Boolean).join(" ") || "—"}`}
                span={4}
              />
              <ReadOnlyField
                label="Biomarcadores"
                value={`MSI ${clinical.msi || "—"} · RAS ${clinical.ras || "—"} · BRAF ${clinical.braf_v600e || "—"}`}
                span={6}
              />
              <ReadOnlyField label="Línea de tratamiento" value={clinical.linea_tratamiento} span={6} />
              <ReadOnlyField label="Esquema" value={clinical.esquema} span={8} />
              <ReadOnlyField label="Dosis derivada" value={`${formatNumber(clinical.dosis_mg_m2)} mg/m²`} span={4} />
              <ReadOnlyField label="Médico prescriptor" value={clinical.medico_prescriptor} span={4} />
              <ReadOnlyField label="Matrícula" value={clinical.matricula} span={4} />
              <ReadOnlyField label="Registrada por (usuario)" value={clinical.prescriptor_username} span={4} />
              {clinical.justificacion_costo ? (
                <ReadOnlyField label="Justificación económica del prescriptor" value={clinical.justificacion_costo} span={12} />
              ) : null}
            </div>

            {clinical.dosis_por_farmaco?.length > 0 && (
              <section className="ml-panel__section">
                <h3 className="ml-panel__title">Dosis prescritas</h3>
                <SimpleTable
                  caption="Dosis por fármaco"
                  columns={["Monodroga", "Dosis (mg)"]}
                  rows={clinical.dosis_por_farmaco}
                  renderRow={(row) => (
                    <tr key={row.monodroga}>
                      <td>{row.monodroga}</td>
                      <td className="num">{formatNumber(row.dosis_mg)}</td>
                    </tr>
                  )}
                />
              </section>
            )}

            <div className="form-grid hash-grid">
              <ReadOnlyField label="Hash del contenido" value={presc.payload_hash} span={12} mono copyable />
              <ReadOnlyField label="Hash actual (último eslabón)" value={presc.current_hash} span={12} mono copyable />
            </div>
          </section>

          <div className="audit-case-side">
            <section className="card card-form">
              {esTerminal ? (
                <CardHeader
                  split
                  eyebrow="Dictamen"
                  title={`Prescripción ${estadoLabel(presc.estado).toLowerCase()}`}
                  description="El ciclo de auditoría está cerrado; el dictamen quedó asentado de forma inmutable en la blockchain."
                />
              ) : (
                <>
                  <CardHeader
                    eyebrow="Acción de auditoría"
                    title="Registrar dictamen"
                    description="Cada acción encadena un nuevo hash on-chain y no puede deshacerse."
                  />
                  <form onSubmit={handleAccionSubmit}>
                    <fieldset className="dictamen-fieldset" disabled={submitting}>
                      <legend className="dictamen-legend">Acción</legend>
                      <div className="dictamen-radio-group">
                        {accionesDisponibles.map((accion) => (
                          <label
                            key={accion.value}
                            className={`dictamen-radio-option dictamen-radio-option--${accion.variant}${accionForm.accion === accion.value ? " is-selected" : ""}`}
                          >
                            <input
                              type="radio"
                              name="accion_radio"
                              value={accion.value}
                              checked={accionForm.accion === accion.value}
                              onChange={(e) => setAccionForm((f) => ({ ...f, accion: e.target.value }))}
                            />
                            <span className="dictamen-radio-option__text">
                              <strong>{accion.label}</strong>
                              <small>{accion.hint}</small>
                            </span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                    <div className="form-grid">
                      <FormField label="Justificación" htmlFor="accion_justificacion" required span={12}>
                        <textarea
                          id="accion_justificacion"
                          name="accion_justificacion"
                          placeholder="Detallá los motivos de la acción…"
                          value={accionForm.justificacion}
                          onChange={(e) => setAccionForm((f) => ({ ...f, justificacion: e.target.value }))}
                          required
                          minLength={MIN_JUSTIFICACION}
                          maxLength={2000}
                          disabled={submitting}
                        />
                        <p className="field-hint">
                          {accionForm.justificacion.trim().length}/2000 · mínimo {MIN_JUSTIFICACION} caracteres. Queda
                          registrada on-chain y es visible para las tres organizaciones.
                        </p>
                      </FormField>
                    </div>
                    <div className="form-actions">
                      <div className="buttons">
                        <button
                          type="submit"
                          className="btn-primary"
                          disabled={submitting || !accionForm.accion || !justificacionValida}
                        >
                          {submitting ? "Registrando en blockchain…" : "Registrar acción"}
                        </button>
                      </div>
                    </div>
                  </form>
                </>
              )}
              {accionStatus && (
                <p className={`status ${accionStatus.type} status--block`} role={accionStatus.type === "error" ? "alert" : "status"}>
                  {accionStatus.message}
                </p>
              )}
            </section>

            <section className="card card-form">
              <CardHeader
                eyebrow="Soporte de decisión"
                title="Veredicto del motor reglas + ML"
                description="El modelo no cierra el ciclo: la decisión final es siempre del auditor."
              />
              <MlVerdictPanel ml={ml} />
            </section>
          </div>

          <section className="card card-form audit-case-events">
            <CardHeader
              eyebrow="Cadena de auditoría"
              title="Eventos registrados"
              description="Cada acción encadena un hash nuevo sobre el anterior; las tres organizaciones ven el mismo historial."
            />
            {eventos.length > 0 ? (
              <SimpleTable
                caption="Eventos de auditoría"
                columns={EVENT_COLUMNS}
                rows={eventos}
                renderRow={(event) => (
                  <tr key={event.seq}>
                    <td className="num">{event.seq}</td>
                    <td>{ACCION_LABEL[event.accion] || event.accion}</td>
                    <td>
                      <StatusChip
                        variant={ESTADO_VARIANT[event.estado_resultante] || "neutral"}
                        label={estadoLabel(event.estado_resultante)}
                      />
                    </td>
                    <td>{event.auditor}</td>
                    <td className="cell-text">{event.justificacion}</td>
                    <td className="cell-nowrap">{formatDate(event.timestamp)}</td>
                    <td title={event.tx_id}>
                      <code>{shortHash(event.tx_id)}</code>
                    </td>
                    <td title={event.event_hash}>
                      <code>{shortHash(event.event_hash)}</code>
                    </td>
                  </tr>
                )}
              />
            ) : (
              <p className="muted">Sin acciones de auditoría todavía.</p>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
