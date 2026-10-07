import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import type { AuthUser } from "../hooks/useAuth";
import appIcon from "../assets/favicon.ico";
import "../styles/AppHeader.css";

const navigationItems = [
  { path: "/dashboard", label: "Inicio" },
  { path: "/calendar", label: "Calendario" },
  { path: "/activities", label: "Actividades" },
  { path: "/plan", label: "Plan" },
  { path: "/progress", label: "Evolución" },
];

interface AppHeaderProps {
  user: AuthUser | null;
  isDemo: boolean;
  onSignOut: () => void;
}

export function AppHeader({ user, isDemo, onSignOut }: AppHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const initials = user?.name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() ?? "VF";
  return (
    <header className="app-header">
      <div className="app-header__content">
        <NavLink
          className="app-header__brand"
          to="/dashboard"
          aria-label="Veloform: inicio"
        >
          <img
            className="app-header__logo"
            src={appIcon}
            alt=""
            aria-hidden="true"
          />

          <span>
            <strong>Veloform</strong>
            <small>Entrenamiento que se adapta</small>
          </span>
        </NavLink>

        <nav
          className={[
            "app-header__navigation",
            menuOpen ? "app-header__navigation--open" : "",
          ].join(" ")}
          aria-label="Navegación principal"
        >
          {navigationItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/dashboard"}
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

        <button
          className={[
            "app-header__profile",
            menuOpen ? "app-header__profile--open" : "",
          ].join(" ")}
          type="button"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-label="Abrir menú de usuario"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {initials}
        </button>
        {menuOpen && (
          <div className="app-header__menu" role="menu">
            <span className="app-header__menu-user">{user?.email}</span>
            {isDemo && <span className="app-header__menu-demo">Modo demostración</span>}
            <Link to="/profile" role="menuitem" onClick={() => setMenuOpen(false)}>
              Perfil
            </Link>
            <button type="button" role="menuitem" onClick={onSignOut}>
              Cerrar sesión
            </button>
          </div>
        )}
      </div>
      {menuOpen && (
        <div className="app-header__mobile-drawer-layer">
          <button
            className="app-header__mobile-backdrop"
            type="button"
            aria-label="Cerrar menú"
            onClick={() => setMenuOpen(false)}
          />
          <aside className="app-header__mobile-drawer" aria-label="Menú principal">
            <div className="app-header__mobile-drawer-header">
              <div>
                <strong>{user?.name}</strong>
                <span>{user?.email}</span>
                {isDemo && <span>Modo demostración</span>}
              </div>
              <button
                type="button"
                aria-label="Cerrar menú"
                onClick={() => setMenuOpen(false)}
              >
                ×
              </button>
            </div>
            <nav aria-label="Navegación móvil">
              {navigationItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === "/dashboard"}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    isActive
                      ? "app-header__mobile-link app-header__mobile-link--active"
                      : "app-header__mobile-link"
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="app-header__mobile-drawer-actions">
              <Link to="/profile" onClick={() => setMenuOpen(false)}>
                Perfil
              </Link>
              <button type="button" onClick={onSignOut}>
                Cerrar sesión
              </button>
            </div>
          </aside>
        </div>
      )}
    </header>
  );
}