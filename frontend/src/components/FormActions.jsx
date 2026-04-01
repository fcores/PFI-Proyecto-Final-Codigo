/**
 * Standard form footer with status message and action buttons.
 *
 * @param {{ message: string, type: string }} status
 * @param {Function} onCancel
 * @param {string}   [submitLabel]
 */
export default function FormActions({
  status,
  onCancel,
  submitLabel = "✅ Agregar",
}) {
  return (
    <footer className="form-actions">
      <div className={`status${status.type ? ` ${status.type}` : ""}`}>
        {status.message}
      </div>
      <div className="buttons">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancelar
        </button>
        <button type="submit" className="btn-primary">
          {submitLabel}
        </button>
      </div>
    </footer>
  );
}
