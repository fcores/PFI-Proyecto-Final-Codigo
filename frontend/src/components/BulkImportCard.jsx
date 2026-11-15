import { useRef, useState } from "react";
import CardHeader from "./CardHeader";
import useFormStatus from "../hooks/useFormStatus";

export default function BulkImportCard({
  title,
  description,
  importFn,
  templateHint,
  onSuccess,
}) {
  const fileRef = useRef(null);
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState(null);
  const [pending, setPending] = useState(false);
  const { status, setLoading, setSuccess, setError, clear } = useFormStatus();

  function resetFormState() {
    if (fileRef.current) {
      fileRef.current.value = "";
    }
    setFileName("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (pending) return;

    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Seleccioná un archivo .xlsx para importar.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setLoading("Importando archivo Excel...");
    setPending(true);

    try {
      const response = await importFn(formData);
      setResult(response);
      setSuccess(
        `Importación finalizada: ${response.imported_count} registros importados y ${response.failed_count} con error.`,
      );
      resetFormState();
      onSuccess?.(response);
    } catch (error) {
      setError(error.message || "No se pudo importar el archivo Excel.");
    } finally {
      setPending(false);
    }
  }

  function handleCancel() {
    resetFormState();
    setResult(null);
    clear();
  }

  return (
    <form className="card card-bulk-import" onSubmit={handleSubmit}>
      <CardHeader
        split
        eyebrow="Carga masiva"
        title={title}
        description={description}
        badge="Excel .xlsx"
      />

      <div className="bulk-import-content">
        <label className="bulk-import-input">
          <span className="bulk-import-label">Archivo Excel</span>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx"
            onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
          />
        </label>

        <p className="bulk-import-hint">
          {fileName || "Seleccioná un archivo .xlsx (máx. 5 MB y 5000 filas) con encabezados en la primera fila."}
        </p>

        {templateHint ? (
          <p className="bulk-import-template">
            <strong>Columnas esperadas:</strong> {templateHint}
          </p>
        ) : null}

        {result?.errors?.length ? (
          <div className="bulk-import-errors">
            <strong>Filas con error</strong>
            <ul>
              {result.errors.slice(0, 5).map((error) => (
                <li key={`${error.row_number}-${error.message}`}>
                  Fila {error.row_number}: {error.message}
                </li>
              ))}
            </ul>
            {result.errors.length > 5 ? (
              <p className="muted">
                Se muestran los primeros 5 errores de {result.errors.length}.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>

      <footer className="form-actions">
        <div className={`status${status.type ? ` ${status.type}` : ""}`}>
          {status.message}
        </div>
        <div className="buttons">
          <button type="button" className="btn-secondary" onClick={handleCancel} disabled={pending}>
            Limpiar
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {pending ? "Importando…" : "Importar Excel"}
          </button>
        </div>
      </footer>
    </form>
  );
}
