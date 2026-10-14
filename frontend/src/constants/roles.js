export const ROLE_LABEL = {
  super_admin: "Super Admin",
  administrador: "Administrativo",
  prescriptor: "Prescriptor",
  auditor: "Auditor",
};

// Pantalla principal de cada perfil. La usan el login y la raíz "/" para que
// ambos caminos lleven al mismo lugar.
export function defaultRouteFor(role) {
  if (role === "auditor") return "/auditoria/cola";
  if (role === "administrador") return "/pacientes/alta";
  return "/prescripciones/alta";
}
