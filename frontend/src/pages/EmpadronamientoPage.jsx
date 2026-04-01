import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { createEnrollment, bulkImportEnrollments } from "../api/enrollments";

const TIPO_LABELS = {
  "tipo-a": "Tipo A",
  "tipo-b": "Tipo B",
};

const MEDICATIONS_OPTIONS = [
  { value: "medicamento_a", label: "Medicamento A" },
  { value: "medicamento_b", label: "Medicamento B" },
  { value: "medicamento_c", label: "Medicamento C" },
  { value: "medicamento_d", label: "Medicamento D" },
  { value: "medicamento_e", label: "Medicamento E" },
];

export default function EmpadronamientoPage() {
  const { tipo } = useParams();
  const label = TIPO_LABELS[tipo] ?? tipo;

  const [selectedMeds, setSelectedMeds] = useState([]);

  useEffect(() => {
    setSelectedMeds([]);
  }, [tipo]);

  const submitFn = useCallback(
    async (formData) => {
      if (selectedMeds.length === 0) {
        throw new Error("Seleccioná al menos un medicamento.");
      }
      const cleaned = new FormData();
      cleaned.append("diagnostico", formData.get("diagnostico"));
      selectedMeds.forEach((m) => cleaned.append("medications", m));
      return createEnrollment(tipo, cleaned);
    },
    [tipo, selectedMeds],
  );

  const onSuccess = useCallback(() => {
    setSelectedMeds([]);
  }, []);

  const { formRef, status, handleSubmit, handleCancel: baseCancel } = useFormSubmit({
    submitFn,
    onSuccess,
    loadingMsg: "Registrando empadronamiento...",
    successMsg: "Empadronamiento registrado correctamente.",
    errorMsg: "Error al registrar el empadronamiento.",
  });

  function handleCancel() {
    setSelectedMeds([]);
    baseCancel();
  }

  function toggleMed(value) {
    setSelectedMeds((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  }

  return (
    <>
      <TopBar
        title={`Empadronamientos ${label}`}
        subtitle={`Alta de empadronamientos ${label}. Registrá el diagnóstico y los medicamentos asignados al esquema de tratamiento.`}
        badge="Empadronamientos"
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
                eyebrow="Nuevo registro"
                title="Datos del empadronamiento"
                description="Completá el diagnóstico y los medicamentos del esquema de tratamiento."
                badge={label}
              />

              <div className="form-grid enrollment-grid">
                <div className="form-group field-span-6">
                  <label>ID de empadronamiento</label>
                  <div className="enrollment-id-preview">
                    <span className="enrollment-id-chip">Auto-generado</span>
                    <span className="enrollment-id-hint">
                      Se asignará al guardar (ej.: EMP-{label.split(" ")[1]}-0001)
                    </span>
                  </div>
                </div>

                <FormField label="Diagnóstico" htmlFor="diagnostico" required span={6}>
                  <input
                    id="diagnostico"
                    name="diagnostico"
                    type="text"
                    placeholder="Ej.: Hipertensión arterial"
                    required
                  />
                </FormField>


                <div className="form-group field-span-12">
                  <label>
                    Medicamentos <span className="required">*</span>
                  </label>
                  <div className="med-checklist">
                    {MEDICATIONS_OPTIONS.map((med) => {
                      const checked = selectedMeds.includes(med.value);
                      return (
                        <label
                          key={med.value}
                          className={`med-chip${checked ? " med-chip--active" : ""}`}
                        >
                          <input
                            type="checkbox"
                            className="sr-only"
                            checked={checked}
                            onChange={() => toggleMed(med.value)}
                          />
                          <span className="med-chip-dot" />
                          {med.label}
                        </label>
                      );
                    })}
                  </div>
                  {selectedMeds.length > 0 && (
                    <p className="muted" style={{ marginTop: 8 }}>
                      {selectedMeds.length} medicamento{selectedMeds.length > 1 ? "s" : ""} seleccionado{selectedMeds.length > 1 ? "s" : ""}
                    </p>
                  )}
                </div>
              </div>

              <FormActions
                status={status}
                onCancel={handleCancel}
                submitLabel="✅ Registrar"
              />
            </form>

            <BulkImportCard
              title={`Importar empadronamientos ${label} desde Excel`}
              description="Cargá múltiples empadronamientos del tipo actual usando un Excel con diagnóstico y medicamentos."
              importFn={(formData) => bulkImportEnrollments(tipo, formData)}
              templateHint="diagnostico, medications (separados por coma)"
            />
          </section>
        </section>
      </main>
    </>
  );
}
