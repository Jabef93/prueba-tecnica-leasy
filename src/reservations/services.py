from __future__ import annotations

from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db import transaction

from reservations.constants import (
    PERMISSION_HOLD_RESERVATION,
    RESERVATION_CANCELLABLE_STATUSES,
    RESERVATION_HOLDABLE_STATUSES,
    RESERVATION_REASON_MAX_LENGTH,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CONFIRMED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.exceptions import (
    ReservationNotFoundError,
    ReservationReasonRequiredError,
    ReservationReasonTooLongError,
    ReservationStatusTransitionError,
)
from reservations.models import Reservation


def normalize_reason(reason: str | None) -> str:
    """Strip and validate a free-text reason required by a lifecycle transition."""
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ReservationReasonRequiredError()
    if len(cleaned) > RESERVATION_REASON_MAX_LENGTH:
        raise ReservationReasonTooLongError()
    return cleaned


class ReservationQueryService:
    def get_reservation(self, *, reservation_id: UUID) -> Reservation:
        try:
            return Reservation.objects.select_related("customer__user", "room").get(
                pk=reservation_id
            )
        except Reservation.DoesNotExist as exc:
            raise ReservationNotFoundError() from exc


class ReservationUpdateService:
    def __init__(self) -> None:
        self._query_service = ReservationQueryService()

    @transaction.atomic
    def update_reservation(
        self,
        *,
        reservation_id: UUID,
        room_id: UUID,
        starts_at,
        ends_at,
        internal_note: str,
    ) -> Reservation:
        reservation = self._query_service.get_reservation(reservation_id=reservation_id)
        reservation.room_id = room_id
        reservation.starts_at = starts_at
        reservation.ends_at = ends_at
        reservation.internal_note = internal_note
        reservation.save(
            update_fields=["room", "starts_at", "ends_at", "internal_note", "updated_at"]
        )
        return reservation


class ReservationLifecycleService:
    def __init__(self) -> None:
        self._query_service = ReservationQueryService()

    @transaction.atomic
    def confirm_reservation(
        self,
        *,
        reservation_id: UUID,
        actor_id: int | None = None,
    ) -> Reservation:
        _ = actor_id
        reservation = self._get_for_update(reservation_id=reservation_id)

        if reservation.status != RESERVATION_STATUS_REQUESTED:
            raise ReservationStatusTransitionError()

        reservation.status = RESERVATION_STATUS_CONFIRMED
        reservation.save(update_fields=["status", "updated_at"])
        return reservation

    @transaction.atomic
    def hold_reservation(
        self,
        *,
        reservation_id: UUID,
        reason: str,
        actor: AbstractBaseUser,
    ) -> Reservation:
        # Defense in depth: the view already enforces the permission, but the
        # business rule must hold for any caller of the service.
        if not actor.has_perm(PERMISSION_HOLD_RESERVATION):
            raise PermissionDenied

        cleaned_reason = normalize_reason(reason)
        reservation = self._get_for_update(reservation_id=reservation_id)

        if reservation.status not in RESERVATION_HOLDABLE_STATUSES:
            raise ReservationStatusTransitionError()

        reservation.status = RESERVATION_STATUS_ON_HOLD
        reservation.hold_reason = cleaned_reason
        reservation.save(update_fields=["status", "hold_reason", "updated_at"])
        return reservation

    @transaction.atomic
    def cancel_reservation(
        self,
        *,
        reservation_id: UUID,
        customer_id: UUID,
        reason: str,
    ) -> Reservation:
        """Cancel a reservation on behalf of its owner.

        The lookup is scoped by ``customer_id`` so a reservation owned by someone
        else is indistinguishable from a missing one (no existence leak).
        """
        cleaned_reason = normalize_reason(reason)
        reservation = self._get_for_update(
            reservation_id=reservation_id, customer_id=customer_id
        )

        if reservation.status not in RESERVATION_CANCELLABLE_STATUSES:
            raise ReservationStatusTransitionError()

        reservation.status = RESERVATION_STATUS_CANCELLED
        reservation.cancel_reason = cleaned_reason
        reservation.save(update_fields=["status", "cancel_reason", "updated_at"])
        return reservation

    def _get_for_update(
        self, *, reservation_id: UUID, customer_id: UUID | None = None
    ) -> Reservation:
        # of=("self",) locks only the reservation row; without it PostgreSQL
        # would also lock the joined customer/user/room rows.
        filters = {"pk": reservation_id}
        if customer_id is not None:
            filters["customer_id"] = customer_id
        try:
            return (
                Reservation.objects.select_for_update(of=("self",))
                .select_related("customer__user", "room")
                .get(**filters)
            )
        except Reservation.DoesNotExist as exc:
            raise ReservationNotFoundError() from exc
