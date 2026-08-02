import PropTypes from "prop-types";

export function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onDismiss ? (
        <button
          type="button"
          className="error-banner__dismiss"
          onClick={onDismiss}
        >
          Dismiss
        </button>
      ) : null}
    </div>
  );
}

ErrorBanner.propTypes = {
  message: PropTypes.string,
  onDismiss: PropTypes.func,
};
