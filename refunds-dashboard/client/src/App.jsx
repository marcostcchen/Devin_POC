import { useState } from "react";
import { AppHeader } from "./components/layout/AppHeader.jsx";
import { SummaryMetrics } from "./components/dashboard/SummaryMetrics.jsx";
import { RefundFilters } from "./components/queue/RefundFilters.jsx";
import { RefundQueue } from "./components/queue/RefundQueue.jsx";
import { NewRefundRequestForm } from "./components/queue/NewRefundRequestForm.jsx";
import { RefundDetailPanel } from "./components/detail/RefundDetailPanel.jsx";
import { ErrorBanner } from "./components/common/ErrorBanner.jsx";
import { useAppConfig } from "./hooks/useAppConfig.js";
import { useRefundsData } from "./hooks/useRefundsData.js";

const DEFAULT_FILTERS = {
  status: "pending",
  minAmount: "",
  maxAmount: "",
  sortBy: "createdAt",
  sortDirection: "desc",
};

export default function App() {
  const appConfig = useAppConfig();
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [selectedRefundId, setSelectedRefundId] = useState(null);
  const { refundRequests, metrics, isLoading, loadError, reload } =
    useRefundsData(filters);

  const selectedRefundRequest =
    refundRequests.find((refund) => refund.id === selectedRefundId) ?? null;

  return (
    <div className="app">
      <AppHeader approvalThresholdAmount={appConfig.approvalThresholdAmount} />
      <ErrorBanner message={loadError} />
      <SummaryMetrics metrics={metrics} />

      <main className="app__body">
        <section className="panel queue-panel">
          <h2 className="panel__title">Requests queue</h2>
          <RefundFilters
            filters={filters}
            statuses={appConfig.statuses}
            onChange={setFilters}
            onReset={() => setFilters(DEFAULT_FILTERS)}
          />
          <RefundQueue
            refundRequests={refundRequests}
            isLoading={isLoading}
            selectedRefundId={selectedRefundId}
            onSelect={setSelectedRefundId}
          />
          <NewRefundRequestForm
            reasonCodes={appConfig.reasonCodes}
            onCreated={reload}
          />
        </section>

        <RefundDetailPanel
          refundRequest={selectedRefundRequest}
          onDecisionRecorded={reload}
        />
      </main>
    </div>
  );
}
