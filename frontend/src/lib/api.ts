import { session } from "./session";

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const DEFAULT_TIMEOUT_MS = 20000;
export const AUTH_TIMEOUT_MS = 60000;
export const LARGE_UPLOAD_TIMEOUT_MS = 1800000;
export const AI_ANALYSIS_TIMEOUT_MS = 1800000;
export const OPPORTUNITY_ANALYSIS_TIMEOUT_MS = 1800000;
export type ApiRequestInit = RequestInit & { timeoutMs?: number; };
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}
function requestHeaders(init: RequestInit): Headers {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const token = session.token();
  const organization = session.organization();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (organization) headers.set("X-Organization-ID", organization);
  return headers;
}
function timeoutForPath(path: string, init: ApiRequestInit): number {
  if (init.timeoutMs !== undefined) return init.timeoutMs;
  if (init.body instanceof FormData) return LARGE_UPLOAD_TIMEOUT_MS;
  if (path.startsWith("/auth/")) return AUTH_TIMEOUT_MS;
  if (path.endsWith("/analyze")) return path.startsWith("/opportunities/") ? OPPORTUNITY_ANALYSIS_TIMEOUT_MS : AI_ANALYSIS_TIMEOUT_MS;
  return DEFAULT_TIMEOUT_MS;
}
function readableDetail(body: unknown): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return "The request could not be completed.";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((item: { msg?: string; loc?: (string | number)[]; }) => `${item.loc?.filter((v) => v !== "body").join(" / ") ?? "Field"}: ${item.msg ?? "invalid value"}`).join(". ");
  return "The request could not be completed.";
}
function ensureSameWorkspace(snapshot: string) {
  if (session.snapshot() !== snapshot) throw new ApiError(409, "The active workspace changed. Please try again in the current workspace.");
}

async function request<T>(path: string, init: ApiRequestInit, read: (response: Response) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const snapshot = session.snapshot();
  const externalSignal = init.signal;
  let timedOut = false;
  const cancel = () => controller.abort();
  if (externalSignal?.aborted) controller.abort();
  else externalSignal?.addEventListener("abort", cancel, { once: true });
  const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, timeoutForPath(path, init));
  const { timeoutMs: _timeoutMs, ...fetchInit } = init;
  void _timeoutMs;
  try {
    const response = await fetch(`${API_URL}${path}`, { ...fetchInit, headers: requestHeaders(init), signal: controller.signal });
    ensureSameWorkspace(snapshot);
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null);
      throw new ApiError(response.status, readableDetail(body));
    }
    const result = await read(response);
    ensureSameWorkspace(snapshot);
    return result;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) {
      if (externalSignal?.aborted) throw new ApiError(0, "Request aborted by user.");
      throw new ApiError(0, timedOut ? "The request timed out. Refresh the status before retrying an analysis." : "The request was aborted.");
    }
    throw new ApiError(0, error instanceof Error ? error.message : "Unable to reach the server.");
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", cancel);
  }
}
export function api<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  return request<T>(path, init, async (response) => response.status === 204 ? undefined as T : await response.json() as T);
}
export function apiBlob(path: string): Promise<Blob> {
  return request(path, { timeoutMs: LARGE_UPLOAD_TIMEOUT_MS }, (response) => response.blob());
}
export async function apiDownload(path: string, filename: string): Promise<void> {
  const blob = await apiBlob(path);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl; anchor.download = filename;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

/** Byte-based upload progress. 100% means transmitted, not yet stored or analyzed. */
export function apiUpload<T>(path: string, form: FormData, onProgress?: (percent: number) => void, signal?: AbortSignal): Promise<T> {
  const snapshot = session.snapshot();
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const cancel = () => xhr.abort();
    const cleanup = () => signal?.removeEventListener("abort", cancel);
    if (signal?.aborted) { reject(new ApiError(0, "Request aborted by user.")); return; }
    xhr.open("POST", `${API_URL}${path}`);
    xhr.timeout = LARGE_UPLOAD_TIMEOUT_MS;
    requestHeaders({ body: form }).forEach((value, key) => xhr.setRequestHeader(key, value));
    xhr.upload.onprogress = (event) => { if (event.lengthComputable && event.total > 0) onProgress?.(Math.min(100, Math.round(event.loaded / event.total * 100))); };
    xhr.onload = () => {
      cleanup();
      try {
        ensureSameWorkspace(snapshot);
        const body: unknown = xhr.responseText ? JSON.parse(xhr.responseText) : null;
        if (xhr.status < 200 || xhr.status >= 300) throw new ApiError(xhr.status, readableDetail(body));
        resolve(body as T);
      } catch (error) { reject(error instanceof ApiError ? error : new ApiError(xhr.status, "The server returned an unreadable response. Refresh before uploading again.")); }
    };
    xhr.onerror = () => { cleanup(); reject(new ApiError(0, "The upload connection was interrupted. Refresh documents before retrying.")); };
    xhr.ontimeout = () => { cleanup(); reject(new ApiError(0, "The upload timed out. Check whether the file was saved before retrying.")); };
    xhr.onabort = () => { cleanup(); reject(new ApiError(0, "Request aborted by user.")); };
    signal?.addEventListener("abort", cancel, { once: true });
    xhr.send(form);
  });
}
