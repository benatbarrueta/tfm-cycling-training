import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import appIcon from "../assets/favicon.ico";
import "../styles/AuthPage.css";

interface AuthPageProps {
  mode: "login" | "register";
  onDemoAccess: () => void;
}

export function AuthPage({ mode, onDemoAccess }: AuthPageProps) {
  const isRegister = mode === "register";
  const navigate = useNavigate();
  const [googleStatus, setGoogleStatus] = useState<
    "idle" | "loading" | "unavailable" | "error"
  >("idle");

  function continueWithGoogle() {
    setGoogleStatus("loading");
    window.setTimeout(() => setGoogleStatus("unavailable"), 500);
  }

  function enterDemo() {
    onDemoAccess();
    navigate(isRegister ? "/onboarding" : "/dashboard", { replace: true });
  }

  const googleLabel =
    googleStatus === "loading" ? "Conectando con Google…" : "Continuar con Google";

  return (
    <main className="auth-page">
      <section className="auth-page__intro">
        <Link className="auth-page__brand" to="/">
          <img className="auth-page__brand-icon" src={appIcon} alt="" aria-hidden="true" />
          <strong>Veloform</strong>
        </Link>
        <p className="auth-page__eyebrow">Entrena con intención</p>
        <h1>Un plan que escucha cómo respondes.</h1>
        <p>Organiza tus semanas, entiende tu carga y adapta el siguiente paso sin perder de vista cómo te sientes sobre la bici.</p>
        <div className="auth-page__promise"><span>01</span><p>Datos claros para decidir mejor cada semana.</p></div>
        <div className="auth-page__promise"><span>02</span><p>Sesiones concretas cuando llega el momento de entrenar.</p></div>
      </section>
      <section className="auth-page__panel">
        <div className="auth-page__form-header">
          <p className="eyebrow">{isRegister ? "Empieza con Veloform" : "Bienvenido de nuevo"}</p>
          <h2>{isRegister ? "Crea tu espacio de entrenamiento" : "Accede a tu entrenamiento"}</h2>
          <p>{isRegister ? "Define tu objetivo y construye una planificación que evoluciona contigo." : "Continúa donde lo dejaste."}</p>
        </div>
        <div className="auth-form">
          <button
            className="auth-form__google"
            type="button"
            onClick={continueWithGoogle}
            disabled={googleStatus === "loading"}
            aria-live="polite"
          >
            <svg
              className="auth-form__google-icon"
              viewBox="0 0 18 18"
              aria-hidden="true"
              focusable="false"
            >
              <path
                fill="#4285F4"
                d="M17.64 9.205c0-.638-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.614Z"
              />
              <path
                fill="#34A853"
                d="M9 18c2.43 0 4.467-.806 5.956-2.181l-2.908-2.258c-.806.54-1.836.86-3.048.86-2.344 0-4.33-1.584-5.04-3.715H.954v2.332A9 9 0 0 0 9 18Z"
              />
              <path
                fill="#FBBC05"
                d="M3.96 10.706A5.41 5.41 0 0 1 3.677 9c0-.592.102-1.167.283-1.706V4.962H.954A9 9 0 0 0 0 9c0 1.453.348 2.827.954 4.038l3.006-2.332Z"
              />
              <path
                fill="#EA4335"
                d="M9 3.58c1.322 0 2.508.454 3.44 1.346l2.582-2.582C13.463.89 11.426 0 9 0A9 9 0 0 0 .954 4.962L3.96 7.294C4.67 5.163 6.656 3.58 9 3.58Z"
              />
            </svg>
            {googleLabel}
          </button>
          {googleStatus === "unavailable" && (
            <p className="auth-form__notice" role="status">
              El acceso con Google se conectará en una fase posterior. Mientras tanto, puedes utilizar el modo demostración.
            </p>
          )}
          <p className="auth-form__privacy">
            {isRegister
              ? "Al continuar, Google confirma tu identidad. Veloform no recibe ni almacena tu contraseña."
              : "Veloform no recibe ni almacena tu contraseña de Google."}
          </p>
          <div className="auth-form__divider"><span>o</span></div>
          <button className="button button--primary" type="button" onClick={enterDemo}>
            {isRegister ? "Probar la aplicación" : "Entrar en modo demostración"}
          </button>
        </div>
        <p className="auth-page__muted-link">
          {isRegister ? "¿Ya tienes una cuenta? " : "¿Es tu primera vez? "}
          <Link to={isRegister ? "/login" : "/register"}>
            {isRegister ? "Acceder" : "Crear mi perfil"}
          </Link>
        </p>
      </section>
    </main>
  );
}
