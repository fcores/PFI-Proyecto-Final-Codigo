import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  return (
    <>
      <Sidebar />
      <div className="main-wrapper">
        <Outlet />
        <footer className="page-footer">
          Copyright © 2025 MedChain AI — Salud, Tecnología e Inteligencia Artificial
        </footer>
      </div>
    </>
  );
}
