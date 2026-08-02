/**
 * Typed client for the admin API.
 *
 * Every call carries the acting identity in the `X-User` header, which the
 * server trusts (no real auth in this POC). Under the POC platform the gateway
 * overwrites that header with the persona selected in its console.
 *
 * Paths are relative to `BASE_URL` ("/" standalone, "/apps/feature-flag-admin/"
 * under the platform) so the same build works at either mount point.
 */

import type {
  AuditEntry,
  EvaluationResult,
  Flag,
  FlagCreate,
  FlagUpdate,
  Identity,
} from "./types";

/** A non-2xx response, carrying the server's `detail` as its message. */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ValidationIssue {
  loc?: (string | number)[];
  msg: string;
}

/** Flatten FastAPI's 422 issue list into one readable line. */
function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (detail as ValidationIssue[])
      .map((issue) => `${issue.loc?.at(-1) ?? "request"}: ${issue.msg}`)
      .join("; ");
  }
  return fallback;
}

const API_ROOT = `${import.meta.env.BASE_URL.replace(/\/$/, "")}/api`;

async function request<T>(path: string, actor: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-User": actor, ...init.headers },
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      detail = ((await response.json()) as { detail?: unknown }).detail ?? detail;
    } catch {
      // Non-JSON error body; the status text is the best we have.
    }
    throw new ApiError(formatDetail(detail, response.statusText), response.status);
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  /** Resolve an identity; pass an empty actor to get the server default. */
  me: (actor: string) => request<Identity>("/me", actor),

  listFlags: (actor: string) => request<Flag[]>("/flags", actor),

  createFlag: (actor: string, flag: FlagCreate) =>
    request<Flag>("/flags", actor, { method: "POST", body: JSON.stringify(flag) }),

  updateFlag: (actor: string, id: number, changes: FlagUpdate) =>
    request<Flag>(`/flags/${id}`, actor, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),

  deleteFlag: (actor: string, id: number) =>
    request<void>(`/flags/${id}`, actor, { method: "DELETE" }),

  flagHistory: (actor: string, id: number) =>
    request<AuditEntry[]>(`/flags/${id}/audit`, actor),

  recentActivity: (actor: string, limit = 15) =>
    request<AuditEntry[]>(`/audit?limit=${limit}`, actor),

  evaluate: (actor: string, flag: string, userId: string, team: string) => {
    const params = new URLSearchParams({ user_id: userId, team });
    return request<EvaluationResult>(`/evaluate/${encodeURIComponent(flag)}?${params}`, actor);
  },
};
