/**
 * Composition root: top bar, error banner, summary stats, then a two-column
 * workspace with the flag list beside the evaluate / activity rail.
 */

import { AuditList } from "./components/AuditList";
import { ErrorBanner } from "./components/ErrorBanner";
import { EvaluatePanel } from "./components/EvaluatePanel";
import { FlagTable } from "./components/FlagTable";
import { IdentityBar } from "./components/IdentityBar";
import { StatsBar } from "./components/StatsBar";
import { useAdminPanel } from "./hooks/useAdminPanel";

export default function App() {
  const panel = useAdminPanel();

  return (
    <>
      <IdentityBar identity={panel.identity} onActAs={panel.actAs} />
      <main className="page">
        <ErrorBanner error={panel.error} onDismiss={panel.clearError} />
        <StatsBar flags={panel.flags} />
        <div className="workspace">
          <FlagTable
            flags={panel.flags}
            isAdmin={panel.isAdmin}
            onCreate={panel.createFlag}
            onUpdate={panel.updateFlag}
            onDelete={panel.deleteFlag}
            loadHistory={panel.loadHistory}
          />
          <div className="rail">
            <EvaluatePanel onEvaluate={panel.evaluate} />
            <section className="card">
              <div className="card-head">
                <h2>Recent activity</h2>
                <span className="pill spacer">{panel.activity.length}</span>
              </div>
              <div className="card-body">
                <AuditList entries={panel.activity} emptyText="No activity yet." />
              </div>
            </section>
          </div>
        </div>
      </main>
    </>
  );
}
