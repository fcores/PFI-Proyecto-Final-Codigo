import { useEffect, useMemo, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import ErrorBoundary from "./ErrorBoundary";
import Sidebar from "./Sidebar";
import { LayoutContext } from "./layoutContext";

const YEAR = new Date().getFullYear();

export default function Layout() {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  // Cada navegación cierra el drawer en mobile.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  const value = useMemo(() => ({ navOpen, setNavOpen }), [navOpen]);

  return (
    <LayoutContext.Provider value={value}>
      <Sidebar />
      {navOpen ? <div className="sidebar-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" /> : null}
      <div className="main-wrapper">
        {/* La key reinicia el boundary al cambiar de ruta: un error en una
            pantalla no deja bloqueada la navegación. */}
        <ErrorBoundary key={location.pathname}>
          <Outlet />
        </ErrorBoundary>
        <footer className="page-footer">
          © {YEAR} MedChain AI — Salud, Tecnología e Inteligencia Artificial
        </footer>
      </div>
    </LayoutContext.Provider>
  );
}
