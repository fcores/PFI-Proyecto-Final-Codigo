import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { bulkImportMonodrugs, createMonodrug } from "../api/monodrugs";

export default function MonodrogasPage() {
  const { formRef, status, pending, handleSubmit, handleCancel } = useFormSubmit({
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
                description="Ingresá el nombre de la droga. El código (MONO-XXXX) se genera automáticamente."
                badge="Formulario guiado"
              />

              <div className="form-grid">
                <FormField label="Descripción (nombre de la droga)" htmlFor="descripcion" required span={12}>
                  <input
                    id="descripcion"
                    name="descripcion"
                    type="text"
                    placeholder="Ej.: oxaliplatino, pembrolizumab, capecitabina"
                    required
                  />
                </FormField>
              </div>

              <FormActions
                status={status}
                onCancel={handleCancel}
                submitLabel="Agregar"
                submitting={pending}
              />
            </form>

            <BulkImportCard
              title="Importar monodrogas desde Excel"
              description="Cargá múltiples monodrogas en una sola operación. El código se genera automáticamente."
              importFn={bulkImportMonodrugs}
              templateHint="descripcion"
            />
          </section>
        </section>
      </main>
    </>
  );
}
