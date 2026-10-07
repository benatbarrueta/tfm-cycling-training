export const storageKeys = {
  profile: "veloform-profile",
  activities: "veloform-activities",
} as const;

const legacyStorageKeys = {
  profile: "cycling-training-profile",
  activities: "cycling-training-activities",
} as const;

export function readMigratedStorage<T>(
  key: keyof typeof legacyStorageKeys,
  parse: (value: unknown) => T | null,
): T | null {
  const currentKey = storageKeys[key];
  const legacyKey = legacyStorageKeys[key];
  const currentValue = localStorage.getItem(currentKey);

  if (currentValue !== null) {
    return parseStoredValue(currentValue, parse);
  }

  const legacyValue = localStorage.getItem(legacyKey);
  if (legacyValue === null) {
    return null;
  }

  const parsed = parseStoredValue(legacyValue, parse);
  if (parsed === null) {
    return null;
  }

  localStorage.setItem(currentKey, JSON.stringify(parsed));
  localStorage.removeItem(legacyKey);
  return parsed;
}

function parseStoredValue<T>(
  value: string,
  parse: (value: unknown) => T | null,
): T | null {
  try {
    return parse(JSON.parse(value));
  } catch {
    return null;
  }
}
