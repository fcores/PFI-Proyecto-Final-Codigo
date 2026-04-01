import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { bulkImportMedications, createMedication } from "../api/medications";

export default function AltaMedicamentosPage() {
  const { formRef, status, handleSubmit, handleCancel } = useFormSubmit({
    submitFn: createMedication,
    loadingMsg: "Guardando medicamento...",
    successMsg: "Medicamento creado correctamente.",
    errorMsg: "Ocurrió un error al guardar el medicamento.",
  });

  return (
    <>
      <TopBar
        title="Alta de medicamentos"
        subtitle="Registrá materiales y medicamentos con sus códigos maestros, datos de conservación y referencias operativas."
        badge="Medicamentos"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="content-stack">
            <form
              ref={formRef}
              className="card card-form"
              onSubmit={handleSubmit}
            >
              <CardHeader
                split
                eyebrow="Maestro de materiales"
                title="Datos del medicamento"
                description="Completá los identificadores principales para dejar el material disponible para consulta y operación."
                badge="Formulario guiado"
              />

              <div className="form-grid">
                <FormField label="Descripción" htmlFor="descripcion" required span={6}>
                  <input
                    id="descripcion"
                    name="descripcion"
                    type="text"
                    placeholder="Ej.: Adalimumab 40 mg jeringa prellenada"
                    required
                  />
                </FormField>

                <FormField label="EAN" htmlFor="ean" required span={3}>
                  <input
                    id="ean"
                    name="ean"
                    type="text"
                    placeholder="Ej.: 7791234567890"
                    required
                  />
                </FormField>

                <FormField label="Código Alfabeta" htmlFor="codigo_alfabeta" required span={3}>
                  <input
                    id="codigo_alfabeta"
                    name="codigo_alfabeta"
                    type="text"
                    placeholder="Ej.: ALF12345"
                    required
                  />
                </FormField>

                <FormField label="Tipo de conservación" htmlFor="tipo_conservacion" required span={3}>
                  <select id="tipo_conservacion" name="tipo_conservacion" required defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="seco">Seco</option>
                    <option value="frio">Frío</option>
                  </select>
                </FormField>

                <FormField label="ID SAP" htmlFor="sap_id" required span={3}>
                  <input
                    id="sap_id"
                    name="sap_id"
                    type="text"
                    placeholder="Ej.: SAP000123"
                    required
                  />
                </FormField>

                <FormField label="ID de monodroga" htmlFor="monodroga_id" required span={3}>
                  <input
                    id="monodroga_id"
                    name="monodroga_id"
                    type="text"
                    placeholder="Ej.: MONO456"
                    required
                  />
                </FormField>

                <FormField label="Tamaño / dimensión" htmlFor="tamano_dimension" required span={3}>
                  <input
                    id="tamano_dimension"
                    name="tamano_dimension"
                    type="text"
                    placeholder="Ej.: 10 x 20 cm / 40 mg"
                    required
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
              title="Importar medicamentos desde Excel"
              description="Cargá múltiples materiales en el maestro de medicamentos a través de un único archivo Excel."
              importFn={bulkImportMedications}
              templateHint="descripcion, ean, codigo_alfabeta, tipo_conservacion, sap_id, monodroga_id, tamano_dimension"
            />
          </section>
        </section>
      </main>
    </>
  );
}
