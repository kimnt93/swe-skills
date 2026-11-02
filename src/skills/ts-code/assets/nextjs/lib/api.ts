// The one HTTP client. Every API answers the envelope
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
    const headers: Record<string, string> = { accept: "application/json" };
    const init: RequestInit = { method, headers, cache: "no-store" };
    if (body !== undefined) {
      headers["content-type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    let response: Response;
    try {
      response = await fetchImpl(`${baseUrl}${path}`, init);
    } catch {
      throw new ApiError(503, "unreachable", `cannot reach the API for ${path}`, true);
    }
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

/** Server-side client: API_BASE_URL is server-only and never reaches the browser. */
export function serverClient(): Client {
  const base = process.env.API_BASE_URL;
  if (!base) {
    throw new Error("API_BASE_URL is not set");
  }
  return createClient(base);
}
