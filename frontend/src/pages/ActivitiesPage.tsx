import { useState } from "react";
import type { Activity } from "../api/activities";
import { ActivityForm } from "../components/ActivityForm";
import { useActivities } from "../hooks/useActivities";
import "../styles/ActivitiesPage.css";

function localDateTime(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function metric(value: number | null, suffix = "") {
  return value === null ? "—" : `${value}${suffix}`;
}

export function ActivitiesPage() {
  const { activities, total, status, error, refresh, addActivity, editActivity, removeActivity } = useActivities({ limit: 50 });
  const [editing, setEditing] = useState<Activity | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

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

  return (
    <main className="activities-page">
      <header className="activities-page__header">
        <div><p className="activities-page__eyebrow">Historial</p><h1>Actividades</h1><p>Añade tus entrenamientos para que el sistema pueda calcular tu carga y adaptar el plan.</p></div>
        <button className="button button--primary activities-page__add-button" type="button" onClick={() => { setEditing(null); setShowForm((value) => !value); }}>
          {showForm ? "Cerrar formulario" : "＋ Añadir actividad"}
        </button>
      </header>
      <section className="activities-page__summary" aria-label="Resumen del historial">
        <article><strong>{total}</strong><span>actividades</span></article>
        <article><strong>{tss.toFixed(0)}</strong><span>TSS cargado</span></article>
        <article><strong>{activities.filter((item) => item.aerobic_decoupling !== null).length}</strong><span>con desacoplamiento</span></article>
      </section>
      {(showForm || editing) && (
        <ActivityForm
          initialValues={editing ? { ...editing, started_at: localDateTime(editing.started_at) } : undefined}
          submitLabel={editing ? "Editar actividad" : "Guardar actividad"}
          onCancel={() => { setShowForm(false); setEditing(null); }}
          onSubmit={async (input) => {
            try {
              if (editing) await editActivity(editing.id, input);
              else await addActivity(input);
              setShowForm(false); setEditing(null); setFormError(null);
              setMessage(editing ? "Actividad actualizada." : "Actividad guardada.");
            } catch (cause) {
              setFormError(cause instanceof Error ? cause.message : "No se ha podido guardar la actividad.");
            }
          }}
        />
      )}
      {formError && <p role="alert">{formError}</p>}
      {message && <p role="status">{message}</p>}
      <section className="activities-page__history">
        <header><div><h2>Historial reciente</h2><p>Las actividades se ordenan desde la más reciente.</p></div><span className="activities-page__history-note">Guardadas en tu cuenta</span></header>
        {status === "loading" && <p role="status">Cargando actividades…</p>}
        {status === "error" && <div role="alert"><p>{error}</p><button type="button" onClick={() => void refresh()}>Reintentar</button></div>}
        {status === "empty" && <div className="activities-page__empty"><strong>No hay actividades registradas</strong><p>Utiliza el formulario superior para añadir tu primer entrenamiento.</p></div>}
        {status === "ready" && (
          <div className="activities-page__table-wrapper">
            <table className="activities-page__table"><thead><tr><th>Actividad</th><th>Fecha</th><th>Duración</th><th>Distancia</th><th>Potencia</th><th>FC</th><th>TSS</th><th>Acciones</th></tr></thead>
              <tbody>{activities.map((activity) => <tr key={activity.id}>
                <td>
                  <strong className="activities-page__activity-title">{activity.title}</strong>
                  <small className="activities-page__activity-source">
                    {activity.source === "MANUAL" ? "Introducida manualmente" : activity.source}
                  </small>
                </td>
                <td>{new Date(activity.started_at).toLocaleString("es-ES")}</td>
                <td>{metric(activity.duration_minutes, " min")}</td><td>{metric(activity.distance_km, " km")}</td><td>{metric(activity.average_power, " W")}</td><td>{metric(activity.average_heart_rate, " ppm")}</td><td>{metric(activity.tss)}</td>
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
