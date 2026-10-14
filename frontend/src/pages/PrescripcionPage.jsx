import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import ReadOnlyField from "../components/ReadOnlyField";
import SimpleTable from "../components/SimpleTable";
import StatusChip from "../components/StatusChip";
import MlVerdictPanel from "../components/MlVerdictPanel";
import useFormStatus from "../hooks/useFormStatus";
import { ESTADO_VARIANT, estadoLabel } from "../constants/estadoVariant";
import { createPrescription, fetchDosisReferencia, fetchRegimenes, recomendarRegimen } from "../api/prescriptions";
import { fetchPatient } from "../api/patients";
import { formatCurrency } from "../utils/format";

function bodySurfaceArea(pesoKg, tallaCm) {
  const peso = Number(pesoKg);
  const talla = Number(tallaCm);
  if (!peso || !talla) return null;
  return Math.sqrt((talla * peso) / 3600).toFixed(2);
}

const PACIENTE_INICIAL = { estado: "idle", texto: "" };

export default function PrescripcionPage() {
  const formRef = useRef(null);
  const resultRef = useRef(null);
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();
  const [result, setResult] = useState(null);
  const [preview, setPreview] = useState({ peso: "", talla: "" });
  const [regimenes, setRegimenes] = useState([]);
  const [regimenesError, setRegimenesError] = useState(null);
  const [idRegimen, setIdRegimen] = useState("");
  const [dosisRows, setDosisRows] = useState([]);
  const [guia, setGuia] = useState({ estado: "idle", texto: "" });
  // RF-34: se activa cuando el motor detecta una alternativa terapeuticamente
  // equivalente de menor costo y el alta fue rechazada por falta de
  // justificacion clinica.
  const [requiereJustificacion, setRequiereJustificacion] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  // Verificación del ID de paciente contra el padrón (el backend vuelve a
  // validarlo: es solo una ayuda para detectar el error antes de enviar).
  const [paciente, setPaciente] = useState(PACIENTE_INICIAL);
  const pacienteConsultaRef = useRef(0);

  const superficie = useMemo(() => bodySurfaceArea(preview.peso, preview.talla), [preview]);

  useEffect(() => {
    fetchRegimenes()
      .then((items) => {
        setRegimenes(items);
        setRegimenesError(null);
      })
      .catch((err) => {
        setRegimenes([]);
        setRegimenesError(err.message || "No se pudo cargar el catálogo de regímenes.");
      });
  }, []);

  // Dosis de referencia: se recalculan con régimen + peso + talla y se vacían
  // si falta alguno (antes quedaban las de la combinación anterior).
  useEffect(() => {
    if (!idRegimen || !Number(preview.peso) || !Number(preview.talla)) {
      setDosisRows([]);
      return undefined;
    }
    let vigente = true;
    fetchDosisReferencia(idRegimen, Number(preview.peso), Number(preview.talla))
      .then((rows) => {
        if (vigente) setDosisRows((rows || []).map((row) => ({ ...row, dosis_mg: String(row.dosis_mg) })));
      })
      .catch(() => {
        if (vigente) setDosisRows([]);
      });
    return () => {
      vigente = false;
    };
  }, [idRegimen, preview.peso, preview.talla]);

  async function verificarPaciente(rawId) {
    const id = Number(rawId);
    const consulta = ++pacienteConsultaRef.current;
    if (!rawId || !Number.isInteger(id) || id < 1) {
      setPaciente(PACIENTE_INICIAL);
      return;
    }
    setPaciente({ estado: "loading", texto: "Buscando paciente…" });
    try {
      const p = await fetchPatient(id);
      if (consulta !== pacienteConsultaRef.current) return;
      const nombre = [p.last_name, p.first_name].filter(Boolean).join(", ");
      setPaciente({ estado: "ok", texto: `Paciente: ${nombre || `#${id}`}` });
    } catch (err) {
      if (consulta !== pacienteConsultaRef.current) return;
      setPaciente(
        err.status === 404
          ? { estado: "missing", texto: `No existe un paciente con ID ${id}.` }
          : { estado: "error", texto: "No se pudo verificar el paciente." },
      );
    }
  }

  function updateDosis(index, value) {
    setDosisRows((current) => current.map((row, idx) => (idx === index ? { ...row, dosis_mg: value } : row)));
  }

  async function handleSugerirGuias() {
    const data = new FormData(formRef.current);
    const peso = data.get("peso_kg");
    const talla = data.get("talla_cm");
    const body = {
      estadio: data.get("estadio") || "",
      t: data.get("t") || "",
      n: data.get("n") || "",
      m: data.get("m") || "",
      localizacion_tumor: data.get("localizacion_tumor") || "",
      msi: data.get("msi") || "no_evaluado",
      ras: data.get("ras") || "no_evaluado",
      braf_v600e: data.get("braf_v600e") || "no_evaluado",
      linea_tratamiento: data.get("linea_tratamiento") || "",
    };
    if (peso) body.peso_kg = Number(peso);
    if (talla) body.talla_cm = Number(talla);

    if (!body.estadio) {
      setGuia({ estado: "error", texto: "Completá el estadio para sugerir según guías." });
      document.getElementById("estadio")?.focus();
      return;
    }

    setGuia({ estado: "loading", texto: "Consultando guías clínicas…" });
    try {
      const reco = await recomendarRegimen(body);
      setIdRegimen(reco.id_regimen);
      let texto = `Sugerido ${reco.id_regimen} (${reco.nombre_regimen}) por: ${
        (reco.reglas_aplicadas || []).join(", ") || "guías clínicas"
      }.`;
      if (reco.costo_total != null) texto += ` Costo estimado por ciclo: ${formatCurrency(reco.costo_total)}.`;
      setGuia({ estado: "ok", texto });
    } catch (err) {
      setGuia({ estado: "error", texto: err.message || "No se pudo obtener la sugerencia de guías." });
    }
  }

  function resetFormulario() {
    formRef.current?.reset();
    setPreview({ peso: "", talla: "" });
    setIdRegimen("");
    setDosisRows([]);
    setGuia({ estado: "idle", texto: "" });
    setRequiereJustificacion(false);
    setPaciente(PACIENTE_INICIAL);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    // Un doble clic no puede generar dos prescripciones on-chain.
    if (submittingRef.current) return;
    const data = new FormData(formRef.current);

    const body = {
      patient_id: Number(data.get("patient_id")),
      edad: Number(data.get("edad")),
      sexo: data.get("sexo") || "",
      peso_kg: Number(data.get("peso_kg")),
      talla_cm: Number(data.get("talla_cm")),
      diagnostico_cie10: (data.get("diagnostico_cie10") || "").trim().toUpperCase(),
      localizacion_tumor: data.get("localizacion_tumor") || "",
      tipo_histologico: (data.get("tipo_histologico") || "").trim(),
      t: data.get("t") || "",
      n: data.get("n") || "",
      m: data.get("m") || "",
      estadio: data.get("estadio") || "",
      msi: data.get("msi") || "no_evaluado",
      ras: data.get("ras") || "no_evaluado",
      braf_v600e: data.get("braf_v600e") || "no_evaluado",
      linea_tratamiento: data.get("linea_tratamiento") || "",
      id_regimen: idRegimen || data.get("id_regimen") || "",
      dosis_por_farmaco: dosisRows.map((row) => ({
        monodroga: row.monodroga,
        dosis_mg: Number(row.dosis_mg) || 0,
      })),
      medico_prescriptor: (data.get("medico_prescriptor") || "").trim(),
      matricula: (data.get("matricula") || "").trim(),
    };

    const justificacionCosto = (data.get("justificacion_costo") || "").trim();
    if (justificacionCosto) {
      body.justificacion_costo = justificacionCosto;
    }

    setLoading("Validando y registrando en la blockchain (endoso de las 3 organizaciones)…");
    setResult(null);
    submittingRef.current = true;
    setSubmitting(true);

    try {
      const created = await createPrescription(body);
      setSuccess(`Prescripción ${created.prescription_code} registrada en la blockchain.`);
      setResult(created);
      resetFormulario();
      // El resultado queda debajo del formulario: se lo trae a la vista.
      requestAnimationFrame(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) {
      const mensaje = err.message || "Ocurrió un error al registrar la prescripción.";
      // RF-34: el backend exige justificar el esquema cuando hay una
      // alternativa equivalente más económica.
      if (err.status === 422 && mensaje.includes("justificacion_costo")) {
        setRequiereJustificacion(true);
        setError(
          "Existe una alternativa terapéuticamente equivalente de menor costo. " +
            "Completá la justificación clínica para registrar el esquema elegido.",
        );
        document.getElementById("justificacion_costo")?.focus();
      } else {
        setError(mensaje);
      }
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  function handleCancel() {
    resetFormulario();
    setResult(null);
    clear();
  }

  const pacienteHintClass =
    paciente.estado === "missing" || paciente.estado === "error"
      ? " field-hint--error"
      : paciente.estado === "ok"
        ? " field-hint--ok"
        : "";

  return (
    <>
      <TopBar
        title="Alta de prescripción"
        subtitle="Prescripciones oncológicas de alta complejidad (caso piloto: cáncer de colon) con validación híbrida y registro en blockchain."
        badge="Prescripciones"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="content-stack">
            <form ref={formRef} className="card card-form" onSubmit={handleSubmit}>
              <CardHeader
                split
                eyebrow="Paciente"
                title="Datos del paciente"
                description="Completá los atributos clínicos, elegí el régimen (opcionalmente sugerido por guías) y validá con el motor híbrido."
                badge="Cáncer de colon"
              />

              <div className="form-grid">
                <FormField label="ID Paciente" htmlFor="patient_id" required span={4}>
                  <input
                    id="patient_id"
                    name="patient_id"
                    type="number"
                    min="1"
                    step="1"
                    placeholder="Ej.: 1"
                    required
                    aria-describedby="patient_id_hint"
                    onBlur={(e) => verificarPaciente(e.target.value)}
                  />
                  <p id="patient_id_hint" className={`field-hint${pacienteHintClass}`} aria-live="polite">
                    {paciente.texto || "ID del padrón de pacientes."}
                  </p>
                </FormField>
                <FormField label="Edad" htmlFor="edad" required span={2}>
                  <input id="edad" name="edad" type="number" min="0" max="120" placeholder="65" required />
                </FormField>
                <FormField label="Sexo" htmlFor="sexo" required span={3}>
                  <select id="sexo" name="sexo" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="Masculino">Masculino</option>
                    <option value="Femenino">Femenino</option>
                  </select>
                </FormField>
                <FormField label="Diagnóstico (CIE-10)" htmlFor="diagnostico_cie10" required span={3}>
                  <input
                    id="diagnostico_cie10"
                    name="diagnostico_cie10"
                    type="text"
                    placeholder="Ej.: C18.9"
                    maxLength={16}
                    required
                  />
                </FormField>

                <FormField label="Peso (kg)" htmlFor="peso_kg" required span={3}>
                  <input
                    id="peso_kg"
                    name="peso_kg"
                    type="number"
                    step="0.1"
                    min="1"
                    max="400"
                    placeholder="72"
                    required
                    onChange={(e) => setPreview((p) => ({ ...p, peso: e.target.value }))}
                  />
                </FormField>
                <FormField label="Talla (cm)" htmlFor="talla_cm" required span={3}>
                  <input
                    id="talla_cm"
                    name="talla_cm"
                    type="number"
                    step="0.1"
                    min="1"
                    max="260"
                    placeholder="170"
                    required
                    onChange={(e) => setPreview((p) => ({ ...p, talla: e.target.value }))}
                  />
                </FormField>
                <ReadOnlyField
                  label="Superficie corporal (Mosteller)"
                  value={superficie ? `${superficie} m²` : "Se calcula con peso y talla"}
                  span={6}
                />
              </div>

              <CardHeader
                eyebrow="Estadificación TNM"
                title="Clasificación del tumor"
                description="Localización, histología y estadificación TNM."
              />
              <div className="form-grid">
                <FormField label="Localización del tumor" htmlFor="localizacion_tumor" required span={4}>
                  <select id="localizacion_tumor" name="localizacion_tumor" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="Colon derecho">Colon derecho</option>
                    <option value="Colon izquierdo">Colon izquierdo</option>
                    <option value="Colon transverso">Colon transverso</option>
                  </select>
                </FormField>
                <FormField label="Tipo histológico" htmlFor="tipo_histologico" required span={4}>
                  <input
                    id="tipo_histologico"
                    name="tipo_histologico"
                    type="text"
                    placeholder="Ej.: Adenocarcinoma"
                    maxLength={200}
                    required
                  />
                </FormField>
                <FormField label="Estadio" htmlFor="estadio" required span={4}>
                  <select id="estadio" name="estadio" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="I">I</option>
                    <option value="II">II</option>
                    <option value="III">III</option>
                    <option value="IV">IV</option>
                  </select>
                </FormField>
                <FormField label="T (tumor primario)" htmlFor="t" required span={4}>
                  <select id="t" name="t" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="T1">T1</option>
                    <option value="T2">T2</option>
                    <option value="T3">T3</option>
                    <option value="T4">T4</option>
                  </select>
                </FormField>
                <FormField label="N (ganglios)" htmlFor="n" required span={4}>
                  <select id="n" name="n" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="N0">N0</option>
                    <option value="N1">N1</option>
                    <option value="N2">N2</option>
                  </select>
                </FormField>
                <FormField label="M (metástasis)" htmlFor="m" required span={4}>
                  <select id="m" name="m" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="M0">M0</option>
                    <option value="M1">M1</option>
                    <option value="MX">MX</option>
                  </select>
                </FormField>
              </div>

              <CardHeader
                eyebrow="Biomarcadores"
                title="Marcadores moleculares"
                description="Tres estados: si no fue evaluado no se asume wild type."
              />
              <div className="form-grid">
                <FormField label="MSI" htmlFor="msi" required span={4}>
                  <select id="msi" name="msi" required defaultValue="no_evaluado">
                    <option value="no_evaluado">No evaluado</option>
                    <option value="MSI-H">MSI-H</option>
                    <option value="MSS">MSS</option>
                  </select>
                </FormField>
                <FormField label="RAS" htmlFor="ras" required span={4}>
                  <select id="ras" name="ras" required defaultValue="no_evaluado">
                    <option value="no_evaluado">No evaluado</option>
                    <option value="wild_type">Wild type</option>
                    <option value="mutado">Mutado</option>
                  </select>
                </FormField>
                <FormField label="BRAF V600E" htmlFor="braf_v600e" required span={4}>
                  <select id="braf_v600e" name="braf_v600e" required defaultValue="no_evaluado">
                    <option value="no_evaluado">No evaluado</option>
                    <option value="wild_type">Wild type / ausente</option>
                    <option value="presente">Presente</option>
                  </select>
                </FormField>
              </div>

              <CardHeader
                eyebrow="Prescripción"
                title="Régimen y dosificación"
                description="Podés pedir una sugerencia según guías; el esquema elegido se audita con el modelo ML."
              />
              <div className="form-grid">
                <FormField label="Línea de tratamiento" htmlFor="linea_tratamiento" required span={4}>
                  <select id="linea_tratamiento" name="linea_tratamiento" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar
                    </option>
                    <option value="Primera">Primera</option>
                    <option value="Segunda">Segunda</option>
                  </select>
                </FormField>
                <FormField label="Régimen" htmlFor="id_regimen" required span={5}>
                  <select
                    id="id_regimen"
                    name="id_regimen"
                    required
                    value={idRegimen}
                    onChange={(e) => setIdRegimen(e.target.value)}
                  >
                    <option value="" disabled>
                      {regimenesError ? "Catálogo no disponible" : "Seleccionar"}
                    </option>
                    {regimenes.map((reg) => (
                      <option key={reg.id_regimen} value={reg.id_regimen}>
                        {reg.id_regimen} — {reg.nombre}
                      </option>
                    ))}
                  </select>
                  {regimenesError ? <p className="field-hint field-hint--error">{regimenesError}</p> : null}
                </FormField>
                <div className="form-group form-group--action field-span-3">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleSugerirGuias}
                    disabled={guia.estado === "loading"}
                  >
                    {guia.estado === "loading" ? "Consultando…" : "Sugerir según guías"}
                  </button>
                </div>
                {guia.texto ? (
                  <div className="field-span-12">
                    <div
                      className={`alert ${guia.estado === "error" ? "alert--error" : guia.estado === "ok" ? "alert--info" : ""}`}
                      role={guia.estado === "error" ? "alert" : "status"}
                    >
                      {guia.texto}
                    </div>
                  </div>
                ) : null}
              </div>

              {dosisRows.length > 0 && (
                <section className="ml-panel__section">
                  <h3 className="ml-panel__title">Dosis por fármaco</h3>
                  <p className="muted">Calculadas por superficie corporal; podés ajustarlas antes de registrar.</p>
                  <SimpleTable
                    caption="Dosis por fármaco"
                    columns={["Monodroga", "Dosis (mg)"]}
                    rows={dosisRows}
                    renderRow={(row, index) => (
                      <tr key={row.monodroga}>
                        <td>{row.monodroga}</td>
                        <td>
                          <input
                            type="number"
                            min="0"
                            step="any"
                            value={row.dosis_mg}
                            aria-label={`Dosis de ${row.monodroga} en mg`}
                            onChange={(e) => updateDosis(index, e.target.value)}
                          />
                        </td>
                      </tr>
                    )}
                  />
                </section>
              )}

              <div className="form-grid">
                <FormField label="Médico prescriptor" htmlFor="medico_prescriptor" required span={8}>
                  <input
                    id="medico_prescriptor"
                    name="medico_prescriptor"
                    type="text"
                    placeholder="Ej.: Dr. Juan Pérez"
                    maxLength={200}
                    required
                  />
                </FormField>
                <FormField label="Matrícula" htmlFor="matricula" required span={4}>
                  <input id="matricula" name="matricula" type="text" placeholder="MN 12345" maxLength={50} required />
                </FormField>

                <FormField
                  label={
                    requiereJustificacion
                      ? "Justificación clínica de la elección económica"
                      : "Justificación clínica de la elección económica (opcional)"
                  }
                  htmlFor="justificacion_costo"
                  required={requiereJustificacion}
                  span={12}
                >
                  <textarea
                    id="justificacion_costo"
                    name="justificacion_costo"
                    rows={3}
                    minLength={5}
                    maxLength={2000}
                    required={requiereJustificacion}
                    className={requiereJustificacion ? "is-required-now" : undefined}
                    placeholder={
                      requiereJustificacion
                        ? "Existe una alternativa equivalente más económica. Indicá la razón clínica por la que se prescribe el esquema elegido."
                        : "Solo se exige si el motor detecta una alternativa equivalente de menor costo."
                    }
                  />
                  {requiereJustificacion ? (
                    <p className="field-hint">
                      La justificación queda registrada de forma inmutable junto con la prescripción y acompaña al
                      expediente durante la auditoría.
                    </p>
                  ) : null}
                </FormField>
              </div>

              <FormActions
                status={status}
                onCancel={handleCancel}
                cancelLabel="Limpiar"
                submitLabel="Validar y registrar"
                submitting={submitting}
                submittingLabel="Registrando en blockchain…"
              />
            </form>

            {result && (
              <section className="card card-form" ref={resultRef} tabIndex={-1}>
                <CardHeader
                  split
                  eyebrow="Registrada en blockchain"
                  title={`Prescripción ${result.prescription_code}`}
                  description="Asset inmutable en Hyperledger Fabric, endosado por las 3 organizaciones. Queda pendiente de auditoría; el veredicto del modelo es soporte de decisión."
                  badge={`Superficie: ${result.clinical?.superficie_corporal_m2 ?? "—"} m²`}
                />
                <div className="form-grid">
                  <ReadOnlyField label="Estado on-chain" span={4}>
                    <StatusChip variant={ESTADO_VARIANT[result.estado] || "neutral"} label={estadoLabel(result.estado)} />
                  </ReadOnlyField>
                  <ReadOnlyField label="TxID de Fabric" value={result.tx_id} span={8} mono copyable />
                  <ReadOnlyField label="Hash del contenido" value={result.payload_hash} span={12} mono copyable />
                </div>
                <MlVerdictPanel ml={result.ml} />
                <div className="form-actions">
                  <div className="buttons">
                    <Link
                      to={`/trazabilidad?id=${encodeURIComponent(result.prescription_id)}`}
                      className="btn-secondary btn-as-link"
                    >
                      Ver trazabilidad
                    </Link>
                  </div>
                </div>
              </section>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
