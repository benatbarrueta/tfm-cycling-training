import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { AppHeader } from "./components/AppHeader";
import { DashboardPage } from "./pages/DashboardPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SeasonPlanPage, } from "./pages/SeasonPlanPage";
import { CalendarPage } from "./pages/CalendarPage";
import { ProgressPage } from "./pages/ProgressPage";
import "./styles/App.css";

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
          element={<SeasonPlanPage />}
        />

        <Route
          path="/progress"
          element={<ProgressPage />}
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