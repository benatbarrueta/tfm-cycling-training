import { useNavigate } from "react-router-dom";
import { ProfilePage } from "./ProfilePage";
import type { AuthenticatedUser } from "../api/types";

export function OnboardingPage({ user }: { user: AuthenticatedUser | null }) {
  const navigate = useNavigate();

  return (
    <ProfilePage user={user} onSaved={() => navigate("/dashboard", { replace: true })} />
  );
}
