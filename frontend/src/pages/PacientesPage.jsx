import { useCallback, useRef, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import FormActions from "../components/FormActions";
import BulkImportCard from "../components/BulkImportCard";
import useFormSubmit from "../hooks/useFormSubmit";
import { bulkImportPatients, createPatient } from "../api/patients";

// Categorías de respaldo que el auditor espera encontrar (CU-05). El nombre del
// input ({key}_file) es el que espera POST /patients.
const ADJUNTOS = [
  { key: "hc", label: "Historia clínica" },
  { key: "ap", label: "Anatomía patológica" },
  { key: "img", label: "Estudios por imágenes" },
  { key: "lab", label: "Laboratorios" },
  { key: "receta", label: "Receta" },
  { key: "otros", label: "Otros" },
];

const ACCEPT = ".pdf,.jpg,.jpeg,.png";

export default function PacientesPage() {
  const [adjuntos, setAdjuntos] = useState({});
  const inputsRef = useRef({});

  const limpiarAdjuntos = useCallback(() => setAdjuntos({}), []);

  const { formRef, status, pending, handleSubmit, handleCancel } = useFormSubmit({
    submitFn: createPatient,
    onSuccess: limpiarAdjuntos,
    loadingMsg: "Guardando paciente…",
    successMsg: "Paciente creado correctamente.",
    errorMsg: "Ocurrió un error al guardar el paciente.",
  });

  function quitarAdjunto(key) {
    const input = inputsRef.current[key];
    if (input) input.value = "";
    setAdjuntos((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  const cantidadAdjuntos = Object.keys(adjuntos).length;

  return (
    <>
      <TopBar
        title="Alta de pacientes"
        subtitle="Registrá los datos del paciente y la documentación respaldatoria que acompaña al expediente."
        badge="Pacientes"
      />
      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="content-stack">
            <form ref={formRef} className="card card-form" encType="multipart/form-data" onSubmit={handleSubmit}>
              <CardHeader
                split
                eyebrow="Alta clínica"
                title="Datos principales"
                description="Datos administrativos y clínicos básicos del paciente. Los datos personales se guardan cifrados."
              />

              <div className="form-grid form-grid--patient">
                <FormField label="Nombre" htmlFor="first_name" required span={4}>
                  <input id="first_name" name="first_name" type="text" autoComplete="off" maxLength={200} required />
                </FormField>

                <FormField label="Apellido" htmlFor="last_name" required span={4}>
                  <input id="last_name" name="last_name" type="text" autoComplete="off" maxLength={200} required />
                </FormField>

                <FormField label="Fecha de nacimiento" htmlFor="birth_date" required span={2}>
                  <input
                    id="birth_date"
                    name="birth_date"
                    type="date"
                    max={new Date().toISOString().slice(0, 10)}
                    required
                  />
                </FormField>

                <FormField label="Género" htmlFor="gender" required span={2}>
                  <select id="gender" name="gender" required defaultValue="">
                    <option value="" disabled>
                      Seleccionar…
                    </option>
                    <option value="femenino">Femenino</option>
                    <option value="masculino">Masculino</option>
                    <option value="otro">Otro</option>
                  </select>
                </FormField>

                <FormField label="Prestador" htmlFor="provider" span={4}>
                  <input id="provider" name="provider" type="text" placeholder="Ej.: Hospital Central" maxLength={200} />
                </FormField>

                <FormField label="ID Prestador" htmlFor="provider_id" span={4}>
                  <input id="provider_id" name="provider_id" type="text" maxLength={100} />
                </FormField>

                <FormField label="ID Credencial" htmlFor="credential_id" span={4}>
                  <input id="credential_id" name="credential_id" type="text" maxLength={100} />
                </FormField>

                <FormField label="Diagnóstico" htmlFor="treatment" span={12}>
                  <input id="treatment" name="treatment" type="text" placeholder="Ej.: Cáncer de colon" maxLength={500} />
                </FormField>
              </div>

              <section className="sub-card">
                <header className="sub-card-header">
                  <div>
                    <span className="card-eyebrow">Respaldo</span>
                    <h2>Documentación del expediente</h2>
                    <p className="muted">
                      Se registra el nombre de cada archivo para dejar constancia de la documentación presentada; el
                      documento en sí no se almacena en la plataforma.
                    </p>
                  </div>
                  <span className={`attach-counter${cantidadAdjuntos === ADJUNTOS.length ? " is-complete" : ""}`}>
                    {cantidadAdjuntos} de {ADJUNTOS.length} categorías
                  </span>
                </header>

                <ul className="attach-grid">
                  {ADJUNTOS.map(({ key, label }) => {
                    const nombre = adjuntos[key];
                    const inputId = `${key}_file`;
                    return (
                      <li key={key} className={`attach-item${nombre ? " has-file" : ""}`}>
                        <div className="attach-item__info">
                          <span className="attach-item__label">{label}</span>
                          <span className="attach-item__file" title={nombre || ""}>
                            {nombre || "Sin archivo"}
                          </span>
                        </div>
                        <div className="attach-item__actions">
                          <label htmlFor={inputId} className="btn-secondary btn-sm">
                            {nombre ? "Cambiar" : "Adjuntar"}
                          </label>
                          {/* Sin `name`: el archivo no viaja al servidor, solo su nombre. */}
                          <input
                            ref={(el) => {
                              inputsRef.current[key] = el;
                            }}
                            id={inputId}
                            type="file"
                            accept={ACCEPT}
                            className="sr-only"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) setAdjuntos((prev) => ({ ...prev, [key]: file.name }));
                              else quitarAdjunto(key);
                            }}
                          />
                          <input type="hidden" name={`${key}_filename`} value={nombre || ""} />
                          {nombre ? (
                            <button
                              type="button"
                              className="btn-link"
                              onClick={() => quitarAdjunto(key)}
                              aria-label={`Quitar ${label}`}
                            >
                              Quitar
                            </button>
                          ) : null}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>

              <FormActions
                status={status}
                onCancel={() => {
                  handleCancel();
                  limpiarAdjuntos();
                }}
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
