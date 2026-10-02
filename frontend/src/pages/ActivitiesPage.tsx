import { useState } from "react";
import { ActivityForm } from "../components/ActivityForm";
import type { ActivityInput } from "../types/training";
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
  const [activities, setActivities] = useState<
    ActivityInput[]
  >([]);

  function addActivity(activity: ActivityInput) {
    setActivities((currentActivities) =>
      [activity, ...currentActivities].sort(
        (first, second) =>
          second.date.localeCompare(first.date),
      ),
    );
  }

  function removeActivity(index: number) {
    setActivities((currentActivities) =>
      currentActivities.filter(
        (_, activityIndex) =>
          activityIndex !== index,
      ),
    );
  }

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

        <div className="activities-page__counter">
          <strong>{activities.length}</strong>
          <span>actividades registradas</span>
        </div>
      </header>

      <ActivityForm onSubmit={addActivity} />

      <section className="activities-page__history">
        <header>
          <div>
            <h2>Historial reciente</h2>
            <p>
              Las actividades se ordenan desde la más
              reciente.
            </p>
          </div>

          <button type="button">
            Importar archivo
          </button>
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
                {activities.map((activity, index) => (
                  <tr
                    key={`${activity.date}-${index}`}
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
                        onClick={() =>
                          removeActivity(index)
                        }
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