const DEFAULT_BASE_URL = "http://localhost:8000";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.API_BASE_URL ??
  DEFAULT_BASE_URL;

export async function serverFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...init
  });

  if (!res.ok) {
    const message = await safeRead(res);
    throw new Error(message || `Request failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export async function clientFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, init);
  if (!res.ok) {
    const message = await safeRead(res);
    throw new Error(message || `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

async function safeRead(res: Response) {
  try {
    const data = await res.json();
    return typeof data === "string" ? data : data.detail || JSON.stringify(data);
  } catch {
    try {
      return await res.text();
    } catch {
      return "";
    }
  }
}

