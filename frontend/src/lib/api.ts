import { session } from "./session";

export const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

const DEFAULT_TIMEOUT_MS = 20000;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function requestHeaders(
  init: RequestInit,
): Headers {
  const headers = new Headers(init.headers);

  if (
    init.body &&
    !(init.body instanceof FormData)
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  const token = session.token();
  const organization = session.organization();

  if (token) {
    headers.set(
      "Authorization",
      `Bearer ${token}`,
    );
  }

  if (organization) {
    headers.set(
      "X-Organization-ID",
      organization,
    );
  }

  return headers;
}

async function errorFromResponse(
  response: Response,
): Promise<ApiError> {
  const body = await response
    .json()
    .catch(() => ({
      detail:
        "The request could not be completed",
    }));

  return new ApiError(
    response.status,
    typeof body.detail === "string"
      ? body.detail
      : "The request could not be completed",
  );
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS,
  );

  let response: Response;

  try {
    response = await fetch(
      `${API_URL}${path}`,
      {
        ...init,
        headers: requestHeaders(init),
        signal: init.signal ?? controller.signal,
      },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        0,
        "The request timed out. Please try again.",
      );
    }

    throw new ApiError(
      0,
      error instanceof Error
        ? error.message
        : "Unable to reach the server.",
    );
  } finally {
    window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw await errorFromResponse(
      response,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function apiDownload(
  path: string,
  filename: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      headers: requestHeaders({}),
    },
  );

  if (!response.ok) {
    throw await errorFromResponse(
      response,
    );
  }

  const blob = await response.blob();

  const objectUrl =
    window.URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = objectUrl;
  anchor.download = filename;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.URL.revokeObjectURL(
    objectUrl,
  );
}
