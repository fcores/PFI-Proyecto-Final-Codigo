import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { useAuth } from "../auth/AuthContext";
import { fetchUsers, createUser, updateUser, resetUserPassword } from "../api/users";
import { ROLE_LABEL } from "../constants/roles";
import { formatDate } from "../utils/formatDate";

const TABLE_COLUMNS = ["Usuario", "Nombre", "Rol", "Estado", "Creado", "Acciones"];

const ROLES = ["prescriptor", "auditor", "administrador", "super_admin"].map((value) => ({
  value,
  label: ROLE_LABEL[value],
}));

const EMPTY_FORM = { username: "", password: "", confirmacion: "", display_name: "", role: "prescriptor" };

function StatusLine({ status }) {
  if (!status) return null;
  return (
    <p className={`status ${status.type} status--block`} role={status.type === "error" ? "alert" : "status"}>
      {status.message}
    </p>
  );
}

export default function UsuariosPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formStatus, setFormStatus] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null); // {id, username, display_name, role, active}
  const [resetTarget, setResetTarget] = useState(null); // {id, username, password, confirmacion}
  const [modalStatus, setModalStatus] = useState(null);
  const [saving, setSaving] = useState(false);
  const [actionStatus, setActionStatus] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setListError(null);
      setUsers(await fetchUsers());
    } catch (err) {
      setListError(err.message || "Error al listar usuarios.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(event) {
    event.preventDefault();
    if (creating) return;
    if (form.password !== form.confirmacion) {
      setFormStatus({ type: "error", message: "La confirmación no coincide con la contraseña." });
      return;
    }
    setFormStatus(null);
    setCreating(true);
    try {
      const { confirmacion: _omit, ...body } = form;
      await createUser(body);
      setFormStatus({ type: "success", message: `Usuario ${form.username} creado.` });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      setFormStatus({ type: "error", message: err.message || "Error al crear el usuario." });
    } finally {
      setCreating(false);
    }
  }

  function closeModals() {
    setEditing(null);
    setResetTarget(null);
    setModalStatus(null);
  }

  async function handleUpdate(event) {
    event.preventDefault();
    if (saving) return;
    setModalStatus(null);
    setSaving(true);
    try {
      await updateUser(editing.id, {
        display_name: editing.display_name,
        role: editing.role,
        active: editing.active,
      });
      setActionStatus({ type: "success", message: `Usuario ${editing.username} actualizado.` });
      closeModals();
      await load();
    } catch (err) {
      setModalStatus({ type: "error", message: err.message || "Error al actualizar." });
    } finally {
      setSaving(false);
    }
  }

  async function handleReset(event) {
    event.preventDefault();
    if (saving) return;
    if (resetTarget.password !== resetTarget.confirmacion) {
      setModalStatus({ type: "error", message: "La confirmación no coincide con la contraseña." });
      return;
    }
    setModalStatus(null);
    setSaving(true);
    try {
      await resetUserPassword(resetTarget.id, resetTarget.password);
      setActionStatus({
        type: "success",
        message: `Contraseña de ${resetTarget.username} actualizada. Sus sesiones abiertas se cerraron.`,
      });
      closeModals();
    } catch (err) {
      setModalStatus({ type: "error", message: err.message || "Error al resetear la contraseña." });
    } finally {
      setSaving(false);
    }
  }

  function renderRow(user) {
    const esPropio = user.username === currentUser?.username;
    return (
      <tr key={user.id}>
        <td>
          {user.username}
          {esPropio ? <span className="tag-self">vos</span> : null}
        </td>
        <td>{user.display_name}</td>
        <td>{ROLE_LABEL[user.role] || user.role}</td>
        <td>
          <StatusChip variant={user.active ? "success" : "neutral"} label={user.active ? "Activo" : "Inactivo"} />
        </td>
        <td className="cell-nowrap">{formatDate(user.created_at)}</td>
        <td>
          <div className="row-actions">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                setModalStatus(null);
                setEditing({
                  id: user.id,
                  username: user.username,
                  display_name: user.display_name,
                  role: user.role,
                  active: user.active,
                  esPropio,
                });
              }}
            >
              Editar
            </button>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                setModalStatus(null);
                setResetTarget({ id: user.id, username: user.username, password: "", confirmacion: "" });
              }}
            >
              Resetear clave
            </button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <>
      <TopBar
        title="Gestión de usuarios"
        subtitle="Alta de cuentas, asignación de roles y reseteo de contraseñas."
        badge="Super Admin"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-form">
            <CardHeader
              eyebrow="Alta"
              title="Nuevo usuario"
              description="La contraseña se almacena con Argon2id. El rol define qué módulos puede operar."
            />
            <form onSubmit={handleCreate}>
              <div className="form-grid">
                <FormField label="Usuario" htmlFor="user_username" required span={4}>
                  <input
                    id="user_username"
                    type="text"
                    autoComplete="off"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    required
                    minLength={3}
                    maxLength={100}
                    pattern="[a-zA-Z0-9._\-]+"
                    title="Letras, números, punto, guion y guion bajo."
                  />
                </FormField>
                <FormField label="Nombre visible" htmlFor="user_display" required span={4}>
                  <input
                    id="user_display"
                    type="text"
                    value={form.display_name}
                    onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                    required
                    maxLength={200}
                  />
                </FormField>
                <FormField label="Rol" htmlFor="user_role" required span={4}>
                  <select
                    id="user_role"
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  >
                    {ROLES.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </FormField>
                <FormField label="Contraseña" htmlFor="user_password" required span={6}>
                  <input
                    id="user_password"
                    type="password"
                    autoComplete="new-password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    required
                    minLength={8}
                    maxLength={128}
                  />
                </FormField>
                <FormField label="Repetir contraseña" htmlFor="user_password_confirm" required span={6}>
                  <input
                    id="user_password_confirm"
                    type="password"
                    autoComplete="new-password"
                    value={form.confirmacion}
                    onChange={(e) => setForm((f) => ({ ...f, confirmacion: e.target.value }))}
                    required
                    minLength={8}
                    maxLength={128}
                  />
                </FormField>
              </div>
              <div className="form-actions">
                <div className={`status${formStatus ? ` ${formStatus.type}` : ""}`} role="status" aria-live="polite">
                  {formStatus?.message}
                </div>
                <div className="buttons">
                  <button type="submit" className="btn-primary" disabled={creating}>
                    {creating ? "Creando…" : "Crear usuario"}
                  </button>
                </div>
              </div>
            </form>
          </section>

          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Cuentas</span>
                <h2>Usuarios del sistema</h2>
                <p className="muted">Desactivar una cuenta o cambiarle el rol cierra sus sesiones abiertas.</p>
              </div>
              <PanelStat count={users.length} singular="cuenta" plural="cuentas" />
            </header>

            <StatusLine status={actionStatus} />
            {listError && (
              <p className="status error status--block" role="alert">
                {listError}{" "}
                <button type="button" className="btn-link" onClick={load}>
                  Reintentar
                </button>
              </p>
            )}

            <DataTable
              columns={TABLE_COLUMNS}
              rows={users}
              renderRow={renderRow}
              emptyText={loading ? "Cargando usuarios…" : "No hay usuarios registrados."}
            />
          </section>
        </section>
      </main>

      <Modal
        open={Boolean(editing)}
        onClose={closeModals}
        title={editing ? `Editar ${editing.username}` : ""}
        description="Cambiá el nombre visible, el rol o el estado de la cuenta."
      >
        {editing && (
          <form onSubmit={handleUpdate}>
            <div className="form-grid">
              <FormField label="Nombre visible" htmlFor="edit_display" required span={12}>
                <input
                  id="edit_display"
                  type="text"
                  value={editing.display_name}
                  onChange={(e) => setEditing((v) => ({ ...v, display_name: e.target.value }))}
                  required
                  maxLength={200}
                />
              </FormField>
              <FormField label="Rol" htmlFor="edit_role" span={6}>
                <select
                  id="edit_role"
                  value={editing.role}
                  disabled={editing.esPropio}
                  onChange={(e) => setEditing((v) => ({ ...v, role: e.target.value }))}
                >
                  {ROLES.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Estado" htmlFor="edit_active" span={6}>
                <select
                  id="edit_active"
                  value={editing.active ? "1" : "0"}
                  disabled={editing.esPropio}
                  onChange={(e) => setEditing((v) => ({ ...v, active: e.target.value === "1" }))}
                >
                  <option value="1">Activo</option>
                  <option value="0">Inactivo</option>
                </select>
              </FormField>
              {editing.esPropio ? (
                <p className="field-hint field-span-12">
                  No podés cambiar tu propio rol ni desactivar tu cuenta.
                </p>
              ) : null}
            </div>
            <StatusLine status={modalStatus} />
            <div className="form-actions">
              <div className="buttons">
                <button type="button" className="btn-secondary" onClick={closeModals} disabled={saving}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? "Guardando…" : "Guardar cambios"}
                </button>
              </div>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        open={Boolean(resetTarget)}
        onClose={closeModals}
        title={resetTarget ? `Resetear contraseña de ${resetTarget.username}` : ""}
        description="La nueva contraseña reemplaza a la anterior de inmediato y se cierran las sesiones abiertas de la cuenta."
      >
        {resetTarget && (
          <form onSubmit={handleReset}>
            <div className="form-grid">
              <FormField label="Nueva contraseña" htmlFor="reset_password" required span={12}>
                <input
                  id="reset_password"
                  type="password"
                  autoComplete="new-password"
                  value={resetTarget.password}
                  onChange={(e) => setResetTarget((v) => ({ ...v, password: e.target.value }))}
                  required
                  minLength={8}
                  maxLength={128}
                />
              </FormField>
              <FormField label="Repetir contraseña" htmlFor="reset_password_confirm" required span={12}>
                <input
                  id="reset_password_confirm"
                  type="password"
                  autoComplete="new-password"
                  value={resetTarget.confirmacion}
                  onChange={(e) => setResetTarget((v) => ({ ...v, confirmacion: e.target.value }))}
                  required
                  minLength={8}
                  maxLength={128}
                />
              </FormField>
            </div>
            <StatusLine status={modalStatus} />
            <div className="form-actions">
              <div className="buttons">
                <button type="button" className="btn-secondary" onClick={closeModals} disabled={saving}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? "Guardando…" : "Resetear"}
                </button>
              </div>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}
