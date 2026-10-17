import { useState } from "react";
import Modal from "./Modal";
import FormField from "./FormField";
import { deleteOwnAccount } from "../api/auth";
import { useAuth } from "../auth/AuthContext";

export default function DeleteAccountDialog({ open, onClose }) {
  const { logout } = useAuth();
  const [password, setPassword] = useState("");
  const [confirmado, setConfirmado] = useState(false);
  const [status, setStatus] = useState(null);
  const [pending, setPending] = useState(false);

  function close() {
    setPassword("");
    setConfirmado(false);
    setStatus(null);
    onClose();
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setPending(true);
    setStatus(null);
    try {
      await deleteOwnAccount(password);
      await logout();
    } catch (err) {
      setStatus({ type: "error", message: err.message || "No se pudo dar de baja la cuenta." });
      setPending(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Dar de baja mi cuenta"
      description="Tu nombre se elimina y la cuenta queda desactivada. Los actos que ya registraste se conservan bajo tu nombre de usuario como seudónimo, porque la normativa obliga a conservarlos."
    >
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <FormField label="Contraseña actual" htmlFor="baja_password" required span={12}>
            <input
              id="baja_password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </FormField>
          <label className="field-span-12">
            <input type="checkbox" checked={confirmado} onChange={(e) => setConfirmado(e.target.checked)} /> Entiendo
            que la baja no se puede deshacer.
          </label>
        </div>
        <footer className="form-actions">
          <div className={`status${status ? ` ${status.type}` : ""}`} role="status" aria-live="polite">
            {status?.message}
          </div>
          <div className="buttons">
            <button type="button" className="btn-secondary" onClick={close} disabled={pending}>
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={pending || !confirmado || !password}>
              {pending ? "Procesando…" : "Dar de baja"}
            </button>
          </div>
        </footer>
      </form>
    </Modal>
  );
}
