import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  commitActivityImport,
  getActivity,
  previewActivityFile,
  type Activity,
  type ActivityImportPreview,
} from "../api/activities";
import { ActivityForm } from "../components/ActivityForm";
import { IntegrationLogo } from "../components/IntegrationLogo";
import { StravaActivityPicker } from "../components/StravaActivityPicker";
import { useActivities } from "../hooks/useActivities";
import "../styles/ActivitiesPage.css";
import { useIntegrations } from "../hooks/useIntegrations";

function localDateTime(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function metric(value: number | null, suffix = "") {
  return value === null ? "—" : `${value}${suffix}`;
}

export function ActivitiesPage() {
  const [searchParams] = useSearchParams();
  const handledEditId = useRef<string | null>(null);
  const importInputRef = useRef<HTMLInputElement | null>(null);
  const { activities, total, status, error, refresh, addActivity, editActivity, removeActivity, linkActivity } = useActivities({ limit: 50 });
  const [editing, setEditing] = useState<Activity | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [importPreview, setImportPreview] = useState<ActivityImportPreview | null>(null);
  const [importing, setImporting] = useState(false);
  const [draggingFile, setDraggingFile] = useState(false);
  const [showStravaPicker, setShowStravaPicker] = useState(false);
  const integrations = useIntegrations();

  useEffect(() => {
    const editId = searchParams.get("edit");
    if (editId === null || handledEditId.current === editId) return;
    handledEditId.current = editId;
    void getActivity(editId)
      .then((activity) => {
        setEditing(activity);
        setShowForm(false);
      })
      .catch((cause: unknown) => {
        setMessage(cause instanceof Error ? cause.message : "No se ha podido abrir la actividad.");
      });
  }, [searchParams]);

  useEffect(() => {
    if (importPreview === null) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setImportPreview(null);
        setFormError(null);
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [importPreview]);

  async function deleteItem(activity: Activity) {
    if (!window.confirm(`¿Eliminar "${activity.title}" del historial?`)) return;
    try {
      await removeActivity(activity.id);
      setMessage("Actividad eliminada.");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "No se ha podido eliminar la actividad.");
    }
  }

  const tss = activities.reduce((totalValue, item) => totalValue + (item.tss ?? 0), 0);
  const estimatedRpeLoad = activities.reduce(
    (totalValue, item) => totalValue + (item.load_source === "RPE" ? item.estimated_load ?? 0 : 0),
    0,
  );

  async function selectImportFile(file: File | undefined) {
    if (file === undefined) return;
    setImporting(true);
    setFormError(null);
    setMessage(null);
    try {
      const preview = await previewActivityFile(file);
      setImportPreview(preview);
      setEditing(null);
      setShowForm(false);
    } catch (cause) {
      setFormError(cause instanceof Error ? cause.message : "No se ha podido analizar el archivo.");
    } finally {
      setImporting(false);
    }
  }

  function handleImportDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setDraggingFile(false);
    if (importing) return;
    void selectImportFile(event.dataTransfer.files[0]);
  }

  function openImportPicker(event: KeyboardEvent<HTMLElement>) {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    importInputRef.current?.click();
  }

  function closeImportPreview() {
    setImportPreview(null);
    setFormError(null);
  }

  return (
    <main className="activities-page">
      <header className="activities-page__header">
        <div><p className="activities-page__eyebrow">Historial</p><h1>Actividades</h1><p>Añade tus entrenamientos para que el sistema pueda calcular tu carga y adaptar el plan.</p></div>
        <div className="activities-page__header-actions">
          <button className="button button--primary activities-page__add-button" type="button" onClick={() => { setImportPreview(null); setEditing(null); setShowForm((value) => !value); }}>
            {showForm ? "Cerrar formulario" : "＋ Añadir actividad"}
          </button>
        </div>
      </header>
      {!integrations.loading && !integrations.strava?.connected && (
        <aside className="activities-page__strava-prompt">
          <IntegrationLogo provider="STRAVA" className="activities-page__integration-logo" />
          <div>
            <strong>¿Usas Strava?</strong>
            <p>Conecta tu cuenta para encontrar tus actividades sin descargar archivos.</p>
          </div>
          <Link to="/profile#connections">Configurar en el perfil</Link>
        </aside>
      )}
      {!integrations.loading && integrations.strava?.connected && (
        <aside className="activities-page__strava-prompt activities-page__strava-prompt--connected">
          <IntegrationLogo provider="STRAVA" className="activities-page__integration-logo" />
          <div>
            <strong>Strava conectado</strong>
            <p>Elige desde qué fecha quieres recuperar tus salidas y configura la sincronización automática.</p>
          </div>
          <button type="button" onClick={() => setShowStravaPicker(true)}>Configurar sincronización</button>
        </aside>
      )}
      {showStravaPicker && <StravaActivityPicker onClose={() => setShowStravaPicker(false)} />}
      <section
        className={`activities-page__drop-zone${draggingFile ? " activities-page__drop-zone--active" : ""}${importing ? " activities-page__drop-zone--busy" : ""}`}
        aria-label="Importar una actividad FIT o TCX"
        aria-busy={importing}
        role="button"
        tabIndex={0}
        onClick={() => importInputRef.current?.click()}
        onKeyDown={openImportPicker}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!importing) setDraggingFile(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = importing ? "none" : "copy";
        }}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
            setDraggingFile(false);
          }
        }}
        onDrop={handleImportDrop}
      >
        <input
          ref={importInputRef}
          className="visually-hidden"
          type="file"
          accept=".fit,.tcx"
          disabled={importing}
          tabIndex={-1}
          onChange={(event) => {
            void selectImportFile(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        <span className="activities-page__drop-icon" aria-hidden="true">⇩</span>
        <div>
          <strong>{importing ? "Analizando actividad…" : draggingFile ? "Suelta el archivo para analizarlo" : "Arrastra aquí tu actividad"}</strong>
          <span>Archivos FIT o TCX · También puedes pulsar para seleccionarlo</span>
        </div>
      </section>
      <section className="activities-page__summary" aria-label="Resumen del historial">
        <article><strong>{total}</strong><span>actividades</span></article>
        <article><strong>{tss.toFixed(0)}</strong><span>TSS cargado</span></article>
        <article><strong>{estimatedRpeLoad.toFixed(0)}</strong><span>carga estimada por RPE</span></article>
        <article><strong>{activities.filter((item) => item.aerobic_decoupling !== null).length}</strong><span>con desacoplamiento</span></article>
      </section>
      {importPreview !== null && (
        <div className="activities-page__import-overlay" role="presentation" onMouseDown={closeImportPreview}>
          <section
            className="activities-page__import-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="activity-import-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header>
              <div>
                <p className="activities-page__eyebrow">Archivo analizado</p>
                <h2 id="activity-import-title">Revisa la actividad antes de importarla</h2>
                <p>{importPreview.filename}</p>
              </div>
              <div className="activities-page__import-dialog-actions">
                {importPreview.duplicate && <strong>Este archivo ya se había importado</strong>}
                <button type="button" onClick={closeImportPreview} aria-label="Cerrar importación" autoFocus>×</button>
              </div>
            </header>
            <div className="activities-page__import-dialog-body">
              {formError && <p className="activities-page__import-error" role="alert">{formError}</p>}
              <ActivityForm
                initialValues={{
                  ...importPreview.activity,
                  started_at: localDateTime(importPreview.activity.started_at),
                }}
                submitLabel="Confirmar importación"
                fieldWarnings={importPreview.warnings ?? {}}
                onCancel={closeImportPreview}
                onSubmit={async (input, plannedWorkoutId) => {
                  try {
                    await commitActivityImport(importPreview, input, plannedWorkoutId);
                    await refresh();
                    closeImportPreview();
                    setMessage("Actividad importada correctamente.");
                  } catch (cause) {
                    setFormError(cause instanceof Error ? cause.message : "No se ha podido importar la actividad.");
                  }
                }}
              />
            </div>
          </section>
        </div>
      )}
      {(showForm || editing) && (
        <ActivityForm
          initialValues={editing ? { ...editing, started_at: localDateTime(editing.started_at) } : undefined}
          initialPlannedWorkoutId={editing?.planned_workout_id}
          activityId={editing?.id}
          submitLabel={editing ? "Editar actividad" : "Guardar actividad"}
          onCancel={() => { setShowForm(false); setEditing(null); }}
          onSubmit={async (input, plannedWorkoutId) => {
            try {
              if (editing) {
                if (editing.planned_workout_id !== plannedWorkoutId && editing.planned_workout_id !== null) {
                  await linkActivity(editing.id, null);
                }
                const updated = await editActivity(editing.id, input);
                if (updated.planned_workout_id !== plannedWorkoutId) {
                  await linkActivity(updated.id, plannedWorkoutId);
                }
              } else {
                const created = await addActivity(input);
                if (plannedWorkoutId !== null) await linkActivity(created.id, plannedWorkoutId);
              }
              setShowForm(false); setEditing(null); setFormError(null);
              setMessage(editing ? "Actividad actualizada." : "Actividad guardada.");
            } catch (cause) {
              setFormError(cause instanceof Error ? cause.message : "No se ha podido guardar la actividad.");
            }
          }}
        />
      )}
      {formError && importPreview === null && (
        <p className="activities-page__page-error" role="alert">{formError}</p>
      )}
      {message && <p role="status">{message}</p>}
      <section className="activities-page__history">
        <header><div><h2>Historial reciente</h2><p>Las actividades se ordenan desde la más reciente.</p></div><span className="activities-page__history-note">Guardadas en tu cuenta</span></header>
        {status === "loading" && <p role="status">Cargando actividades…</p>}
        {status === "error" && <div role="alert"><p>{error}</p><button type="button" onClick={() => void refresh()}>Reintentar</button></div>}
        {status === "empty" && <div className="activities-page__empty"><strong>No hay actividades registradas</strong><p>Utiliza el formulario superior para añadir tu primer entrenamiento.</p></div>}
        {status === "ready" && (
          <div className="activities-page__table-wrapper">
            <table className="activities-page__table"><thead><tr><th>Actividad</th><th>Fecha</th><th>Duración</th><th>Distancia</th><th>Potencia</th><th>FC</th><th>Carga</th><th>Sesión</th><th>Acciones</th></tr></thead>
              <tbody>{activities.map((activity) => <tr key={activity.id}>
                <td>
                  <strong className="activities-page__activity-title">{activity.title}</strong>
                  <small className="activities-page__activity-source">
                    {activity.source === "MANUAL"
                      ? "Introducida manualmente"
                      : activity.source === "FILE_IMPORT"
                        ? "Importada desde archivo"
                        : activity.source}
                  </small>
                </td>
                <td>{new Date(activity.started_at).toLocaleString("es-ES")}</td>
                <td>{metric(activity.duration_minutes, " min")}</td><td>{metric(activity.distance_km, " km")}</td><td>{metric(activity.average_power, " W")}</td><td>{metric(activity.average_heart_rate, " ppm")}</td>
                <td>
                  {activity.load_source === "TSS" && `${activity.tss?.toFixed(0)} TSS`}
                  {activity.load_source === "RPE" && `${activity.estimated_load?.toFixed(0)} RPE·min`}
                  {activity.load_source === "UNKNOWN" && "Sin datos"}
                </td>
                <td><span className={activity.planned_workout_id === null ? "activities-page__link-status activities-page__link-status--extra" : "activities-page__link-status"}>{activity.planned_workout_id === null ? "Actividad adicional" : "Vinculada"}</span></td>
                <td className="activities-page__actions">
                  <button
                    className="activities-page__edit"
                    type="button"
                    onClick={() => { setEditing(activity); setShowForm(false); }}
                  >
                    Editar
                  </button>
                  <button className="activities-page__delete" type="button" onClick={() => void deleteItem(activity)}>
                    Eliminar
                  </button>
                </td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
