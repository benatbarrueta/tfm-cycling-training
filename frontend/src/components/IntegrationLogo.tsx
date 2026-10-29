import stravaLogo from "../assets/integrations/strava-app.jpg";

const integrationLogos = {
  STRAVA: stravaLogo,
} as const;

export type IntegrationProvider = keyof typeof integrationLogos;

export function IntegrationLogo({
  provider,
  className,
}: {
  provider: IntegrationProvider;
  className?: string;
}) {
  return (
    <img
      className={className}
      src={integrationLogos[provider]}
      alt=""
      aria-hidden="true"
    />
  );
}
