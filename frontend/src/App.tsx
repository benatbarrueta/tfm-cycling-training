import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { AppHeader } from "./components/AppHeader";
import { DashboardPage } from "./pages/DashboardPage";
import { ProfilePage } from "./pages/ProfilePage";
import { WeeklyPlan } from "./components/WeeklyPlan";
import { trainingPlanMock } from "./mocks/trainingPlan";
import { CalendarPage } from "./pages/CalendarPage";
import "./styles/App.css";

function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <main className="placeholder-page">
      <p className="placeholder-page__eyebrow">
        Cycling Training
      </p>

      <h1>{title}</h1>
      <p>{description}</p>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppHeader />

      <Routes>
        <Route
          path="/"
          element={<DashboardPage />}
        />

        <Route
          path="/calendar"
          element={<CalendarPage />}
        />

        <Route
          path="/plan"
          element={
            <WeeklyPlan plan={trainingPlanMock.plan} />
          }
        />

        <Route
          path="/progress"
          element={
            <PlaceholderPage
              title="Evolución"
              description={
                "Aquí mostraremos la carga, el desacoplamiento aeróbico y su evolución."
              }
            />
          }
        />

        <Route
          path="/profile"
          element={<ProfilePage />}
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;