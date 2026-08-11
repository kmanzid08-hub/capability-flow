import { session } from "./session";

const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);

  headers.set("Content-Type", "application/json");

  const token = session.token();
  const organization = session.organization();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (organization) {
    headers.set("X-Organization-ID", organization);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({
        detail: "The request could not be completed",
      }));

    throw new ApiError(
      response.status,
      typeof body.detail === "string"
        ? body.detail
        : "The request could not be completed",
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}