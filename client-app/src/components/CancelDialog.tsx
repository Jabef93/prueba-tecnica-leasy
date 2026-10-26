import { FormEvent, useState } from "react";
import { ApiError } from "../api/client";
import type { Reservation } from "../api/types";

interface CancelDialogProps {
  reservation: Reservation;
  onConfirm: (reservationId: string, reason: string) => Promise<void>;
  onClose: () => void;
}

const REASON_MAX_LENGTH = 500;

export function CancelDialog({
  reservation,
  onConfirm,
  onClose,
}: CancelDialogProps) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = reason.trim();
    if (!trimmed) {
      setError("Debes ingresar un motivo para cancelar la reserva.");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await onConfirm(reservation.id, trimmed);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.message} (código: ${err.code})`);
      } else {
        setError("No se pudo cancelar la reserva. Inténtalo de nuevo.");
      }
      setSubmitting(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancel-modal-title"
    >
      <div className="modal card stack">
        <div>
          <h3 id="cancel-modal-title" className="card-title">
            Cancelar reserva · {reservation.room_name}
          </h3>
          <p className="muted">
            Inicio: {new Date(reservation.starts_at).toLocaleString("es-PE")}
          </p>
        </div>

        {error && (
          <div className="alert alert--error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="stack">
          <div className="field">
            <label htmlFor="cancel-reason">
              <strong>Motivo de cancelación *</strong>
            </label>
            <textarea
              id="cancel-reason"
              rows={3}
              maxLength={REASON_MAX_LENGTH}
              placeholder="Ej.: Cambio de agenda o reunión reprogramada..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={submitting}
              autoFocus
            />
            <span className="muted field-help">
              {reason.trim().length}/{REASON_MAX_LENGTH} caracteres
            </span>
          </div>

          <div className="actions actions--end">
            <button
              type="button"
              className="btn"
              onClick={onClose}
              disabled={submitting}
            >
              Volver
            </button>
            <button
              type="submit"
              className="btn btn-danger"
              disabled={submitting}
            >
              {submitting ? "Cancelando..." : "Confirmar cancelación"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
