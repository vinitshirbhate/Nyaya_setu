const DEFAULT_BASE_URL = "http://localhost:8000";
const DEFAULT_DOCUMENT_API_URL = "http://localhost:8001";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.API_BASE_URL ??
  DEFAULT_BASE_URL;

export const DOCUMENT_API_BASE_URL =
  process.env.NEXT_PUBLIC_DOCUMENT_API_BASE_URL ??
  process.env.DOCUMENT_API_BASE_URL ??
  DEFAULT_DOCUMENT_API_URL;

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

// Document RAG API Client Functions
export async function documentClientFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${DOCUMENT_API_BASE_URL}${path}`, init);
  if (!res.ok) {
    const message = await safeRead(res);
    throw new Error(message || `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

