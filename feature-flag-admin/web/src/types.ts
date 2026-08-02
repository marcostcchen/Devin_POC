/** Mirrors the pydantic schemas in `app/models.py`. */

export type Role = "admin" | "viewer";

export interface Identity {
  email: string;
  role: Role;
  /** Every identity the switcher may act as, keyed by email. Empty under the platform. */
  users: Record<string, Role>;
  display_name: string;
  /** True when the POC platform chose the identity, so the local switcher is hidden. */
  platform_managed: boolean;
  platform_console_url: string;
}

export interface Flag {
  id: number;
  name: string;
  description: string;
  enabled: boolean;
  rollout_percentage: number;
  target_team: string;
  created_at: string;
  updated_at: string;
}

export interface AuditEntry {
  id: number;
  flag_id: number;
  flag_name: string;
  actor: string;
  action: string;
  detail: string;
  created_at: string;
}

export interface EvaluationResult {
  flag: string;
  user_id: string;
  team: string;
  enabled: boolean;
  reason: string;
}

export interface FlagCreate {
  name: string;
  description: string;
  enabled: boolean;
  rollout_percentage: number;
  target_team: string;
}

/** Fields a PATCH may carry; omitted keys are left untouched server-side. */
export type FlagUpdate = Partial<
  Pick<Flag, "description" | "enabled" | "rollout_percentage" | "target_team">
>;
