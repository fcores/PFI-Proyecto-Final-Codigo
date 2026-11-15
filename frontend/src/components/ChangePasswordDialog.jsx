import { useState } from "react";
import Modal from "./Modal";
import FormField from "./FormField";
import { changePassword } from "../api/auth";

const EMPTY = { actual: "", nueva: "", confirmacion: "" };

export default function ChangePasswordDialog({ open, onClose }) {
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState(null);
  const [pending, setPending] = useState(false);

  function close() {
    setForm(EMPTY);
    setStatus(null);
    onClose();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (form.nueva !== form.confirmacion) {
      setStatus({ type: "error", message: "La confirmación no coincide con la nueva contraseña." });
      return;
    }
    setPending(true);
    setStatus(null);
    try {
      await changePassword(form.actual, form.nueva);
      setForm(EMPTY);
      setStatus({
        type: "success",
        message: "Contraseña actualizada. Se cerraron tus otras sesiones abiertas.",
      });
    } catch (err) {
      setStatus({ type: "error", message: err.message || "No se pudo cambiar la contraseña." });
    } finally {
      setPending(false);
    }
  }

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <Modal
      open={open}
      onClose={close}
      title="Cambiar contraseña"
      description="Mínimo 8 caracteres. Las demás sesiones abiertas con tu usuario se cierran."
    >
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <FormField label="Contraseña actual" htmlFor="pwd_actual" required span={12}>
            <input
              id="pwd_actual"
              type="password"
              autoComplete="current-password"
              value={form.actual}
              onChange={update("actual")}
              required
            />
          </FormField>
          <FormField label="Nueva contraseña" htmlFor="pwd_nueva" required span={12}>
            <input
              id="pwd_nueva"
              type="password"
              autoComplete="new-password"
              value={form.nueva}
              onChange={update("nueva")}
              required
              minLength={8}
            />
          </FormField>
          <FormField label="Repetir nueva contraseña" htmlFor="pwd_confirmacion" required span={12}>
            <input
              id="pwd_confirmacion"
              type="password"
              autoComplete="new-password"
              value={form.confirmacion}
              onChange={update("confirmacion")}
              required
              minLength={8}
            />
          </FormField>
        </div>
        <footer className="form-actions">
          <div className={`status${status ? ` ${status.type}` : ""}`} role="status" aria-live="polite">
            {status?.message}
          </div>
          <div className="buttons">
            <button type="button" className="btn-secondary" onClick={close} disabled={pending}>
              {status?.type === "success" ? "Cerrar" : "Cancelar"}
            </button>
            <button type="submit" className="btn-primary" disabled={pending}>
              {pending ? "Guardando…" : "Cambiar contraseña"}
            </button>
          </div>
        </footer>
      </form>
    </Modal>
  );
}
