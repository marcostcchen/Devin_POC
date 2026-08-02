import PropTypes from "prop-types";
import { formatStatus } from "../../utils/formatters.js";

export function RefundFilters({ filters, statuses, onChange, onReset }) {
  const updateFilter = (key, value) => onChange({ ...filters, [key]: value });

  return (
    <section className="refund-filters" aria-label="Queue filters">
      <div className="refund-filters__field">
        <label htmlFor="filter-status">Status</label>
        <select
          id="filter-status"
          value={filters.status}
          onChange={(event) => updateFilter("status", event.target.value)}
        >
          <option value="all">All statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {formatStatus(status)}
            </option>
          ))}
        </select>
      </div>

      <div className="refund-filters__field">
        <label htmlFor="filter-min-amount">Min amount ($)</label>
        <input
          id="filter-min-amount"
          type="number"
          min="0"
          step="1"
          value={filters.minAmount}
          onChange={(event) => updateFilter("minAmount", event.target.value)}
        />
      </div>

      <div className="refund-filters__field">
        <label htmlFor="filter-max-amount">Max amount ($)</label>
        <input
          id="filter-max-amount"
          type="number"
          min="0"
          step="1"
          value={filters.maxAmount}
          onChange={(event) => updateFilter("maxAmount", event.target.value)}
        />
      </div>

      <div className="refund-filters__field">
        <label htmlFor="filter-sort-by">Sort by</label>
        <select
          id="filter-sort-by"
          value={filters.sortBy}
          onChange={(event) => updateFilter("sortBy", event.target.value)}
        >
          <option value="createdAt">Requested date</option>
          <option value="amount">Amount</option>
          <option value="customerName">Customer</option>
          <option value="status">Status</option>
        </select>
      </div>

      <div className="refund-filters__field">
        <label htmlFor="filter-sort-direction">Direction</label>
        <select
          id="filter-sort-direction"
          value={filters.sortDirection}
          onChange={(event) =>
            updateFilter("sortDirection", event.target.value)
          }
        >
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>
      </div>

      <button type="button" className="button button--ghost" onClick={onReset}>
        Reset filters
      </button>
    </section>
  );
}

RefundFilters.propTypes = {
  filters: PropTypes.object.isRequired,
  statuses: PropTypes.arrayOf(PropTypes.string).isRequired,
  onChange: PropTypes.func.isRequired,
  onReset: PropTypes.func.isRequired,
};
