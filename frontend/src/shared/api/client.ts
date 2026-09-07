import { config } from "@/shared/config";

export class ApiError extends Error {
  constructor(public code: string, message: string) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>;
  const body = await res.json().catch(() => null);
  const err = body?.error ?? { code: `HTTP_${res.status}`, message: res.statusText };
  throw new ApiError(err.code, err.message);
}

export const apiGet = <T>(path: string) =>
  fetch(`${config.apiBase}${path}`).then((r) => handle<T>(r));

export const apiPost = <T>(path: string, body: unknown, base: string = config.apiBase) =>
  fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => handle<T>(r));
