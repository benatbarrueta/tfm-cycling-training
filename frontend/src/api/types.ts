export interface AuthenticatedUser {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  email_verified: boolean;
  is_demo: boolean;
}

export interface ApiErrorDetails {
  status: number;
  message: string;
  kind: "http" | "network" | "invalid-response";
}
