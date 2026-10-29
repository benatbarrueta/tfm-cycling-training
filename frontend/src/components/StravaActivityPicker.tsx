import { useEffect, useState, type FormEvent } from "react";
import { IntegrationLogo } from "./IntegrationLogo";
import { useStravaActivities } from "../hooks/useStravaActivities";

function isoDate(date: Date) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function initialDates() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 29);
  return { start: isoDate(start), end: isoDate(end) };
}

function formatHours(minutes: number) {
  return `${(minutes / 60).toLocaleString("es-ES", { maximumFractionDigits: 1 })} h`;
}

function displayDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("es-ES");
}

export function StravaActivityPicker({ onClose }: { onClose: () => void }) {
  const [dates] = useState(initialDates);
  const [start, setStart] = useState(dates.start);
  const [appliedStart, setAppliedStart] = useState(dates.start);
  const [synchronizing, setSynchronizing] = useState(false);
  const strava = useStravaActivities();
  const loadPreview = strava.loadPreview;

  useEffect(() => {
    void loadPreview(dates);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [dates, loadPreview, onClose]);

  function previewSync(event: FormEvent) {
    event.preventDefault();
    setAppliedStart(start);
    void loadPreview({ start, end: dates.end });
  }

  async function activateSync() {
    setSynchronizing(true);
    await strava.synchronize(appliedStart);
    setSynchronizing(false);
  }

  return (
    <div className="strava-picker__overlay" role="presentation" onMouseDown={onClose}>
      <section
        className="strava-picker strava-picker--setup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="strava-picker-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="strava-picker__header">
          <IntegrationLogo provider="STRAVA" className="strava-picker__logo" />
          <div>
            <p>Strava conectado</p>
            <h2 id="strava-picker-title">Configura la sincronización</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar configuración de Strava">×</button>
        </header>

        <div className="strava-picker__body strava-sync-setup">
          <div className="strava-sync-setup__intro">
            <strong>Tus salidas, sin importarlas una a una</strong>
            <p>Elige desde qué fecha quieres recuperar tu historial y deja preparada la cuenta para sincronizar automáticamente las nuevas actividades.</p>
          </div>

          <form className="strava-sync-setup__form" onSubmit={previewSync}>
            <label>
              <span>Importar actividades desde</span>
              <input type="date" value={start} max={dates.end} onChange={(event) => setStart(event.target.value)} required />
            </label>
            <button type="submit" disabled={strava.status === "loading"}>
              {strava.status === "loading" ? "Consultando…" : "Calcular actividades"}
            </button>
          </form>

          <div className="strava-sync-setup__scope">
            <span aria-hidden="true">✓</span>
            <div><strong>Solo ciclismo</strong><p>Se incluirán carretera, montaña, gravel, ciclismo virtual y bicicletas eléctricas.</p></div>
          </div>

          {strava.status === "loading" && (
            <p className="strava-picker__state" role="status">
              {synchronizing ? "Importando actividades y calculando sus métricas…" : "Buscando todas tus actividades de ciclismo…"}
            </p>
          )}
          {strava.status === "error" && (
            <div className="strava-picker__state strava-picker__state--error" role="alert">
              <p>{strava.error}</p>
              <button type="button" onClick={() => void loadPreview({ start: appliedStart, end: dates.end })}>Reintentar</button>
            </div>
          )}
          {strava.status === "empty" && (
            <div className="strava-picker__state">
              <strong>No hay actividades de ciclismo desde esa fecha</strong>
              <p>Prueba con una fecha anterior o comprueba que las actividades estén disponibles en Strava.</p>
            </div>
          )}
          {strava.status === "ready" && strava.syncResult === null && (
            <section className="strava-sync-setup__preview" aria-live="polite">
              <div className="strava-sync-setup__summary">
                <div><strong>{strava.preview.importable}</strong><span>se incorporarán</span></div>
                <div><strong>{formatHours(strava.preview.durationMinutes)}</strong><span>de actividad</span></div>
                <div><strong>{strava.preview.distanceKm.toLocaleString("es-ES", { maximumFractionDigits: 0 })} km</strong><span>recorridos</span></div>
              </div>
              <p>
                Se han encontrado {strava.preview.total} actividades desde el {displayDate(appliedStart)}.
                {strava.preview.duplicates > 0 && ` ${strava.preview.duplicates} ya existen en Veloform y se omitirán.`}
              </p>
            </section>
          )}
          {strava.syncResult !== null && (
            <section className="strava-sync-setup__result" role="status">
              <strong>{strava.syncResult.failed > 0 ? "Sincronización completada con incidencias" : "Sincronización completada"}</strong>
              <div>
                <span><b>{strava.syncResult.imported}</b> importadas</span>
                <span><b>{strava.syncResult.skipped}</b> omitidas</span>
                <span><b>{strava.syncResult.failed}</b> con incidencias</span>
              </div>
              <p>La cuenta ha quedado configurada desde el {displayDate(strava.syncResult.start_date)} y preparada para la sincronización automática.</p>
            </section>
          )}
        </div>

        <footer className="strava-picker__footer">
          <button type="button" onClick={onClose}>{strava.syncResult === null ? "Cancelar" : "Cerrar"}</button>
          {strava.syncResult === null ? (
            <button
              type="button"
              disabled={strava.status !== "ready" || strava.preview.importable === 0 || synchronizing}
              onClick={() => void activateSync()}
            >
              Importar {strava.preview.importable} y activar sincronización
            </button>
          ) : (
            <button type="button" onClick={() => window.location.assign("/calendar")}>Ver en calendario</button>
          )}
        </footer>
      </section>
    </div>
  );
}
