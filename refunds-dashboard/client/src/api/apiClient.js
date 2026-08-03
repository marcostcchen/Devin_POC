// Under the POC platform the API is served from the same origin, one level
// below the app's mount point (`/apps/refunds-dashboard/api`), so the built
// client follows Vite's BASE_URL instead of the standalone dev-server URL.
const API_BASE_URL = import.meta.env.VITE_PLATFORM_BASE_PATH
  ? `${import.meta.env.BASE_URL.replace(/\/$/, "")}/api`
  : (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:4000/api");

/** Error carrying the API's status code and per-field validation details. */
export class ApiError extends Error {
  constructor(message, { status, details } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details ?? [];
  }
}

export async function request(path, { method = "GET", body, actor } = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        // Mocked identity headers driven by the role switcher.
        ...(actor
          ? { "x-user-role": actor.role, "x-user-name": actor.name }
          : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the refunds API. Is the server running?");
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      payload?.error?.message ??
        `Request failed with status ${response.status}`,
      {
        status: response.status,
        details: payload?.error?.details,
      },
    );
  }

  return payload;
}
