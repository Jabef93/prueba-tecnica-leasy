import type { Reservation, ReservationStatus } from "../api/types";

interface ReservationListProps {
  reservations: Reservation[];
  loading: boolean;
  onRefresh: () => void;
  onRequestCancel: (reservation: Reservation) => void;
}

const STATUS_LABELS: Record<ReservationStatus, string> = {
  requested: "Solicitada",
  confirmed: "Confirmada",
  on_hold: "En espera",
  cancelled: "Cancelada",
};

const CANCELLABLE_STATUSES = new Set<ReservationStatus>([
  "requested",
  "confirmed",
  "on_hold",
]);

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function ReservationList({
  reservations,
  loading,
  onRefresh,
  onRequestCancel,
}: ReservationListProps) {
  return (
    <div className="card stack">
      <div className="topbar">
        <div>
          <h2 className="card-title">Mis reservas</h2>
          <p className="muted">
            Consulta el estado de tus reservas o cancélalas indicando el motivo.
          </p>
        </div>
        <button
          type="button"
          className="btn"
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? "Actualizando..." : "Actualizar"}
        </button>
      </div>

      {loading && reservations.length === 0 ? (
        <p className="muted">Cargando reservas...</p>
      ) : reservations.length === 0 ? (
        <p className="muted">No tienes reservas registradas.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Sala</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Estado</th>
                <th>Motivo de cancelación</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {reservations.map((reservation) => {
                const canCancel = CANCELLABLE_STATUSES.has(reservation.status);
                return (
                  <tr key={reservation.id}>
                    <td>
                      <strong>{reservation.room_name}</strong>
                    </td>
                    <td>{formatDateTime(reservation.starts_at)}</td>
                    <td>{formatDateTime(reservation.ends_at)}</td>
                    <td>
                      <span
                        className={`badge badge--${reservation.status}`}
                        data-status={reservation.status}
                      >
                        {STATUS_LABELS[reservation.status] ??
                          reservation.status}
                      </span>
                    </td>
                    <td>{reservation.cancel_reason || "—"}</td>
                    <td>
                      {canCancel ? (
                        <button
                          type="button"
                          className="btn btn-danger"
                          onClick={() => onRequestCancel(reservation)}
                        >
                          Cancelar reserva
                        </button>
                      ) : (
                        <span className="muted">Sin acciones</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
