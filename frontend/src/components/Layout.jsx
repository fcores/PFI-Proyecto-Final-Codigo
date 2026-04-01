import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  return (
    <>
      <Sidebar />
      <div className="main-wrapper">
        <Outlet />
        <footer className="page-footer">
          Copyright © 2024 Alleanza Tracking — Droguería Scienza Argentina
        </footer>
      </div>
    </>
  );
}
