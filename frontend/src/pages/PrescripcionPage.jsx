import { useMemo, useRef, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import StatusChip from "../components/StatusChip";
import useFormStatus from "../hooks/useFormStatus";
import { createPrescription } from "../api/prescriptions";

const ESTADO_VARIANT = {
  APROBADO: "success",
  REVISION: "warning",
  RECHAZADO: "error",
};

function bodySurfaceArea(pesoKg, tallaCm) {
  const peso = Number(pesoKg);
  const talla = Number(tallaCm);
  if (!peso || !talla) return null;
  return Math.sqrt((talla * peso) / 3600).toFixed(2);
}

export default function PrescripcionPage() {
  const formRef = useRef(null);
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();
  const [result, setResult] = useState(null);
  const [preview, setPreview] = useState({ peso: "", talla: "" });

  const superficie = useMemo(
    () => bodySurfaceArea(preview.peso, preview.talla),
    [preview],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    const form = formRef.current;
    const data = new FormData(form);

    const body = {
      patient_sap_id: (data.get("patient_sap_id") || "").trim(),
      edad: Number(data.get("edad")),
      sexo: data.get("sexo") || "",
      peso_kg: Number(data.get("peso_kg")),
      talla_cm: Number(data.get("talla_cm")),
      diagnostico_cie10: (data.get("diagnostico_cie10") || "").trim(),
      localizacion_tumor: data.get("localizacion_tumor") || "",
      tipo_histologico: (data.get("tipo_histologico") || "").trim(),
      t: data.get("t") || "",
      n: data.get("n") || "",
      m: data.get("m") || "",
      estadio: data.get("estadio") || "",
      msi_alta: data.get("msi_alta") === "on",
      ras_mutado: data.get("ras_mutado") === "on",
      braf_v600e: data.get("braf_v600e") === "on",
      linea_tratamiento: data.get("linea_tratamiento") || "",
      esquema: (data.get("esquema") || "").trim(),
      dosis_mg_m2: Number(data.get("dosis_mg_m2")),
      medico_prescriptor: (data.get("medico_prescriptor") || "").trim(),
      matricula: (data.get("matricula") || "").trim(),
    };

    setLoading("Validando y registrando prescripción...");
    setResult(null);

    try {
      const created = await createPrescription(body);
      setSuccess(`Prescripción ${created.prescription_code} registrada.`);
      setResult(created);
      form.reset();
      setPreview({ peso: "", talla: "" });
    } catch (err) {
      setError(err.message || "Ocurrió un error al registrar la prescripción.");
    }
  }

  function handleCancel() {
    formRef.current.reset();
    setPreview({ peso: "", talla: "" });
    setResult(null);
    clear();
  }

  return (
    <>
      <TopBar
        title="Alta de prescripción de alta complejidad"
        subtitle="Registro de prescripciones oncológicas (caso piloto: cáncer de colon) con validación y trazabilidad en blockchain."
        badge="Prescripciones"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="content-stack">
            <form ref={formRef} className="card card-form" onSubmit={handleSubmit}>
              <CardHeader
                split
                eyebrow="Auditoría de prescripciones"
                title="Datos clínicos y prescripción"
                description="Completá los atributos clínicos del paciente y el esquema prescrito. El sistema ejecuta una validación preliminar y registra la operación en el ledger."
                badge="Cáncer de colon"
              />

              <div className="form-grid">
                <FormField label="ID Paciente" htmlFor="patient_sap_id" required span={4}>
                  <input id="patient_sap_id" name="patient_sap_id" type="text" placeholder="Ej.: SAP-000123" required />
                </FormField>
                <FormField label="Edad" htmlFor="edad" required span={2}>
                  <input id="edad" name="edad" type="number" min="0" max="120" placeholder="65" required />
                </FormField>
                <FormField label="Sexo" htmlFor="sexo" required span={3}>
                  <select id="sexo" name="sexo" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="Masculino">Masculino</option>
                    <option value="Femenino">Femenino</option>
                  </select>
                </FormField>
                <FormField label="Diagnóstico (CIE-10)" htmlFor="diagnostico_cie10" required span={3}>
                  <input id="diagnostico_cie10" name="diagnostico_cie10" type="text" placeholder="Ej.: C18.9" required />
                </FormField>

                <FormField label="Peso (kg)" htmlFor="peso_kg" required span={3}>
                  <input
                    id="peso_kg"
                    name="peso_kg"
                    type="number"
                    step="0.1"
                    min="0"
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
                    min="0"
                    placeholder="170"
                    required
                    onChange={(e) => setPreview((p) => ({ ...p, talla: e.target.value }))}
                  />
                </FormField>
                <FormField label="Superficie corporal (m²)" htmlFor="superficie_preview" span={6}>
                  <input
                    id="superficie_preview"
                    type="text"
                    value={superficie ? `${superficie} m² (Mosteller)` : "Se calcula con peso y talla"}
                    readOnly
                  />
                </FormField>
              </div>

              <CardHeader
                eyebrow="Estadificación TNM"
                title="Clasificación del tumor"
                description="Localización, histología y estadificación TNM."
              />
              <div className="form-grid">
                <FormField label="Localización del tumor" htmlFor="localizacion_tumor" required span={4}>
                  <select id="localizacion_tumor" name="localizacion_tumor" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="Colon derecho">Colon derecho</option>
                    <option value="Colon izquierdo">Colon izquierdo</option>
                  </select>
                </FormField>
                <FormField label="Tipo histológico" htmlFor="tipo_histologico" required span={4}>
                  <input id="tipo_histologico" name="tipo_histologico" type="text" placeholder="Ej.: Adenocarcinoma" required />
                </FormField>
                <FormField label="Estadio" htmlFor="estadio" required span={4}>
                  <select id="estadio" name="estadio" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="I">I</option>
                    <option value="II">II</option>
                    <option value="III">III</option>
                    <option value="IV">IV</option>
                  </select>
                </FormField>
                <FormField label="T (tumor primario)" htmlFor="t" required span={4}>
                  <select id="t" name="t" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="T1">T1</option>
                    <option value="T2">T2</option>
                    <option value="T3">T3</option>
                    <option value="T4">T4</option>
                  </select>
                </FormField>
                <FormField label="N (ganglios)" htmlFor="n" required span={4}>
                  <select id="n" name="n" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="N0">N0</option>
                    <option value="N1">N1</option>
                    <option value="N2">N2</option>
                  </select>
                </FormField>
                <FormField label="M (metástasis)" htmlFor="m" required span={4}>
                  <select id="m" name="m" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="M0">M0</option>
                    <option value="M1">M1</option>
                  </select>
                </FormField>
              </div>

              <CardHeader
                eyebrow="Biomarcadores"
                title="Marcadores moleculares"
                description="Condicionan el esquema terapéutico."
              />
              <div className="form-grid">
                <FormField label="MSI-alta" htmlFor="msi_alta" span={4}>
                  <label className="checkbox-inline">
                    <input id="msi_alta" name="msi_alta" type="checkbox" /> Inestabilidad microsatelital alta
                  </label>
                </FormField>
                <FormField label="Mutación RAS" htmlFor="ras_mutado" span={4}>
                  <label className="checkbox-inline">
                    <input id="ras_mutado" name="ras_mutado" type="checkbox" /> KRAS/NRAS mutado
                  </label>
                </FormField>
                <FormField label="Mutación BRAF V600E" htmlFor="braf_v600e" span={4}>
                  <label className="checkbox-inline">
                    <input id="braf_v600e" name="braf_v600e" type="checkbox" /> BRAF V600E presente
                  </label>
                </FormField>
              </div>

              <CardHeader
                eyebrow="Prescripción"
                title="Esquema y dosificación"
                description="Esquema prescrito, dosis en mg/m² y datos del prescriptor."
              />
              <div className="form-grid">
                <FormField label="Línea de tratamiento" htmlFor="linea_tratamiento" required span={4}>
                  <select id="linea_tratamiento" name="linea_tratamiento" required defaultValue="">
                    <option value="" disabled>Seleccionar</option>
                    <option value="Primera">Primera</option>
                    <option value="Segunda">Segunda</option>
                  </select>
                </FormField>
                <FormField label="Esquema / medicamento" htmlFor="esquema" required span={5}>
                  <input id="esquema" name="esquema" type="text" placeholder="Ej.: FOLFOX + Bevacizumab" required />
                </FormField>
                <FormField label="Dosis (mg/m²)" htmlFor="dosis_mg_m2" required span={3}>
                  <input id="dosis_mg_m2" name="dosis_mg_m2" type="number" step="0.1" min="0" placeholder="85" required />
                </FormField>
                <FormField label="Médico prescriptor" htmlFor="medico_prescriptor" required span={8}>
                  <input id="medico_prescriptor" name="medico_prescriptor" type="text" placeholder="Ej.: Dr. Juan Pérez" required />
                </FormField>
                <FormField label="Matrícula" htmlFor="matricula" required span={4}>
                  <input id="matricula" name="matricula" type="text" placeholder="MN 12345" required />
                </FormField>
              </div>

              <FormActions status={status} onCancel={handleCancel} submitLabel="✅ Validar y registrar" />
            </form>

            {result && (
              <section className="card card-form">
                <CardHeader
                  split
                  eyebrow="Resultado de la validación"
                  title={`Prescripción ${result.prescription_code}`}
                  description="Resultado preliminar del motor de validación y registro en la blockchain simulada."
                  badge={`Superficie: ${result.superficie_corporal_m2} m²`}
                />
                <div className="form-grid">
                  <FormField label="Estado" htmlFor="result_estado" span={4}>
                    <div>
                      <StatusChip
                        variant={ESTADO_VARIANT[result.validacion.estado] || "neutral"}
                        label={result.validacion.estado}
                      />
                    </div>
                  </FormField>
                  <FormField label="Hash del bloque (tx)" htmlFor="result_hash" span={8}>
                    <input id="result_hash" type="text" value={result.blockchain_tx_id || ""} readOnly />
                  </FormField>
                </div>
                <ul className="muted">
                  {result.validacion.motivos.map((motivo, idx) => (
                    <li key={idx}>{motivo}</li>
                  ))}
                </ul>
              </section>
            )}
          </section>
        </section>
      </main>
    </>
  );
}
