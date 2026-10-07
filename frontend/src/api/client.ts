import type { ApiErrorDetails } from "./types";

export class ApiError extends Error implements ApiErrorDetails {
  status: number;
  kind: ApiErrorDetails["kind"];

  constructor(details: ApiErrorDetails) {
    super(details.message);
    this.name = "ApiError";
    this.status = details.status;
    this.kind = details.kind;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError({
      status: 0,
      message: "No se ha podido conectar con el backend.",
      kind: "network",
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError({
      status: response.status,
      message: "El backend ha devuelto una respuesta no válida.",
      kind: "invalid-response",
    });
  }

  if (!response.ok) {
    const message =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof data.detail === "string"
        ? data.detail
        : "No se ha podido completar la operación.";
    throw new ApiError({
      status: response.status,
      message,
      kind: "http",
    });
  }

  return data as T;
}
