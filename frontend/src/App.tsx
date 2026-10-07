import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useEffect } from "react";
import { flushSync } from "react-dom";
import { AppHeader } from "./components/AppHeader";
import { useAuth } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { LandingPage } from "./pages/LandingPage";
import { ActivitiesPage } from "./pages/ActivitiesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SeasonPlanPage, } from "./pages/SeasonPlanPage";
import { CalendarPage } from "./pages/CalendarPage";
import { ProgressPage } from "./pages/ProgressPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import "./styles/App.css";

function App() {
  const auth = useAuth();

  return (
    <BrowserRouter>
      <AppRoutes
        isAuthenticated={auth.isAuthenticated}
        user={auth.user}
        isDemo={auth.isDemo}
        onSignIn={auth.signInDemo}
        onSignOut={auth.signOut}
      />
    </BrowserRouter>
  );
}

interface AppRoutesProps {
  isAuthenticated: boolean;
  user: ReturnType<typeof useAuth>["user"];
  isDemo: boolean;
  onSignIn: ReturnType<typeof useAuth>["signInDemo"];
  onSignOut: ReturnType<typeof useAuth>["signOut"];
}

function AppRoutes({
  isAuthenticated,
  user,
  isDemo,
  onSignIn,
  onSignOut,
}: AppRoutesProps) {
  const navigate = useNavigate();

  function signOut() {
    flushSync(() => {
      onSignOut();
    });
    navigate("/login", { replace: true });
  }

  function signIn() {
    onSignIn();
  }

  return (
    <>
      <ScrollToTop />
      <PageTitle />
      {isAuthenticated && (
        <AppHeader user={user} isDemo={isDemo} onSignOut={signOut} />
      )}
      {isAuthenticated && isDemo && (
        <div className="demo-banner" role="status">
          Estás utilizando Veloform en modo demostración.
        </div>
      )}

      <Routes>
        <Route
          element={
            <PublicOnly
              isAuthenticated={isAuthenticated}
            />
          }
        >
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthPage mode="login" onDemoAccess={signIn} />} />
          <Route path="/register" element={<AuthPage mode="register" onDemoAccess={signIn} />} />
        </Route>
        <Route element={<PrivateRoutes isAuthenticated={isAuthenticated} />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/activities" element={<ActivitiesPage />} />
          <Route path="/plan" element={<SeasonPlanPage />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
        </Route>
        <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/"} replace />} />
      </Routes>
    </>
  );
}

function ScrollToTop() {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname, location.search]);

  return null;
}

function PageTitle() {
  const location = useLocation();

  useEffect(() => {
    document.title = "Veloform";
  }, [location.pathname]);

  return null;
}

function PublicOnly({
  isAuthenticated,
}: {
  isAuthenticated: boolean;
}) {
  return isAuthenticated ? (
    <Navigate to="/dashboard" replace />
  ) : (
    <Outlet />
  );
}

function PrivateRoutes({ isAuthenticated }: { isAuthenticated: boolean }) {
  const location = useLocation();
  return isAuthenticated ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace state={{ from: location.pathname }} />
  );
}

export default App;