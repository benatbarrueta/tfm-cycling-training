import { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { Link, useLocation, useNavigate } from "react-router-dom";
import appIcon from "../assets/favicon.ico";
import type { ApiError } from "../api/client";
import "../styles/AuthPage.css";

interface AuthPageProps {
  mode: "login" | "register";
  onDemoAccess: () => Promise<void>;
  onGoogleLogin: (credential: string) => Promise<void>;
}

export function AuthPage({ mode, onDemoAccess, onGoogleLogin }: AuthPageProps) {
  const isRegister = mode === "register";
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState<"idle" | "google" | "demo">("idle");
  const [error, setError] = useState<string | null>(null);
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const demoEnabled = import.meta.env.VITE_ENABLE_DEMO_AUTH !== "false";

  function destination() {
    const from = (location.state as { from?: string } | null)?.from;
    return from ?? "/dashboard";
  }

  async function handleGoogle(credential: string) {
    setError(null);
    setStatus("google");
    try {
      await onGoogleLogin(credential);
      navigate(destination(), { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se ha podido iniciar sesión con Google.");
      setStatus("idle");
    }
  }

  async function handleDemo() {
    setError(null);
    setStatus("demo");
    try {
      await onDemoAccess();
      navigate(destination(), { replace: true });
    } catch (cause) {
      const message = (cause as ApiError)?.status === 404
        ? "El acceso demo no está disponible en este entorno."
        : cause instanceof Error
          ? cause.message
          : "No se ha podido iniciar el modo demostración.";
      setError(message);
      setStatus("idle");
    }
  }

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
          <p className="eyebrow">{isRegister ? "Empieza en Veloform" : "Bienvenido de nuevo"}</p>
          <h2>{isRegister ? "Crea tu espacio de entrenamiento" : "Accede a tu entrenamiento"}</h2>
          <p>{isRegister ? "Configura tu perfil y prepara tu primera temporada." : "Continúa donde lo dejaste."}</p>
        </div>
        <div className="auth-form">
          {googleClientId ? (
            <div className="auth-form__google-wrapper">
              <GoogleLogin
                onSuccess={(response) => {
                  if (response.credential) void handleGoogle(response.credential);
                  else setError("Google no ha devuelto una credencial válida.");
                }}
                onError={() => setError("Google no ha podido completar el acceso.")}
                useOneTap={false}
                text="continue_with"
                shape="rectangular"
                width="100%"
              />
            </div>
          ) : (
            <button className="auth-form__google auth-form__google--unavailable" type="button" disabled>
              Google no está configurado todavía
            </button>
          )}
          {status === "google" && <p className="auth-form__notice" role="status">Conectando con Google…</p>}
          {error && <p className="auth-form__notice" role="alert">{error}</p>}
          <p className="auth-form__privacy">Veloform no recibe ni almacena tu contraseña de Google.</p>
          <div className="auth-form__divider"><span>o</span></div>
          {demoEnabled && (
            <button className="button button--primary" type="button" onClick={() => void handleDemo()} disabled={status !== "idle"}>
              {status === "demo" ? "Entrando en la demostración…" : "Explorar con una cuenta demo"}
            </button>
          )}
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
