/** Single place where API errors surface, dismissible by the user. */

interface Props {
  error: string | null;
  onDismiss: () => void;
}

export function ErrorBanner({ error, onDismiss }: Props) {
  if (!error) return null;

  return (
    <div className="banner" role="alert">
      <span className="error">⚠ {error}</span>
      <button className="link spacer" onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  );
}
