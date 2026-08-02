import { useEffect, useState } from "react";
import { fetchAppConfig } from "../api/refundsApi.js";

const FALLBACK_CONFIG = {
  approvalThresholdAmount: 200,
  statuses: [],
  reasonCodes: [],
  roles: [],
};

/** Loads server-owned constants (threshold, statuses, reason codes) once on mount. */
export function useAppConfig() {
  const [appConfig, setAppConfig] = useState(FALLBACK_CONFIG);

  useEffect(() => {
    let cancelled = false;

    fetchAppConfig()
      .then((payload) => {
        if (!cancelled) setAppConfig(payload);
      })
      .catch(() => {
        // The dashboard still renders with fallback values if /config is unreachable.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return appConfig;
}
