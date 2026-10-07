import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useEffect, useState } from "react";
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
import { useCyclistProfile } from "./hooks/useCyclistProfile";
import "./styles/App.css";

function App() {
  const auth = useAuth();

  if (auth.status === "loading") {
    return <div className="app-loading" role="status">Comprobando sesión…</div>;
  }

  return (
    <BrowserRouter>
      <AppRoutes
        auth={auth}
      />
    </BrowserRouter>
  );
}

interface AppRoutesProps {
  auth: ReturnType<typeof useAuth>;
}

function AppRoutes({ auth }: AppRoutesProps) {
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    try {
      await auth.logout();
      navigate("/login", { replace: true });
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <>
      <ScrollToTop />
      <PageTitle />
      {auth.isAuthenticated && (
        <AppHeader user={auth.user} onSignOut={signOut} signingOut={signingOut} />
      )}
      {auth.user?.is_demo && (
        <div className="demo-banner" role="status">
          Estás utilizando Veloform en modo demostración.
        </div>
      )}

      <Routes>
        <Route
          element={
            <PublicOnly
              isAuthenticated={auth.isAuthenticated}
            />
          }
        >
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthPage mode="login" onDemoAccess={auth.loginAsDemo} onGoogleLogin={auth.loginWithGoogle} />} />
          <Route path="/register" element={<AuthPage mode="register" onDemoAccess={auth.loginAsDemo} onGoogleLogin={auth.loginWithGoogle} />} />
        </Route>
        <Route element={<PrivateRoutes isAuthenticated={auth.isAuthenticated} />}>
          <Route element={<ProfileRequired />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/activities" element={<ActivitiesPage />} />
            <Route path="/plan" element={<SeasonPlanPage />} />
            <Route path="/progress" element={<ProgressPage />} />
          </Route>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
        </Route>
        <Route path="*" element={<Navigate to={auth.isAuthenticated ? "/dashboard" : "/"} replace />} />
      </Routes>
    </>
  );
}

function ProfileRequired() {
  const { profile, loading } = useCyclistProfile();
  if (loading) return <div className="app-loading" role="status">Cargando perfil…</div>;
  return profile ? <Outlet /> : <Navigate to="/onboarding" replace />;
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