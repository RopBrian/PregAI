import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import './ConfirmDialog.css';

const ConfirmDialog = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  isBusy = false,
  error = null,
  onCancel,
  onConfirm
}) => {
  if (!isOpen) return null;

  return (
    <div className="confirm-dialog-overlay fade-in" onClick={onCancel}>
      <div
        className="confirm-dialog glass-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="confirm-dialog-close"
          onClick={onCancel}
          aria-label="Close confirmation"
          disabled={isBusy}
        >
          <X size={20} />
        </button>

        <div className="confirm-dialog-icon">
          <AlertTriangle size={30} />
        </div>

        <h2 id="confirm-dialog-title">{title}</h2>
        <p>{message}</p>

        {error && <div className="confirm-dialog-error">{error}</div>}

        <div className="confirm-dialog-actions">
          <button
            type="button"
            className="confirm-dialog-cancel"
            onClick={onCancel}
            disabled={isBusy}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className="confirm-dialog-delete"
            onClick={onConfirm}
            disabled={isBusy}
          >
            {isBusy ? 'Deleting...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
