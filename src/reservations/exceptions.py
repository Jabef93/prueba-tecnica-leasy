from shared.errors import DomainError


class ReservationError(DomainError):
    code = "reservation_error"
    detail = "Reservation error."


class ReservationNotFoundError(ReservationError):
    code = "reservation_not_found"
    detail = "Reservation not found."


class ReservationStatusTransitionError(ReservationError):
    code = "reservation_invalid_transition"
    detail = "Reservation cannot transition from its current status."


class ReservationReasonRequiredError(ReservationError):
    code = "reservation_reason_required"
    detail = "A reason is required for this action."


class ReservationReasonTooLongError(ReservationError):
    code = "reservation_reason_too_long"
    detail = "The reason is too long."
