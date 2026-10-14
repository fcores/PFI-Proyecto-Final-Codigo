/**
 * Standard form footer with status message and action buttons.
 *
 * @param {{ message: string, type: string }} status
 * @param {Function} onCancel
 * @param {string}   [submitLabel]
 * @param {boolean}  [submitting]   - Disables both buttons while the request is in flight
 * @param {string}   [submittingLabel]
 * @param {string}   [cancelLabel]
 */
export default function FormActions({
  status,
  onCancel,
  submitLabel = "Agregar",
  submitting = false,
  submittingLabel = "Guardando…",
  cancelLabel = "Cancelar",
}) {
  return (
    <footer className="form-actions">
      <div
        className={`status${status.type ? ` ${status.type}` : ""}`}
        role={status.type === "error" ? "alert" : "status"}
        aria-live="polite"
      >
        {status.message}
      </div>
      <div className="buttons">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={submitting}>
          {cancelLabel}
        </button>
        <button type="submit" className="btn-primary" disabled={submitting} aria-busy={submitting}>
          {submitting ? submittingLabel : submitLabel}
        </button>
      </div>
    </footer>
  );
}
