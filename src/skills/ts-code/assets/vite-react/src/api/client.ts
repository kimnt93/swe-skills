// The one HTTP client of the app. Every API answers the envelope
// {success, status_code, message, data, error: {code, retryable}} (api-contract skill);
// this unwraps `data` or throws ApiError carrying the error code.

export interface Envelope<T> {
  success: boolean;
  status_code: number;
  message: string;
  data: T;
  error: { code: string; retryable: boolean };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;

  constructor(status: number, code: string, message: string, retryable: boolean) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

export type Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export function createClient(baseUrl: string, fetchImpl: Fetch = fetch) {
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const init: RequestInit = { method, headers: { accept: "application/json" } };
    if (body !== undefined) {
      init.headers = { ...init.headers, "content-type": "application/json" };
      init.body = JSON.stringify(body);
    }
    const response = await fetchImpl(`${baseUrl}${path}`, init);
    let envelope: Envelope<T>;
    try {
      envelope = (await response.json()) as Envelope<T>;
    } catch {
      throw new ApiError(response.status, "invalid_response", `non-JSON response from ${path}`, false);
    }
    if (!envelope.success) {
      throw new ApiError(envelope.status_code, envelope.error.code, envelope.message, envelope.error.retryable);
    }
    return envelope.data;
  }

  return {
    get: <T>(path: string) => request<T>("GET", path),
    post: <T>(path: string, body: unknown) => request<T>("POST", path, body),
    delete: <T>(path: string) => request<T>("DELETE", path),
  };
}

export type Client = ReturnType<typeof createClient>;

export const api = createClient(import.meta.env.VITE_API_BASE_URL ?? "");
