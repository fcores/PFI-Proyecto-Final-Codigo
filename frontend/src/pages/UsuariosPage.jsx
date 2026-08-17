import { useCallback, useEffect, useState } from "react";
import TopBar from "../components/TopBar";
import CardHeader from "../components/CardHeader";
import FormField from "../components/FormField";
import DataTable from "../components/DataTable";
import PanelStat from "../components/PanelStat";
import StatusChip from "../components/StatusChip";
import { fetchUsers, createUser, updateUser, resetUserPassword } from "../api/users";
import { formatDate } from "../utils/formatDate";

const TABLE_COLUMNS = ["ID", "Usuario", "Nombre", "Rol", "Estado", "Creado", "Acciones"];

const ROLES = [
  { value: "prescriptor", label: "Prescriptor" },
  { value: "auditor", label: "Auditor" },
  { value: "administrador", label: "Administrativo" },
  { value: "super_admin", label: "Super Admin" },
];

const ROLE_LABEL = Object.fromEntries(ROLES.map((r) => [r.value, r.label]));

const EMPTY_FORM = { username: "", password: "", display_name: "", role: "prescriptor" };

export default function UsuariosPage() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formStatus, setFormStatus] = useState(null);
  const [editing, setEditing] = useState(null); // {id, display_name, role, active}
  const [resetTarget, setResetTarget] = useState(null); // {id, username, password}
  const [actionStatus, setActionStatus] = useState(null);

  const load = useCallback(async () => {
    try {
      setUsers(await fetchUsers());
    } catch (err) {
      setActionStatus({ type: "error", message: err.message || "Error al listar usuarios." });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(event) {
    event.preventDefault();
    setFormStatus(null);
    try {
      await createUser(form);
      setFormStatus({ type: "success", message: `Usuario ${form.username} creado.` });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      setFormStatus({ type: "error", message: err.message || "Error al crear el usuario." });
    }
  }

  async function handleUpdate(event) {
    event.preventDefault();
    setActionStatus(null);
    try {
      await updateUser(editing.id, {
        display_name: editing.display_name,
        role: editing.role,
        active: editing.active,
      });
      setActionStatus({ type: "success", message: "Usuario actualizado." });
      setEditing(null);
      await load();
    } catch (err) {
      setActionStatus({ type: "error", message: err.message || "Error al actualizar." });
    }
  }

  async function handleReset(event) {
    event.preventDefault();
    setActionStatus(null);
    try {
      await resetUserPassword(resetTarget.id, resetTarget.password);
      setActionStatus({ type: "success", message: `Contraseña de ${resetTarget.username} actualizada.` });
      setResetTarget(null);
    } catch (err) {
      setActionStatus({ type: "error", message: err.message || "Error al resetear la contraseña." });
    }
  }

  function renderRow(user) {
    return (
      <tr key={user.id}>
        <td>{user.id}</td>
        <td>{user.username}</td>
        <td>{user.display_name}</td>
        <td>{ROLE_LABEL[user.role] || user.role}</td>
        <td>
          <StatusChip
            variant={user.active ? "success" : "neutral"}
            label={user.active ? "Activo" : "Inactivo"}
          />
        </td>
        <td>{formatDate(user.created_at)}</td>
        <td>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                setEditing({
                  id: user.id,
                  username: user.username,
                  display_name: user.display_name,
                  role: user.role,
                  active: user.active,
                })
              }
            >
              Editar
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setResetTarget({ id: user.id, username: user.username, password: "" })}
            >
              Reset clave
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
        subtitle="Alta de cuentas, asignación de roles y reseteo de contraseñas. Solo visible para el super admin."
        badge="Usuarios"
      />

      <main className="page page--wide">
        <section className="layout layout--single">
          <section className="card card-form">
            <CardHeader
              eyebrow="Alta"
              title="👤 Nuevo usuario"
              description="La contraseña se almacena con Argon2id. El rol define qué módulos puede operar."
            />
            <form onSubmit={handleCreate}>
              <div className="form-grid">
                <FormField label="Usuario" htmlFor="user_username" span={3}>
                  <input
                    id="user_username"
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    required
                    minLength={3}
                    pattern="[a-zA-Z0-9._-]+"
                  />
                </FormField>
                <FormField label="Nombre visible" htmlFor="user_display" span={3}>
                  <input
                    id="user_display"
                    type="text"
                    value={form.display_name}
                    onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                    required
                  />
                </FormField>
                <FormField label="Contraseña" htmlFor="user_password" span={3}>
                  <input
                    id="user_password"
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    required
                    minLength={8}
                  />
                </FormField>
                <FormField label="Rol" htmlFor="user_role" span={3}>
                  <select
                    id="user_role"
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  >
                    {ROLES.map((role) => (
                      <option key={role.value} value={role.value}>{role.label}</option>
                    ))}
                  </select>
                </FormField>
              </div>
              <div className="form-actions">
                {formStatus && (
                  <span className={`status ${formStatus.type}`}>{formStatus.message}</span>
                )}
                <div className="buttons">
                  <button type="submit" className="btn-primary">Crear usuario</button>
                </div>
              </div>
            </form>
          </section>

          <section className="card card-table">
            <header className="agreements-header">
              <div>
                <span className="card-eyebrow">Cuentas</span>
                <h2>Usuarios del sistema</h2>
              </div>
              <PanelStat count={users.length} singular="cuenta" plural="cuentas" />
            </header>

            {actionStatus && (
              <p className={`status ${actionStatus.type}`}>{actionStatus.message}</p>
            )}

            {editing && (
              <form className="correction-form" onSubmit={handleUpdate}>
                <CardHeader
                  eyebrow="Edición"
                  title={`Editar ${editing.username}`}
                  description="Cambiá el nombre visible, el rol o el estado de la cuenta."
                />
                <div className="form-grid">
                  <FormField label="Nombre visible" htmlFor="edit_display" span={4}>
                    <input
                      id="edit_display"
                      type="text"
                      value={editing.display_name}
                      onChange={(e) => setEditing((v) => ({ ...v, display_name: e.target.value }))}
                      required
                    />
                  </FormField>
                  <FormField label="Rol" htmlFor="edit_role" span={4}>
                    <select
                      id="edit_role"
                      value={editing.role}
                      onChange={(e) => setEditing((v) => ({ ...v, role: e.target.value }))}
                    >
                      {ROLES.map((role) => (
                        <option key={role.value} value={role.value}>{role.label}</option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Estado" htmlFor="edit_active" span={4}>
                    <select
                      id="edit_active"
                      value={editing.active ? "1" : "0"}
                      onChange={(e) => setEditing((v) => ({ ...v, active: e.target.value === "1" }))}
                    >
                      <option value="1">Activo</option>
                      <option value="0">Inactivo</option>
                    </select>
                  </FormField>
                </div>
                <div className="form-actions">
                  <div className="buttons">
                    <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>
                      Cancelar
                    </button>
                    <button type="submit" className="btn-primary">Guardar cambios</button>
                  </div>
                </div>
              </form>
            )}

            {resetTarget && (
              <form className="correction-form" onSubmit={handleReset}>
                <CardHeader
                  eyebrow="Seguridad"
                  title={`Resetear contraseña de ${resetTarget.username}`}
                  description="La nueva contraseña reemplaza a la anterior de inmediato."
                />
                <div className="form-grid">
                  <FormField label="Nueva contraseña" htmlFor="reset_password" span={6}>
                    <input
                      id="reset_password"
                      type="password"
                      value={resetTarget.password}
                      onChange={(e) => setResetTarget((v) => ({ ...v, password: e.target.value }))}
                      required
                      minLength={8}
                    />
                  </FormField>
                </div>
                <div className="form-actions">
                  <div className="buttons">
                    <button type="button" className="btn-secondary" onClick={() => setResetTarget(null)}>
                      Cancelar
                    </button>
                    <button type="submit" className="btn-primary">Resetear</button>
                  </div>
                </div>
              </form>
            )}

            <DataTable
              columns={TABLE_COLUMNS}
              rows={users}
              renderRow={renderRow}
              emptyText="No hay usuarios registrados."
            />
          </section>
        </section>
      </main>
    </>
  );
}
