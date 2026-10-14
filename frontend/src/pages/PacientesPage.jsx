import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import Accordion from "../components/Accordion";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { bulkImportPatients, createPatient } from "../api/patients";

const ACCORDION_ITEMS = [
  { key: "hc", label: "Historia clínica", placeholder: "Detalle de la historia clínica..." },
  { key: "ap", label: "Anatomía patológica", placeholder: "Detalle de anatomía patológica..." },
  { key: "img", label: "Estudios por imágenes", placeholder: "Detalle de estudios por imágenes..." },
  { key: "lab", label: "Laboratorios", placeholder: "Detalle de laboratorios..." },
  { key: "receta", label: "Receta", placeholder: "Detalle de la receta..." },
  { key: "otros", label: "Otros", placeholder: "Otros detalles..." },
];

export default function PacientesPage() {
  const { formRef, status, pending, handleSubmit, handleCancel } = useFormSubmit({
    submitFn: createPatient,
    loadingMsg: "Guardando paciente...",
    successMsg: "Paciente creado correctamente.",
    errorMsg: "Ocurrió un error al guardar el paciente.",
  });

  return (
    <>
      <TopBar
        title="Alta de pacientes"
        subtitle="Gestioná el alta clínica y la documentación del paciente desde una sola vista."
        badge="Pacientes"
      />
      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="content-stack">
            <form
              ref={formRef}
              className="card card-form"
              encType="multipart/form-data"
              onSubmit={handleSubmit}
            >
              <CardHeader
                split
                eyebrow="Alta clínica"
                title="Datos principales"
                description="Completá los datos administrativos y clínicos del paciente para dejar el registro listo para operar."
                badge="Formulario guiado"
              />

              <div className="form-grid form-grid--patient">
                <FormField label="ID Credencial" htmlFor="credential_id" span={3}>
                  <input id="credential_id" name="credential_id" type="text" />
                </FormField>

                <FormField label="ID Prestador" htmlFor="provider_id" span={3}>
                  <input id="provider_id" name="provider_id" type="text" />
                </FormField>

                <FormField label="Prestador" htmlFor="provider" span={3}>
                  <select id="provider" name="provider" defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="hospital_central">Hospital Central</option>
                    <option value="clinica_norte">Clínica del Norte</option>
                  </select>
                </FormField>

                <FormField label="Nombre" htmlFor="first_name" required span={4}>
                  <input id="first_name" name="first_name" type="text" required />
                </FormField>

                <FormField label="Apellido" htmlFor="last_name" required span={4}>
                  <input id="last_name" name="last_name" type="text" required />
                </FormField>

                <FormField label="Fecha de nacimiento" htmlFor="birth_date" required span={2}>
                  <input id="birth_date" name="birth_date" type="date" required />
                </FormField>

                <FormField label="Género" htmlFor="gender" required span={2}>
                  <select id="gender" name="gender" required defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="femenino">Femenino</option>
                    <option value="masculino">Masculino</option>
                    <option value="otro">Otro</option>
                  </select>
                </FormField>

                <FormField label="Diagnóstico" htmlFor="treatment" span={4}>
                  <input
                    id="treatment"
                    name="treatment"
                    type="text"
                    placeholder="Ej.: Cáncer de colon"
                  />
                </FormField>
              </div>

              <section className="sub-card">
                <header className="sub-card-header">
                  <div>
                    <span className="card-eyebrow">Adjuntos</span>
                    <h2>📄 Documentación</h2>
                    <p className="muted">
                      Adjuntá respaldo clínico y estudios para completar el alta.
                    </p>
                  </div>
                </header>
                <Accordion items={ACCORDION_ITEMS} />
              </section>

              <FormActions
                status={status}
                onCancel={handleCancel}
                submitLabel="Agregar"
                submitting={pending}
              />
            </form>

            <BulkImportCard
              title="Importar pacientes desde Excel"
              description="Cargá múltiples pacientes en una sola operación usando un archivo Excel con los campos del alta clínica."
              importFn={bulkImportPatients}
              templateHint="credential_id, provider_id, provider, first_name, last_name, birth_date, gender, treatment"
            />
          </section>
        </section>
      </main>
    </>
  );
}
