import { createContext, useContext } from "react";

// Estado del drawer de navegación en pantallas chicas: lo abre la TopBar de
// cada página y lo cierra el Sidebar al navegar.
export const LayoutContext = createContext({ navOpen: false, setNavOpen: () => {} });

export function useLayout() {
  return useContext(LayoutContext);
}
