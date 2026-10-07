import { useNavigate } from "react-router-dom";
import { ProfilePage } from "./ProfilePage";

export function OnboardingPage() {
  const navigate = useNavigate();

  return (
    <ProfilePage onSaved={() => navigate("/dashboard", { replace: true })} />
  );
}
