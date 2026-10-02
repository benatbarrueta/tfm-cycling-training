import type { CalendarView } from "../types/calendar";
import "../styles/CalendarToolbar.css";

interface CalendarToolbarProps {
  title: string;
  view: CalendarView;
  onViewChange: (view: CalendarView) => void;
  onPrevious: () => void;
  onToday: () => void;
  onNext: () => void;
}

const viewOptions: Array<{
  value: CalendarView;
  label: string;
}> = [
  { value: "month", label: "Mes" },
  { value: "week", label: "Semana" },
  { value: "day", label: "Día" },
];

export function CalendarToolbar({
  title,
  view,
  onViewChange,
  onPrevious,
  onToday,
  onNext,
}: CalendarToolbarProps) {
  return (
    <header className="calendar-toolbar">
      <div className="calendar-toolbar__navigation">
        <button
          type="button"
          onClick={onPrevious}
          aria-label="Periodo anterior"
        >
          ‹
        </button>

        <button
          type="button"
          onClick={onToday}
        >
          Hoy
        </button>

        <button
          type="button"
          onClick={onNext}
          aria-label="Periodo siguiente"
        >
          ›
        </button>
      </div>

      <h1>{title}</h1>

      <div
        className="calendar-toolbar__views"
        aria-label="Vista del calendario"
      >
        {viewOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            className={
              view === option.value
                ? "calendar-toolbar__view calendar-toolbar__view--active"
                : "calendar-toolbar__view"
            }
            onClick={() =>
              onViewChange(option.value)
            }
          >
            {option.label}
          </button>
        ))}
      </div>
    </header>
  );
}