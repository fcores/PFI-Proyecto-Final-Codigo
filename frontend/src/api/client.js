const API_BASE = import.meta.env.VITE_API_URL || "/api";

export const TOKEN_STORAGE_KEY = "medchain_token";

// Endpoints donde un 401 significa "credenciales incorrectas", no "sesión vencida".
const AUTH_ENDPOINTS_SIN_SESION = ["/auth/login"];

export class ApiError extends Error {
  constructor(status, message, { type = null, body = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.type = type;
    this.body = body;
  }
}

function authHeaders() {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// El backend responde errores en dos formas: Problem Details (RFC 7807) con
// `title`/`detail`, y la validación de FastAPI con `detail` como lista.
function messageFromBody(body, status) {
  const { detail, title } = body || {};
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        const campo = Array.isArray(item.loc) ? item.loc.filter((p) => p !== "body").join(".") : "";
        return campo ? `${campo}: ${item.msg}` : item.msg;
      })
      .join(" · ");
  }
  if (typeof title === "string" && title.trim()) return title;
  if (status === 504) return "El servidor tardó demasiado en responder. Verificá el estado antes de reintentar.";
  if (status >= 500) return "Error del servidor. Intentá nuevamente en unos minutos.";
  return `Error ${status}`;
}

async function handleResponse(res, path) {
  if (res.status === 401 && !AUTH_ENDPOINTS_SIN_SESION.includes(path)) {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.dispatchEvent(new Event("auth:unauthorized"));
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, messageFromBody(body, res.status), { type: body?.type ?? null, body });
  }
  if (res.status === 204) return null;
  return res.json();
}

async function request(path, init = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. Revisá tu conexión.");
  }
  return handleResponse(res, path);
}

export async function get(path) {
  return request(path, { headers: { ...authHeaders() } });
}

export async function postForm(path, formData) {
  return request(path, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
}

export async function postJson(path, body) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
}

export async function putJson(path, body) {
  return request(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
}
