import uuid

import pytest
from django.urls import reverse

from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.tests.factories import ReservationFactory, UserFactory, grant_permission


def _staff_user(*codenames):
    user = UserFactory(is_staff=True)
    for codename in codenames:
        grant_permission(user=user, codename=codename)
    return user


@pytest.mark.django_db
def test_reservation_list_requires_login(client):
    response = client.get(reverse("reservation_list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_reservation_list_renders_for_user_with_permission(client):
    reservation = ReservationFactory()
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_list"))

    assert response.status_code == 200
    assert reservation.customer.display_name in response.content.decode()


@pytest.mark.django_db
def test_reservation_confirm_requires_permission(client):
    reservation = ReservationFactory()
    user = UserFactory()
    client.force_login(user)

    response = client.post(reverse("reservation_confirm", args=[reservation.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_reservation_confirm_invalid_transition_shows_error_instead_of_500(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)
    client.force_login(_staff_user("view_reservation", "change_reservation"))

    response = client.post(
        reverse("reservation_confirm", args=[reservation.id]), follow=True
    )

    assert response.status_code == 200
    assert "no puede cambiar" in response.content.decode()
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED


# --- ON_HOLD -----------------------------------------------------------------


@pytest.mark.django_db
def test_hold_requires_login(client):
    reservation = ReservationFactory()

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Waiting"},
    )

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.django_db
def test_hold_is_forbidden_without_hold_permission_even_with_change_permission(client):
    """Mirrors the seeded `operator` group: can edit but cannot put on hold."""
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    client.force_login(_staff_user("view_reservation", "change_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Waiting"},
    )

    assert response.status_code == 403
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_hold_with_permission_updates_status_and_reason(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Customer asked to wait"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("reservation_detail", args=[reservation.id])
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_ON_HOLD
    assert reservation.hold_reason == "Customer asked to wait"


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [{}, {"hold_reason": ""}, {"hold_reason": "   "}])
def test_hold_without_reason_returns_422_and_keeps_status(client, payload):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(reverse("reservation_hold", args=[reservation.id]), payload)

    assert response.status_code == 422
    assert "El motivo es obligatorio." in response.content.decode()
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_hold_invalid_transition_redirects_with_error(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Waiting"},
        follow=True,
    )

    assert response.status_code == 200
    assert "no puede cambiar" in response.content.decode()
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED


@pytest.mark.django_db
def test_hold_unknown_reservation_returns_404(client):
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[uuid.uuid4()]),
        {"hold_reason": "Waiting"},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_detail_shows_hold_reason_and_list_shows_on_hold_status(client):
    reservation = ReservationFactory(
        status=RESERVATION_STATUS_ON_HOLD, hold_reason="Pending documents"
    )
    client.force_login(_staff_user("view_reservation"))

    detail = client.get(reverse("reservation_detail", args=[reservation.id]))
    listing = client.get(reverse("reservation_list"))

    assert "Pending documents" in detail.content.decode()
    assert "On hold" in listing.content.decode()
    assert "badge--on_hold" in listing.content.decode()


@pytest.mark.django_db
def test_detail_shows_hold_form_only_with_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    hold_url = reverse("reservation_hold", args=[reservation.id])
    detail_url = reverse("reservation_detail", args=[reservation.id])

    client.force_login(_staff_user("view_reservation", "change_reservation"))
    assert hold_url not in client.get(detail_url).content.decode()

    client.force_login(_staff_user("view_reservation", "hold_reservation"))
    assert hold_url in client.get(detail_url).content.decode()
