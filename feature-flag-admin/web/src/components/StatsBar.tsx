/** At-a-glance counts derived from the flag list. */

import type { Flag } from "../types";

interface Props {
  flags: Flag[];
}

export function StatsBar({ flags }: Props) {
  const enabled = flags.filter((flag) => flag.enabled);
  const partial = enabled.filter((flag) => flag.rollout_percentage < 100);
  const teams = new Set(flags.filter((flag) => flag.target_team).map((f) => f.target_team));

  const stats: Array<[string, number]> = [
    ["Flags", flags.length],
    ["Enabled", enabled.length],
    ["Partial rollout", partial.length],
    ["Targeted teams", teams.size],
  ];

  return (
    <div className="stats">
      {stats.map(([label, value]) => (
        <div className="stat" key={label}>
          <div className="stat-value">{value}</div>
          <div className="stat-label">{label}</div>
        </div>
      ))}
    </div>
  );
}
