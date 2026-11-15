import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import ReadOnlyField from "../components/ReadOnlyField";
import { InfoGrid, InfoGroup } from "../components/InfoGroup";
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

// Biomarcadores: las alteraciones detectadas se resaltan; "no evaluado" se
// atenúa para que no se confunda con un resultado negativo.
const BIOMARCADORES = [
  { key: "msi", label: "MSI" },
  { key: "ras", label: "RAS" },
  { key: "braf_v600e", label: "BRAF V600E" },
];

const BIOMARCADOR_TEXTO = {
  no_evaluado: { texto: "No evaluado", tono: "muted" },
  wild_type: { texto: "Wild type", tono: "neutral" },
  MSS: { texto: "MSS", tono: "neutral" },
  "MSI-H": { texto: "MSI-H", tono: "alert" },
  mutado: { texto: "Mutado", tono: "alert" },
  presente: { texto: "Presente", tono: "alert" },
};

function biomarcador(valor) {
  if (!valor) return { texto: "—", tono: "muted" };
  return BIOMARCADOR_TEXTO[valor] || { texto: valor, tono: "neutral" };
}

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

            <InfoGrid>
              <InfoGroup
                title="Paciente"
                rows={[
                  { label: "ID", value: clinical.patient_id != null ? `#${clinical.patient_id}` : null },
                  { label: "Edad", value: clinical.edad != null ? `${clinical.edad} años` : null },
                  { label: "Sexo", value: clinical.sexo },
                  { label: "Peso", value: clinical.peso_kg != null ? `${formatNumber(clinical.peso_kg)} kg` : null },
                  { label: "Talla", value: clinical.talla_cm != null ? `${formatNumber(clinical.talla_cm)} cm` : null },
                  {
                    label: "Superficie corporal",
                    value:
                      clinical.superficie_corporal_m2 != null ? `${formatNumber(clinical.superficie_corporal_m2)} m²` : null,
                  },
                ]}
              />

              <InfoGroup
                title="Tumor"
                rows={[
                  { label: "Diagnóstico (CIE-10)", value: clinical.diagnostico_cie10 },
                  { label: "Localización", value: clinical.localizacion_tumor },
                  { label: "Tipo histológico", value: clinical.tipo_histologico },
                  { label: "Estadio", value: clinical.estadio },
                  { label: "TNM", value: [clinical.t, clinical.n, clinical.m].filter(Boolean).join(" · ") },
                ]}
              />

              <InfoGroup title="Biomarcadores">
                <div className="biomarker-list">
                  {BIOMARCADORES.map(({ key, label }) => {
                    const { texto, tono } = biomarcador(clinical[key]);
                    return (
                      <div className="biomarker" key={key}>
                        <span className="biomarker__name">{label}</span>
                        <span className={`biomarker__value biomarker__value--${tono}`}>{texto}</span>
                      </div>
                    );
                  })}
                </div>
              </InfoGroup>

              <InfoGroup
                title="Tratamiento"
                rows={[
                  { label: "Línea", value: clinical.linea_tratamiento },
                  {
                    label: "Esquema",
                    value: [clinical.id_regimen, clinical.esquema].filter(Boolean).join(" — "),
                  },
                  // Con varios fármacos la "dosis derivada" suma mg de drogas distintas:
                  // solo se muestra cuando el esquema tiene una sola.
                  ...((clinical.dosis_por_farmaco ?? []).length === 1 && clinical.dosis_mg_m2 != null
                    ? [{ label: "Dosis por superficie", value: `${formatNumber(clinical.dosis_mg_m2)} mg/m²` }]
                    : []),
                  ...(clinical.dosis_por_farmaco ?? []).map((row) => ({
                    label: row.monodroga,
                    value: `${formatNumber(row.dosis_mg)} mg`,
                  })),
                ]}
              />

              <InfoGroup
                title="Prescriptor"
                wide
                rows={[
                  { label: "Médico", value: clinical.medico_prescriptor },
                  { label: "Matrícula", value: clinical.matricula },
                  { label: "Usuario que la registró", value: clinical.prescriptor_username },
                  { label: "Fecha de registro", value: formatDate(presc.created_at) },
                ]}
              />

              {clinical.justificacion_costo ? (
                <InfoGroup title="Justificación económica del prescriptor" wide>
                  <p className="info-group__text">{clinical.justificacion_costo}</p>
                </InfoGroup>
              ) : null}
            </InfoGrid>

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
