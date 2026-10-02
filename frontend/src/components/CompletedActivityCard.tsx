import type {
  ActivityRecord,
} from "../types/calendar";
import "../styles/CompletedActivityCard.css";

interface CompletedActivityCardProps {
  activity: ActivityRecord;
  onRemove: (activityId: string) => void;
}

function showMetric(
  value: number | null,
  suffix: string,
): string {
  return value === null
    ? "Sin datos"
    : `${value}${suffix}`;
}

export function CompletedActivityCard({
  activity,
  onRemove,
}: CompletedActivityCardProps) {
  return (
    <article className="completed-activity">
      <header className="completed-activity__header">
        <div>
          <span>Actividad realizada</span>
          <strong>{activity.date}</strong>
        </div>

        <button
          type="button"
          onClick={() =>
            onRemove(activity.id)
          }
        >
          Eliminar
        </button>
      </header>

      <dl className="completed-activity__metrics">
        <div>
          <dt>Duración</dt>
          <dd>
            {showMetric(
              activity.duration_minutes,
              " min",
            )}
          </dd>
        </div>

        <div>
          <dt>TSS</dt>
          <dd>
            {showMetric(activity.tss, "")}
          </dd>
        </div>

        <div>
          <dt>Potencia media</dt>
          <dd>
            {showMetric(
              activity.average_power,
              " W",
            )}
          </dd>
        </div>

        <div>
          <dt>IF</dt>
          <dd>
            {showMetric(
              activity.intensity_factor,
              "",
            )}
          </dd>
        </div>

        <div>
          <dt>Desacoplamiento</dt>
          <dd>
            {showMetric(
              activity.aerobic_decoupling,
              " %",
            )}
          </dd>
        </div>
      </dl>
    </article>
  );
}