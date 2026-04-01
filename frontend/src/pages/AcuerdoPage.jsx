import { useState, useRef } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormStatus from "../hooks/useFormStatus";
import { bulkImportAgreements, createAgreement } from "../api/agreements";

export default function AcuerdoPage() {
  const formRef = useRef(null);
  const contratoRef = useRef(null);
  const [contratoFilename, setContratoFilename] = useState("");
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();

  function handleContratoChange(e) {
    const files = e.target.files;
    setContratoFilename(files.length ? files[0].name : "");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const formData = new FormData(formRef.current);

    if (contratoRef.current?.files.length) {
      formData.append("contrato_file", contratoRef.current.files[0]);
    }

    setLoading("Guardando acuerdo...");

    try {
      await createAgreement(formData);
      setSuccess("Acuerdo creado correctamente.");
      formRef.current.reset();
      setContratoFilename("");
      if (contratoRef.current) contratoRef.current.value = "";
    } catch (error) {
      setError(error.message || "Ocurrió un error al guardar el acuerdo.");
    }
  }

  function handleCancel() {
    formRef.current.reset();
    setContratoFilename("");
    if (contratoRef.current) contratoRef.current.value = "";
    clear();
  }

  return (
    <>
      <TopBar
        title="Nuevo acuerdo"
        subtitle="Configurá el convenio operativo, sus fechas y la documentación contractual en una experiencia más clara."
        badge="Acuerdos"
      />
      <main className="page page--wide">
        <section className="layout layout-acuerdo">
          <section className="content-stack">
            <form
              ref={formRef}
              className="card card-acuerdo-form"
              encType="multipart/form-data"
              onSubmit={handleSubmit}
            >
              <CardHeader
                split
                eyebrow="Configuración comercial"
                title="Detalle del acuerdo"
                description="Definí laboratorio, prestador, vigencia y condición de recupero desde un layout más limpio y legible."
                badge="Gestión operativa"
              />

              <div className="form-grid form-grid--agreement">
                <FormField label="Laboratorio" htmlFor="laboratorio" required span={6}>
                  <select id="laboratorio" name="laboratorio" required defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="lab_a">Laboratorio A</option>
                    <option value="lab_b">Laboratorio B</option>
                  </select>
                </FormField>

                <FormField label="Prestador" htmlFor="prestador" required span={6}>
                  <select id="prestador" name="prestador" required defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="hospital_central">Hospital Central</option>
                    <option value="clinica_norte">Clínica del Norte</option>
                  </select>
                </FormField>

                <FormField label="Medicamento" htmlFor="medicamento" required span={6}>
                  <select id="medicamento" name="medicamento" required defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="med_a">Medicamento A</option>
                    <option value="med_b">Medicamento B</option>
                  </select>
                </FormField>

                <FormField label="Medicamento SAP" htmlFor="medicamento_sap" required span={6}>
                  <input id="medicamento_sap" name="medicamento_sap" type="text" required />
                </FormField>

                <FormField label="Médico auditor" htmlFor="medico_auditor" span={6}>
                  <input id="medico_auditor" name="medico_auditor" type="text" />
                </FormField>

                <FormField label="Rango de fecha" span={6}>
                  <div className="date-range">
                    <div className="form-group-inline">
                      <label htmlFor="fecha_inicial" className="sr-only">Fecha inicial</label>
                      <input id="fecha_inicial" name="fecha_inicial" type="date" placeholder="Fecha inicial" />
                    </div>
                    <div className="form-group-inline">
                      <label htmlFor="fecha_final" className="sr-only">Fecha final</label>
                      <input id="fecha_final" name="fecha_final" type="date" placeholder="Fecha final" />
                    </div>
                  </div>
                </FormField>

                <FormField label="Condición de recupero" htmlFor="condicion_recupero" required span={12}>
                  <textarea
                    id="condicion_recupero"
                    name="condicion_recupero"
                    rows={4}
                    required
                    placeholder="Describa la condición de recupero..."
                  />
                </FormField>
              </div>

              <FormActions
                status={status}
                onCancel={handleCancel}
                submitLabel="✅ Agregar"
              />
            </form>

            <BulkImportCard
              title="Importar acuerdos desde Excel"
              description="Cargá múltiples acuerdos de una sola vez mediante un archivo Excel con los datos del convenio."
              importFn={bulkImportAgreements}
              templateHint="laboratorio, prestador, medicamento, medicamento_sap, medico_auditor, fecha_inicial, fecha_final, condicion_recupero"
            />
          </section>

          <section className="card card-contrato card-sticky">
            <CardHeader
              eyebrow="Respaldo"
              title="📎 Contrato"
              description="Subí el archivo contractual para dejar el acuerdo asociado a su documentación."
            />
            <div className="contrato-upload-zone">
              <input
                ref={contratoRef}
                type="file"
                id="contrato_file"
                name="contrato_file"
                accept=".pdf,.doc,.docx"
                className="contrato-file-input"
                onChange={handleContratoChange}
              />
              <label htmlFor="contrato_file" className="contrato-upload-btn">
                <span className="contrato-upload-icon">⬆️</span>
                Subir contrato
              </label>
              <p className="contrato-hint">
                {contratoFilename || "Arrastrá o hacé clic para subir"}
              </p>
            </div>
          </section>
        </section>
      </main>
    </>
  );
}
