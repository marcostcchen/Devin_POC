/** Composes the panel: identity bar, create form, flag table, evaluate, feed. */

import { AuditList } from "./components/AuditList";
import { EvaluatePanel } from "./components/EvaluatePanel";
import { FlagTable } from "./components/FlagTable";
import { IdentityBar } from "./components/IdentityBar";
import { NewFlagForm } from "./components/NewFlagForm";
import { useAdminPanel } from "./hooks/useAdminPanel";

export default function App() {
  const panel = useAdminPanel();

  return (
    <main>
      <IdentityBar identity={panel.identity} error={panel.error} onActAs={panel.actAs} />
      <NewFlagForm disabled={!panel.isAdmin} onCreate={panel.createFlag} />
      <FlagTable
        flags={panel.flags}
        isAdmin={panel.isAdmin}
        onUpdate={panel.updateFlag}
        onDelete={panel.deleteFlag}
        loadHistory={panel.loadHistory}
      />
      <EvaluatePanel onEvaluate={panel.evaluate} />
      <section className="card">
        <strong>Recent activity</strong>
        <AuditList entries={panel.activity} emptyText="no activity yet" />
      </section>
    </main>
  );
}
