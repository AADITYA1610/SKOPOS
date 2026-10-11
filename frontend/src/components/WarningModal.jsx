function WarningModal({
  open,
  title,
  message,
  detail,
  primaryLabel = "I understand, continue",
  secondaryLabel = "Go back",
  onPrimary,
  onSecondary,
  variant = "warning",
}) {
  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onSecondary?.();
      }}
    >
      <div
        className={`modal modal--${variant}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="warning-modal-title"
      >
        <h2 id="warning-modal-title" className="modal__title">
          {title}
        </h2>
        <p className="modal__message">{message}</p>
        {detail && <div className="modal__detail">{detail}</div>}
        <div className="modal__actions">
          <button type="button" className="btn btn--ghost" onClick={onSecondary}>
            {secondaryLabel}
          </button>
          <button type="button" className="btn btn--primary" onClick={onPrimary}>
            {primaryLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export default WarningModal;
