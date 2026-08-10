import { useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { bulkImportMedications, createMedication } from "../api/medications";
import { fetchMonodrugs } from "../api/monodrugs";

export default function AltaMedicamentosPage() {
  const [monodrugs, setMonodrugs] = useState([]);
  const { formRef, status, handleSubmit, handleCancel } = useFormSubmit({
    submitFn: createMedication,
    loadingMsg: "Guardando medicamento...",
    successMsg: "Medicamento creado correctamente.",
    errorMsg: "Ocurrió un error al guardar el medicamento.",
  });

  useEffect(() => {
    fetchMonodrugs()
      .then(setMonodrugs)
      .catch(() => setMonodrugs([]));
  }, []);

  return (
    <>
      <TopBar
        title="Alta de medicamentos"
        subtitle="Registrá presentaciones con los atributos del catálogo (EAN, potencia, laboratorio, precio) y vinculalas a una monodroga."
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
                description="Completá los atributos del catálogo. El código (MED-XXXX) se genera automáticamente."
                badge="Formulario guiado"
              />

              <div className="form-grid">
                <FormField label="Texto Largo de Material" htmlFor="descripcion" required span={8}>
                  <input
                    id="descripcion"
                    name="descripcion"
                    type="text"
                    placeholder="Ej.: TO-OXALIPLATINO** 100 mg iny.f.a.x 1"
                    required
                  />
                </FormField>

                <FormField label="Código EAN/UPC" htmlFor="ean" required span={4}>
                  <input
                    id="ean"
                    name="ean"
                    type="text"
                    placeholder="Ej.: 7791234567890"
                    required
                  />
                </FormField>

                <FormField label="Nro Troquel Alfabeta" htmlFor="codigo_alfabeta" required span={4}>
                  <input
                    id="codigo_alfabeta"
                    name="codigo_alfabeta"
                    type="text"
                    placeholder="Ej.: 2980771"
                    required
                  />
                </FormField>

                <FormField label="Cadena de frío" htmlFor="tipo_conservacion" required span={4}>
                  <select id="tipo_conservacion" name="tipo_conservacion" required defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="seco">Seco</option>
                    <option value="frio">Frío</option>
                  </select>
                </FormField>

                <FormField label="Laboratorio" htmlFor="laboratorio" required span={4}>
                  <input
                    id="laboratorio"
                    name="laboratorio"
                    type="text"
                    placeholder="Ej.: BIOPROFARMA BAGO SA"
                    required
                  />
                </FormField>

                <FormField label="Monodroga" htmlFor="monodroga" required span={6}>
                  <select id="monodroga" name="monodroga" required defaultValue="">
                    <option value="" disabled>Seleccionar monodroga...</option>
                    {monodrugs.map((m) => (
                      <option key={m.id} value={m.descripcion}>
                        {m.descripcion} ({m.codigo})
                      </option>
                    ))}
                  </select>
                </FormField>

                <FormField label="Tamaño / Dimensión" htmlFor="tamano_dimension" required span={6}>
                  <input
                    id="tamano_dimension"
                    name="tamano_dimension"
                    type="text"
                    placeholder="Ej.: 100 MG INY.F.A.X 1"
                    required
                  />
                </FormField>

                <FormField label="Valor de Potencia" htmlFor="potencia_mg" span={3}>
                  <input
                    id="potencia_mg"
                    name="potencia_mg"
                    type="number"
                    step="0.0001"
                    min="0"
                    placeholder="Ej.: 100"
                  />
                </FormField>

                <FormField label="Códigos de Potencia" htmlFor="unidad_potencia" span={3}>
                  <input
                    id="unidad_potencia"
                    name="unidad_potencia"
                    type="text"
                    placeholder="Ej.: MG"
                  />
                </FormField>

                <FormField label="Precio de Venta al Público" htmlFor="precio" span={3}>
                  <input
                    id="precio"
                    name="precio"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Ej.: 12500.00"
                  />
                </FormField>

                <FormField label="Vía de administración" htmlFor="via_administracion" span={3}>
                  <select id="via_administracion" name="via_administracion" defaultValue="">
                    <option value="">Seleccionar...</option>
                    <option value="ORAL">ORAL</option>
                    <option value="INYECTABLE IV">INYECTABLE IV</option>
                    <option value="INYECTABLE">INYECTABLE</option>
                  </select>
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
              description="Usá el archivo Medicamentos v1.xlsx. Si la monodroga no existe, se crea automáticamente."
              importFn={bulkImportMedications}
              templateHint="Tamaño/Dimensión, Código EAN/UPC, Cadena de frío, Nro Troquel alfabeta, Laboratorio, Valor de Potencia, Códigos de Potencia, Código de vías de administración, Código de monodroga, Texto Largo de Material, Precio de Venta al Publico"
            />
          </section>
        </section>
      </main>
    </>
  );
}
