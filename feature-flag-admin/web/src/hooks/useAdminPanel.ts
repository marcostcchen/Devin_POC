/** State container for the panel: identity, flags, activity and errors. */

import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { AuditEntry, Flag, FlagCreate, FlagUpdate, Identity } from "../types";

const ACTIVITY_LIMIT = 15;

export interface AdminPanel {
  identity: Identity | null;
  flags: Flag[];
  activity: AuditEntry[];
  error: string | null;
  isAdmin: boolean;
  actAs: (email: string) => void;
  clearError: () => void;
  /** Each mutation resolves to whether it succeeded, so callers can react. */
  createFlag: (flag: FlagCreate) => Promise<boolean>;
  updateFlag: (id: number, changes: FlagUpdate) => Promise<boolean>;
  deleteFlag: (id: number) => Promise<boolean>;
  loadHistory: (id: number) => Promise<AuditEntry[]>;
  evaluate: (flag: string, userId: string, team: string) => Promise<string | null>;
}

export function useAdminPanel(): AdminPanel {
  // Empty until the first /api/me: the server picks the default identity.
  const [actor, setActor] = useState("");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [flags, setFlags] = useState<Flag[]>([]);
  const [activity, setActivity] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (email: string) => {
    const [nextFlags, nextActivity] = await Promise.all([
      api.listFlags(email),
      api.recentActivity(email, ACTIVITY_LIMIT),
    ]);
    setFlags(nextFlags);
    setActivity(nextActivity);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const me = await api.me(actor);
        setIdentity(me);
        await refresh(me.email);
        setError(null);
      } catch (err) {
        setError((err as Error).message);
      }
    })();
  }, [actor, refresh]);

  /** Run a mutation, refresh the view, and surface any failure as `error`. */
  const mutate = useCallback(
    async (action: (email: string) => Promise<unknown>): Promise<boolean> => {
      const email = identity?.email ?? "";
      try {
        await action(email);
        await refresh(email);
        setError(null);
        return true;
      } catch (err) {
        setError((err as Error).message);
        return false;
      }
    },
    [identity, refresh],
  );

  const loadHistory = useCallback(
    async (id: number) => {
      try {
        return await api.flagHistory(identity?.email ?? "", id);
      } catch (err) {
        setError((err as Error).message);
        return [];
      }
    },
    [identity],
  );

  const evaluate = useCallback(
    async (flag: string, userId: string, team: string) => {
      try {
        const result = await api.evaluate(identity?.email ?? "", flag, userId, team);
        setError(null);
        return `${result.enabled ? "ENABLED" : "DISABLED"} — ${result.reason}`;
      } catch (err) {
        setError((err as Error).message);
        return null;
      }
    },
    [identity],
  );

  return {
    identity,
    flags,
    activity,
    error,
    isAdmin: identity?.role === "admin",
    actAs: setActor,
    clearError: () => setError(null),
    createFlag: (flag) => mutate((email) => api.createFlag(email, flag)),
    updateFlag: (id, changes) => mutate((email) => api.updateFlag(email, id, changes)),
    deleteFlag: (id) => mutate((email) => api.deleteFlag(email, id)),
    loadHistory,
    evaluate,
  };
}
