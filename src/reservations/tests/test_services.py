import uuid

import pytest
from django.core.exceptions import PermissionDenied

from reservations.constants import (
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
from reservations.services import ReservationLifecycleService
from reservations.tests.factories import ReservationFactory, UserFactory, grant_permission


@pytest.fixture
def hold_actor(db):
    user = UserFactory()
    grant_permission(user=user, codename="hold_reservation")
    return user


@pytest.mark.django_db
def test_confirm_reservation_moves_requested_to_confirmed():
    reservation = ReservationFactory(status="requested")

    ReservationLifecycleService().confirm_reservation(reservation_id=reservation.id)

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CONFIRMED


@pytest.mark.django_db
def test_confirm_reservation_rejects_invalid_transition():
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().confirm_reservation(reservation_id=reservation.id)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status", [RESERVATION_STATUS_REQUESTED, RESERVATION_STATUS_CONFIRMED]
)
def test_hold_reservation_moves_to_on_hold_and_stores_reason(hold_actor, initial_status):
    reservation = ReservationFactory(status=initial_status)

    ReservationLifecycleService().hold_reservation(
        reservation_id=reservation.id,
        reason="  Waiting for payment confirmation  ",
        actor=hold_actor,
    )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_ON_HOLD
    assert reservation.hold_reason == "Waiting for payment confirmation"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status", [RESERVATION_STATUS_CANCELLED, RESERVATION_STATUS_ON_HOLD]
)
def test_hold_reservation_rejects_invalid_transition(hold_actor, initial_status):
    reservation = ReservationFactory(status=initial_status)

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason="Any reason",
            actor=hold_actor,
        )

    reservation.refresh_from_db()
    assert reservation.status == initial_status
    assert reservation.hold_reason == ""


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", "   ", None])
def test_hold_reservation_requires_reason(hold_actor, reason):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    with pytest.raises(ReservationReasonRequiredError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason=reason,
            actor=hold_actor,
        )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_hold_reservation_rejects_too_long_reason(hold_actor):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    with pytest.raises(ReservationReasonTooLongError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason="x" * (RESERVATION_REASON_MAX_LENGTH + 1),
            actor=hold_actor,
        )


@pytest.mark.django_db
def test_hold_reservation_requires_permission_at_service_level():
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    user_without_permission = UserFactory()
    grant_permission(user=user_without_permission, codename="change_reservation")

    with pytest.raises(PermissionDenied):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason="Any reason",
            actor=user_without_permission,
        )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_hold_reservation_raises_not_found_for_unknown_id(hold_actor):
    with pytest.raises(ReservationNotFoundError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=uuid.uuid4(),
            reason="Any reason",
            actor=hold_actor,
        )


@pytest.mark.django_db
def test_seed_assessment_data_is_idempotent():
    from django.core.management import call_command

    from reservations.models import Reservation

    call_command("seed_assessment_data")
    first_count = Reservation.objects.count()

    call_command("seed_assessment_data")
    second_count = Reservation.objects.count()

    assert first_count == 3
    assert second_count == first_count
