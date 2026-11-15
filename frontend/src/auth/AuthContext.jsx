import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { TOKEN_STORAGE_KEY } from "../api/client";
import { login as loginRequest, logout as logoutRequest } from "../api/auth";

const USER_STORAGE_KEY = "medchain_user";

// Motivos de cierre de sesión que se informan en la pantalla de login.
export const LOGOUT_REASON = {
  MANUAL: "manual",
  EXPIRED: "expired",
};

const AuthContext = createContext(null);

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState(readStoredUser);
  const [logoutReason, setLogoutReason] = useState(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const loggingOutRef = useRef(false);

  const clearSession = useCallback((reason) => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setLogoutReason(reason ?? null);
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await loginRequest(username, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, data.token);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
    setLogoutReason(null);
    setToken(data.token);
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    // Evita disparar dos requests por doble click.
    if (loggingOutRef.current) return;
    loggingOutRef.current = true;
    setLoggingOut(true);
    try {
      await logoutRequest();
    } catch {
      // Ignorar errores de red al cerrar sesión: la sesión local se limpia igual.
    } finally {
      loggingOutRef.current = false;
      setLoggingOut(false);
      clearSession(LOGOUT_REASON.MANUAL);
    }
  }, [clearSession]);

  useEffect(() => {
    function handleUnauthorized() {
      // Un 401 durante el logout manual no es una expiración.
      if (loggingOutRef.current) return;
      clearSession(LOGOUT_REASON.EXPIRED);
    }
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, [clearSession]);

  const value = useMemo(
    () => ({
      token,
      user,
      isAuthenticated: Boolean(token),
      login,
      logout,
      logoutReason,
      loggingOut,
    }),
    [token, user, login, logout, logoutReason, loggingOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de AuthProvider.");
  }
  return ctx;
}
