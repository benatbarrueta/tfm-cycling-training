import { NavLink } from "react-router-dom";
import "../styles/AppHeader.css";

const navigationItems = [
  { path: "/", label: "Inicio" },
  { path: "/calendar", label: "Calendario" },
  { path: "/plan", label: "Plan" },
  { path: "/progress", label: "Evolución" },
];

export function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-header__content">
        <NavLink
          className="app-header__brand"
          to="/"
          aria-label="Cycling Training: inicio"
        >
          <span className="app-header__logo">CT</span>

          <span>
            <strong>Cycling Training</strong>
            <small>Entrenamiento personalizado</small>
          </span>
        </NavLink>

        <nav
          className="app-header__navigation"
          aria-label="Navegación principal"
        >
          {navigationItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                isActive
                  ? "app-header__link app-header__link--active"
                  : "app-header__link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <NavLink
          className="app-header__profile"
          to="/profile"
          aria-label="Abrir perfil"
        >
          BB
        </NavLink>
      </div>
    </header>
  );
}