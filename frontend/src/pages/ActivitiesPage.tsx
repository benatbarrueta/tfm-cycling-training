import { useState } from "react";
import { ActivityForm } from "../components/ActivityForm";
import { useActivities } from "../hooks/useActivities";
import "../styles/ActivitiesPage.css";

function formatValue(
  value: number | null,
  suffix = "",
): string {
  return value === null
    ? "—"
    : `${value}${suffix}`;
}

export function ActivitiesPage() {
  const { activities, addActivity, removeActivity } = useActivities();
  const [showForm, setShowForm] = useState(false);
  const totalTss = activities.reduce((total, activity) => total + (activity.tss ?? 0), 0);
  const decouplings = activities
    .map((activity) => activity.aerobic_decoupling)
    .filter((value): value is number => value !== null);
  const averageDecoupling = decouplings.length > 0
    ? decouplings.reduce((total, value) => total + value, 0) / decouplings.length
    : null;

  return (
    <main className="activities-page">
      <header className="activities-page__header">
        <div>
          <p className="activities-page__eyebrow">
            Historial
          </p>

          <h1>Actividades</h1>

          <p>
            Añade tus entrenamientos para que el sistema
            pueda calcular tu carga y adaptar el plan.
          </p>
        </div>

        <button
          className="button button--primary activities-page__add-button"
          type="button"
          onClick={() => setShowForm((visible) => !visible)}
        >
          {showForm ? "Cerrar formulario" : "＋ Añadir actividad"}
        </button>
      </header>

      <section className="activities-page__summary" aria-label="Resumen del historial">
        <article><strong>{activities.length}</strong><span>actividades</span></article>
        <article><strong>{totalTss.toFixed(0)}</strong><span>TSS acumulado</span></article>
        <article><strong>{averageDecoupling === null ? "—" : `${averageDecoupling.toFixed(1)}%`}</strong><span>desacoplamiento medio</span></article>
      </section>

      {showForm && (
        <ActivityForm
          onSubmit={(activity) => {
            addActivity(activity);
            setShowForm(false);
          }}
        />
      )}

      <section className="activities-page__history">
        <header>
          <div>
            <h2>Historial reciente</h2>
            <p>
              Las actividades se ordenan desde la más
              reciente.
            </p>
          </div>

          <span className="activities-page__history-note">
            Tus sesiones se guardan en este dispositivo
          </span>
        </header>

        {activities.length === 0 ? (
          <div className="activities-page__empty">
            <strong>No hay actividades registradas</strong>
            <p>
              Utiliza el formulario superior para añadir
              tu primer entrenamiento.
            </p>
          </div>
        ) : (
          <div className="activities-page__table-wrapper">
            <table className="activities-page__table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Duración</th>
                  <th>Potencia</th>
                  <th>IF</th>
                  <th>TSS</th>
                  <th>Desacoplamiento</th>
                  <th>
                    <span className="visually-hidden">
                      Acciones
                    </span>
                  </th>
                </tr>
              </thead>

              <tbody>
                {activities.map((activity) => (
                  <tr
                    key={activity.id}
                  >
                    <td>{activity.date}</td>

                    <td>
                      {formatValue(
                        activity.duration_minutes,
                        " min",
                      )}
                    </td>

                    <td>
                      {formatValue(
                        activity.average_power,
                        " W",
                      )}
                    </td>

                    <td>
                      {formatValue(
                        activity.intensity_factor,
                      )}
                    </td>

                    <td>
                      {formatValue(activity.tss)}
                    </td>

                    <td>
                      {formatValue(
                        activity.aerobic_decoupling,
                        " %",
                      )}
                    </td>

                    <td>
                      <button
                        className="activities-page__delete"
                        type="button"
                        onClick={() => removeActivity(activity.id)}
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}