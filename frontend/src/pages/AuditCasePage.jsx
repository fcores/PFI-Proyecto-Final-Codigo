import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import StatusChip from "../components/StatusChip";
import DataTable from "../components/DataTable";
import {
  fetchAuditCase,
  createDictamen,
  createCorrection,
  fetchCorrectionHistory,
} from "../api/audit";

const ESTADO_VARIANT = {
  APROBADO: "success",
  RECHAZADO: "error",
  PENDIENTE_DOCS: "warning",
  REVISION: "info",
  pendiente: "neutral",
};

const CORRECTION_COLUMNS = ["Campo", "Valor nuevo", "Justificación", "Fecha"];

const CAMPO_OPTIONS = [
  "diagnostico_cie10",
  "estadio",
  "esquema",
  "dosis_mg_m2",
  "localizacion_tumor",
  "tipo_histologico",
  "linea_tratamiento",
];

function formatDate(raw) {
  if (!raw) return "—";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function AuditCasePage() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [corrections, setCorrections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [dictamenForm, setDictamenForm] = useState({
    resultado: "",
    justificacion: "",
  });
  const [dictamenStatus, setDictamenStatus] = useState(null);

  const [correctionForm, setCorrectionForm] = useState({
    campo: "",
    valor_nuevo: "",
    justificacion: "",
  });
  const [showCorrectionForm, setShowCorrectionForm] = useState(false);
  const [correctionStatus, setCorrectionStatus] = useState(null);

  const loadCase = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAuditCase(caseId);
      setCaseData(data);
    } catch (err) {
      setError(err.message || "Error al cargar el caso.");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  const loadHistory = useCallback(async () => {
    try {
      const history = await fetchCorrectionHistory(caseId);
      setCorrections(history);
    } catch {
      setCorrections([]);
    }
  }, [caseId]);

  useEffect(() => {
    loadCase();
    loadHistory();
  }, [loadCase, loadHistory]);

  async function handleDictamenSubmit(event) {
    event.preventDefault();
    setDictamenStatus(null);
    try {
      await createDictamen(caseId, dictamenForm.resultado, dictamenForm.justificacion);
      setDictamenStatus({ type: "success", message: "Dictamen registrado correctamente." });
      await loadCase();
    } catch (err) {
      setDictamenStatus({ type: "error", message: err.message || "Error al registrar dictamen." });
    }
  }

  async function handleCorrectionSubmit(event) {
    event.preventDefault();
    setCorrectionStatus(null);
    try {
      await createCorrection(
        caseId,
        correctionForm.campo,
        correctionForm.valor_nuevo,
        correctionForm.justificacion
      );
      setCorrectionStatus({ type: "success", message: "Corrección registrada." });
      setCorrectionForm({ campo: "", valor_nuevo: "", justificacion: "" });
      setShowCorrectionForm(false);
      await loadHistory();
    } catch (err) {
      setCorrectionStatus({ type: "error", message: err.message || "Error al registrar corrección." });
    }
  }

  function renderCorrectionRow(item, idx) {
    return (
      <tr key={idx}>
        <td>{item.campo}</td>
        <td>{item.valor_nuevo}</td>
        <td>{item.justificacion}</td>
        <td>{formatDate(item.fecha)}</td>
      </tr>
    );
  }

  if (loading) {
    return (
      <>
        <TopBar title="Detalle del caso" subtitle="Cargando..." badge="Auditoría" />
        <main className="page page--wide">
          <p className="muted" style={{ textAlign: "center", padding: "3rem" }}>
            Cargando caso de auditoría...
          </p>
        </main>
      </>
    );
  }

  if (error) {
    return (
      <>
        <TopBar title="Detalle del caso" subtitle="Error" badge="Auditoría" />
        <main className="page page--wide">
          <section className="card" style={{ textAlign: "center", padding: "3rem" }}>
            <p className="status error">{error}</p>
          </section>
        </main>
      </>
    );
  }

  if (!caseData) return null;

  const prescription = caseData.prescription || caseData;
  const validacion = prescription.validacion || {};
  const dictamen = caseData.dictamen;
  const hasDictamen = dictamen && dictamen.resultado;

  return (
    <>
      <TopBar
        title={`Caso ${caseId}`}
        subtitle={`Prescripción ${prescription.prescription_code || ""} — Paciente ${prescription.patient_sap_id || ""}`}
        badge="Auditoría"
      />

      <main className="page page--wide">
        <section className="audit-case-detail">
          <section className="card card-form">
            <CardHeader
              split
              eyebrow="Datos de la prescripción"
              title={`Prescripción ${prescription.prescription_code || ""}`}
              description="Información clínica y resultado de validación automática."
              badge={prescription.estadio ? `Estadio ${prescription.estadio}` : undefined}
            />

            <div className="form-grid">
              <FormField label="Paciente SAP" htmlFor="case_patient" span={4}>
                <input id="case_patient" type="text" value={prescription.patient_sap_id || ""} readOnly />
              </FormField>
              <FormField label="Diagnóstico (CIE-10)" htmlFor="case_diag" span={4}>
                <input id="case_diag" type="text" value={prescription.diagnostico_cie10 || ""} readOnly />
              </FormField>
              <FormField label="Estadio" htmlFor="case_estadio" span={4}>
                <input id="case_estadio" type="text" value={prescription.estadio || ""} readOnly />
              </FormField>
              <FormField label="Esquema" htmlFor="case_esquema" span={6}>
                <input id="case_esquema" type="text" value={prescription.esquema || ""} readOnly />
              </FormField>
              <FormField label="Dosis (mg/m²)" htmlFor="case_dosis" span={3}>
                <input id="case_dosis" type="text" value={prescription.dosis_mg_m2 || ""} readOnly />
              </FormField>
              <FormField label="Superficie corporal (m²)" htmlFor="case_bsa" span={3}>
                <input id="case_bsa" type="text" value={prescription.superficie_corporal_m2 || ""} readOnly />
              </FormField>
            </div>

            <CardHeader
              eyebrow="Validación automática"
              title="Resultado"
              description="Estado y motivos de la validación preliminar."
            />
            <div className="form-grid">
              <FormField label="Estado" htmlFor="case_val_estado" span={4}>
                <div style={{ paddingTop: "8px" }}>
                  <StatusChip
                    variant={ESTADO_VARIANT[validacion.estado] || "neutral"}
                    label={validacion.estado || "—"}
                  />
                </div>
              </FormField>
              <FormField label="Motivos" htmlFor="case_val_motivos" span={8}>
                {validacion.motivos && validacion.motivos.length > 0 ? (
                  <ul className="muted" style={{ paddingLeft: "18px", margin: 0 }}>
                    {validacion.motivos.map((motivo, idx) => (
                      <li key={idx}>{motivo}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">Sin motivos registrados.</p>
                )}
              </FormField>
            </div>
          </section>

          <section className="card card-form">
            {hasDictamen ? (
              <>
                <CardHeader
                  split
                  eyebrow="Dictamen del auditor"
                  title="Dictamen registrado"
                  description="Este caso ya fue dictaminado."
                />
                <div className="form-grid">
                  <FormField label="Resultado" htmlFor="dict_resultado" span={4}>
                    <div style={{ paddingTop: "8px" }}>
                      <StatusChip
                        variant={ESTADO_VARIANT[dictamen.resultado] || "neutral"}
                        label={dictamen.resultado}
                      />
                    </div>
                  </FormField>
                  <FormField label="Justificación" htmlFor="dict_justificacion" span={8}>
                    <textarea
                      id="dict_justificacion"
                      value={dictamen.justificacion || ""}
                      readOnly
                      style={{ minHeight: "80px" }}
                    />
                  </FormField>
                  {dictamen.fecha && (
                    <FormField label="Fecha" htmlFor="dict_fecha" span={4}>
                      <input id="dict_fecha" type="text" value={formatDate(dictamen.fecha)} readOnly />
                    </FormField>
                  )}
                </div>
              </>
            ) : (
              <>
                <CardHeader
                  eyebrow="Dictamen del auditor"
                  title="Emitir dictamen"
                  description="Seleccioná el resultado y escribí la justificación."
                />
                <form onSubmit={handleDictamenSubmit}>
                  <div className="form-grid">
                    <FormField label="Resultado" htmlFor="dictamen_resultado" span={12}>
                      <div className="dictamen-radio-group">
                        <label className="dictamen-radio-option">
                          <input
                            type="radio"
                            name="dictamen_resultado"
                            value="APROBADO"
                            checked={dictamenForm.resultado === "APROBADO"}
                            onChange={(e) =>
                              setDictamenForm((f) => ({ ...f, resultado: e.target.value }))
                            }
                          />
                          <StatusChip variant="success" label="APROBADO" />
                        </label>
                        <label className="dictamen-radio-option">
                          <input
                            type="radio"
                            name="dictamen_resultado"
                            value="RECHAZADO"
                            checked={dictamenForm.resultado === "RECHAZADO"}
                            onChange={(e) =>
                              setDictamenForm((f) => ({ ...f, resultado: e.target.value }))
                            }
                          />
                          <StatusChip variant="error" label="RECHAZADO" />
                        </label>
                        <label className="dictamen-radio-option">
                          <input
                            type="radio"
                            name="dictamen_resultado"
                            value="PENDIENTE_DOCS"
                            checked={dictamenForm.resultado === "PENDIENTE_DOCS"}
                            onChange={(e) =>
                              setDictamenForm((f) => ({ ...f, resultado: e.target.value }))
                            }
                          />
                          <StatusChip variant="warning" label="PENDIENTE_DOCS" />
                        </label>
                      </div>
                    </FormField>
                    <FormField label="Justificación" htmlFor="dictamen_justificacion" span={12}>
                      <textarea
                        id="dictamen_justificacion"
                        name="dictamen_justificacion"
                        placeholder="Detallá los motivos del dictamen..."
                        value={dictamenForm.justificacion}
                        onChange={(e) =>
                          setDictamenForm((f) => ({ ...f, justificacion: e.target.value }))
                        }
                        required
                      />
                    </FormField>
                  </div>
                  <div className="form-actions">
                    {dictamenStatus && (
                      <span className={`status ${dictamenStatus.type}`}>
                        {dictamenStatus.message}
                      </span>
                    )}
                    <div className="buttons">
                      <button
                        type="submit"
                        className="btn-primary"
                        disabled={!dictamenForm.resultado || !dictamenForm.justificacion}
                      >
                        Registrar dictamen
                      </button>
                    </div>
                  </div>
                </form>
              </>
            )}

            <div style={{ marginTop: "28px", borderTop: "1px solid rgba(213,219,229,0.9)", paddingTop: "24px" }}>
              <CardHeader
                eyebrow="Historial"
                title="Correcciones"
                description="Correcciones realizadas sobre esta prescripción."
              />

              {!showCorrectionForm ? (
                <div style={{ marginBottom: "16px" }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowCorrectionForm(true)}
                  >
                    + Agregar corrección
                  </button>
                </div>
              ) : (
                <form className="correction-form" onSubmit={handleCorrectionSubmit}>
                  <div className="form-grid">
                    <FormField label="Campo" htmlFor="corr_campo" span={4}>
                      <select
                        id="corr_campo"
                        name="corr_campo"
                        value={correctionForm.campo}
                        onChange={(e) =>
                          setCorrectionForm((f) => ({ ...f, campo: e.target.value }))
                        }
                        required
                      >
                        <option value="" disabled>Seleccionar campo</option>
                        {CAMPO_OPTIONS.map((campo) => (
                          <option key={campo} value={campo}>{campo}</option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Valor nuevo" htmlFor="corr_valor" span={4}>
                      <input
                        id="corr_valor"
                        name="corr_valor"
                        type="text"
                        placeholder="Nuevo valor"
                        value={correctionForm.valor_nuevo}
                        onChange={(e) =>
                          setCorrectionForm((f) => ({ ...f, valor_nuevo: e.target.value }))
                        }
                        required
                      />
                    </FormField>
                    <FormField label="Justificación" htmlFor="corr_justificacion" span={4}>
                      <input
                        id="corr_justificacion"
                        name="corr_justificacion"
                        type="text"
                        placeholder="Motivo de la corrección"
                        value={correctionForm.justificacion}
                        onChange={(e) =>
                          setCorrectionForm((f) => ({ ...f, justificacion: e.target.value }))
                        }
                        required
                      />
                    </FormField>
                  </div>
                  <div className="form-actions">
                    {correctionStatus && (
                      <span className={`status ${correctionStatus.type}`}>
                        {correctionStatus.message}
                      </span>
                    )}
                    <div className="buttons">
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setShowCorrectionForm(false);
                          setCorrectionStatus(null);
                        }}
                      >
                        Cancelar
                      </button>
                      <button type="submit" className="btn-primary">
                        Guardar corrección
                      </button>
                    </div>
                  </div>
                </form>
              )}

              <DataTable
                columns={CORRECTION_COLUMNS}
                rows={corrections}
                renderRow={renderCorrectionRow}
                emptyText="No hay correcciones registradas para este caso."
              />
            </div>
          </section>
        </section>
      </main>
    </>
  );
}
