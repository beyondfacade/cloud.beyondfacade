import { config } from "@/shared/config";

export class ApiError extends Error {
  constructor(public code: string, message: string) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  if (res.ok) return res.json() as Promise<T>;
  const body = await res.json().catch(() => null);
  const err = body?.error ?? { code: `HTTP_${res.status}`, message: res.statusText };
  throw new ApiError(err.code, err.message);
}

export const apiGet = <T>(path: string, options?: { signal?: AbortSignal }) =>
  fetch(`${config.apiBase}${path}`, options).then((r) => handle<T>(r));

export const apiPost = <T>(path: string, body: unknown, base: string = config.apiBase, options?: { signal?: AbortSignal }) =>
  fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: options?.signal,
  }).then((r) => handle<T>(r));

export const apiDelete = <T = void>(path: string) =>
  fetch(`${config.apiBase}${path}`, { method: "DELETE" }).then((r) => handle<T>(r));

const sendJson = (method: "PATCH" | "PUT") => <T>(path: string, body: unknown) =>
  fetch(`${config.apiBase}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => handle<T>(r));

export const apiPatch = sendJson("PATCH");
export const apiPut = sendJson("PUT");
