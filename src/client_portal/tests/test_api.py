import uuid

import pytest

from client_portal.security import ClientTokenService
from reservations.constants import (
    RESERVATION_REASON_MAX_LENGTH,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CONFIRMED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.tests.factories import CustomerFactory, ReservationFactory, UserFactory


@pytest.mark.django_db
def test_login_returns_access_token(client):
    user = UserFactory(email="alice@example.com", username="alice", password="demo1234")
    customer = CustomerFactory(user=user)

    response = client.post(
        "/api/v1/auth/login",
        data={"email": customer.user.email, "password": "demo1234"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.django_db
def test_me_returns_customer_profile(client):
    customer = CustomerFactory()
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.get(
        "/api/v1/auth/me",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)


@pytest.mark.django_db
def test_reservation_list_is_scoped_to_customer(client):
    customer = CustomerFactory()
    other_customer = CustomerFactory()
    own_reservation = ReservationFactory(customer=customer)
    ReservationFactory(customer=other_customer)
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.get(
        "/api/v1/reservations/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(own_reservation.id)


# --- Cancel reservation endpoint ---------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [
        RESERVATION_STATUS_REQUESTED,
        RESERVATION_STATUS_CONFIRMED,
        RESERVATION_STATUS_ON_HOLD,
    ],
)
def test_cancel_own_reservation_succeeds(client, initial_status):
    customer = CustomerFactory()
    reservation = ReservationFactory(customer=customer, status=initial_status)
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data={"reason": "  Change of schedule  "},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(reservation.id)
    assert body["status"] == RESERVATION_STATUS_CANCELLED
    assert body["cancel_reason"] == "Change of schedule"

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED
    assert reservation.cancel_reason == "Change of schedule"


@pytest.mark.django_db
def test_cancel_other_customers_reservation_returns_404_problem_detail(client):
    owner = CustomerFactory()
    intruder = CustomerFactory()
    reservation = ReservationFactory(
        customer=owner, status=RESERVATION_STATUS_REQUESTED
    )
    token = ClientTokenService.issue_access_token(customer=intruder)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data={"reason": "Trying to cancel someone else"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "reservation_not_found"
    assert body["type"] == "urn:assessment:problem:reservation_not_found"
    assert body["status"] == 404
    assert body["instance"] == f"/api/v1/reservations/{reservation.id}/cancel"

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED
    assert reservation.cancel_reason == ""


@pytest.mark.django_db
def test_cancel_unknown_reservation_returns_404_problem_detail(client):
    customer = CustomerFactory()
    token = ClientTokenService.issue_access_token(customer=customer)
    unknown_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/reservations/{unknown_id}/cancel",
        data={"reason": "Does not exist"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "reservation_not_found"
    assert body["status"] == 404


@pytest.mark.django_db
def test_cancel_already_cancelled_reservation_returns_409_problem_detail(client):
    customer = CustomerFactory()
    reservation = ReservationFactory(
        customer=customer,
        status=RESERVATION_STATUS_CANCELLED,
        cancel_reason="Original reason",
    )
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data={"reason": "Another reason"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "reservation_invalid_transition"
    assert body["type"] == "urn:assessment:problem:reservation_invalid_transition"
    assert body["status"] == 409

    reservation.refresh_from_db()
    assert reservation.cancel_reason == "Original reason"


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [{}, {"reason": ""}, {"reason": "   "}])
def test_cancel_without_reason_returns_422_problem_detail(client, payload):
    customer = CustomerFactory()
    reservation = ReservationFactory(
        customer=customer, status=RESERVATION_STATUS_REQUESTED
    )
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data=payload,
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "reservation_reason_required"
    assert body["type"] == "urn:assessment:problem:reservation_reason_required"
    assert body["status"] == 422

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_cancel_with_too_long_reason_returns_422_problem_detail(client):
    customer = CustomerFactory()
    reservation = ReservationFactory(
        customer=customer, status=RESERVATION_STATUS_REQUESTED
    )
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data={"reason": "x" * (RESERVATION_REASON_MAX_LENGTH + 1)},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "reservation_reason_too_long"
    assert body["status"] == 422


@pytest.mark.django_db
def test_cancel_without_token_returns_401_problem_detail(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data={"reason": "No auth"},
        content_type="application/json",
    )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "auth_required"
    assert body["type"] == "urn:assessment:problem:auth_required"
    assert body["status"] == 401


@pytest.mark.django_db
def test_cancel_with_invalid_token_returns_401_problem_detail(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = client.post(
        f"/api/v1/reservations/{reservation.id}/cancel",
        data={"reason": "Bad token"},
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer not-a-valid-jwt",
    )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "auth_invalid_token"
    assert body["type"] == "urn:assessment:problem:auth_invalid_token"
    assert body["status"] == 401
