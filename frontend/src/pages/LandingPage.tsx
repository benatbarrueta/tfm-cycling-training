import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { seasonPlanMock } from "../mocks/seasonPlan";
import { trainingPlanMock } from "../mocks/trainingPlan";
import appIcon from "../assets/favicon.ico";
import "../styles/LandingPage.css";

export function LandingPage() {
  const activeWeek = seasonPlanMock.weeks.find(
    (week) => week.status === "ACTIVE",
  );
  const plan = trainingPlanMock.plan;
  const nextWorkout = plan.workouts[0];

  return (
    <main className="landing-page">
      <header className="landing-page__header">
        <Link className="landing-page__brand" to="/">
          <img className="landing-page__brand-icon" src={appIcon} alt="" aria-hidden="true" />
          <strong>Veloform</strong>
        </Link>
        <Link
          className="landing-page__login landing-page__outline-link"
          to="/login"
          state={null}
        >
          Acceder
        </Link>
      </header>

      <section className="landing-page__hero">
        <div className="landing-page__hero-copy">
          <p className="eyebrow">Entrenamiento que se adapta</p>
          <h1>Pedalea hacia tu objetivo con un plan que escucha.</h1>
          <p>
            Organiza tu temporada, entiende tu carga y descubre qué sesión
            tiene sentido para ti esta semana.
          </p>
          <div className="landing-page__actions">
            <Link className="button button--primary" to="/register">
              Crear mi plan
            </Link>
            <Link className="landing-page__secondary-link" to="/login" state={null}>
              Ya tengo una cuenta
            </Link>
          </div>
        </div>

        <div className="landing-page__visual" aria-label="Resumen de entrenamiento semanal">
          <div className="landing-page__visual-top">
            <span>
              {activeWeek
                ? `${format(parseISO(activeWeek.week_start), "d MMM", { locale: es })} · semana activa`
                : "Semana activa"}
            </span>
            <strong>Respuesta estable</strong>
          </div>
          <div className="landing-page__visual-chart">
            <span style={{ height: "42%" }} />
            <span style={{ height: "62%" }} />
            <span style={{ height: "50%" }} />
            <span style={{ height: "78%" }} />
            <span style={{ height: "35%" }} />
            <span style={{ height: "66%" }} />
            <span style={{ height: "25%" }} />
          </div>
          <div className="landing-page__visual-footer">
            <strong>{plan.estimated_total_tss.toFixed(0)} TSS</strong>
            <span>Carga semanal prevista</span>
          </div>
          <div className="landing-page__visual-next">
            <span>Próxima sesión</span>
            <strong>{nextWorkout?.workout_type === "VO2MAX" ? "Intervalos intensos" : "Sesión de entrenamiento"}</strong>
            <small>{nextWorkout?.duration_minutes ?? "—"} min · {nextWorkout?.estimated_tss?.toFixed(0) ?? "—"} TSS estimados</small>
          </div>
        </div>
      </section>

      <section className="landing-page__intro-section">
        <div>
          <p className="eyebrow">De la carga a la sesión</p>
          <h2>No necesitas interpretar un modelo para saber qué hacer hoy.</h2>
        </div>
        <p>
          Veloform convierte tu historial y tu disponibilidad en una
          semana comprensible. La tecnología trabaja detrás; tú recibes una
          decisión clara, sesiones concretas y una planificación que se revisa
          contigo.
        </p>
      </section>

      <section className="landing-page__features">
        <article>
          <span>01</span>
          <h2>Una semana clara</h2>
          <p>Consulta tus sesiones, tus días de descanso y el siguiente paso sin perderte entre datos.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Decisiones comprensibles</h2>
          <p>Te contamos por qué mantenemos, aumentamos o reducimos la carga de entrenamiento.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Plan en evolución</h2>
          <p>Las semanas futuras son provisionales y se revisan cuando sabemos cómo has respondido.</p>
        </article>
      </section>

      <section className="landing-page__steps">
        <header>
          <p className="eyebrow">Cómo funciona</p>
          <h2>Una temporada que aprende de cada semana.</h2>
        </header>
        <div className="landing-page__step-list">
          <article><span>01</span><div><h3>Cuéntanos tu punto de partida</h3><p>Perfil, objetivo, disponibilidad e historial reciente.</p></div></article>
          <article><span>02</span><div><h3>Entrena con una semana concreta</h3><p>Sesiones con duración, potencia, intervalos y carga estimada.</p></div></article>
          <article><span>03</span><div><h3>Revisamos antes de dar el siguiente paso</h3><p>Lo realizado y tu respuesta orientan la próxima semana.</p></div></article>
        </div>
      </section>

      <footer className="landing-page__footer">
        <div>
          <span className="landing-page__brand-mark">VF</span>
          <strong>Veloform</strong>
        </div>
        <p>Planifica mejor. Entrena con contexto.</p>
        <Link className="landing-page__outline-link" to="/register">
          Empezar ahora
        </Link>
      </footer>
    </main>
  );
}
