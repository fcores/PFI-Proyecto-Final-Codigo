import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { bulkImportMonodrugs, createMonodrug } from "../api/monodrugs";

export default function MonodrogasPage() {
  const { formRef, status, handleSubmit, handleCancel } = useFormSubmit({
    submitFn: createMonodrug,
    loadingMsg: "Guardando monodroga...",
    successMsg: "Monodroga creada correctamente.",
    errorMsg: "Ocurrió un error al guardar la monodroga.",
  });

  return (
    <>
      <TopBar
        title="Alta de monodrogas"
        subtitle="Gestioná el maestro de monodrogas con alta individual o carga masiva por Excel."
        badge="Monodrogas"
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
                eyebrow="Maestro farmacológico"
                title="Datos de la monodroga"
                description="Completá la descripción y el ID SAP para dejar la monodroga disponible para relacionarla con medicamentos."
                badge="Formulario guiado"
              />

              <div className="form-grid">
                <FormField label="Descripción" htmlFor="descripcion" required span={8}>
                  <input
                    id="descripcion"
                    name="descripcion"
                    type="text"
                    placeholder="Ej.: Adalimumab"
                    required
                  />
                </FormField>

                <FormField label="ID SAP" htmlFor="sap_id" required span={4}>
                  <input
                    id="sap_id"
                    name="sap_id"
                    type="text"
                    placeholder="Ej.: MONO-SAP-001"
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
              title="Importar monodrogas desde Excel"
              description="Cargá múltiples monodrogas en una sola operación usando un archivo Excel con descripción e ID SAP."
              importFn={bulkImportMonodrugs}
              templateHint="descripcion, sap_id"
            />
          </section>
        </section>
      </main>
    </>
  );
}
