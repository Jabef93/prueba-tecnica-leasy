from __future__ import annotations

from uuid import UUID

from ninja import NinjaAPI, Router
from ninja.errors import AuthenticationError, ValidationError
from ninja.responses import Status

from client_portal.exceptions import AuthenticationRequiredError
from client_portal.schemas import (
    CancelReservationRequest,
    ClientProfileSchema,
    LoginRequest,
    ProblemDetailSchema,
    ReservationListItem,
    TokenResponse,
)
from client_portal.security import ClientJWTAuth, ClientTokenService
from client_portal.services import ClientPortalAuthService, ClientReservationQueryService
from reservations.models import Reservation
from reservations.services import ReservationLifecycleService
from shared.errors import AppError

api = NinjaAPI(title="Assessment Client API", version="1.0.0")
client_auth = ClientJWTAuth()

auth_router = Router(tags=["auth"])
reservation_router = Router(tags=["reservations"])

FAMILY_HTTP = {
    "auth": (401, "Authentication Failed"),
    "domain": (400, "Application Error"),
}

CODE_HTTP = {
    "reservation_not_found": (404, "Resource Not Found"),
    "reservation_invalid_transition": (409, "Invalid State Transition"),
    "reservation_reason_required": (422, "Validation Error"),
    "reservation_reason_too_long": (422, "Validation Error"),
}


def _to_reservation_item(reservation: Reservation) -> ReservationListItem:
    return ReservationListItem(
        id=reservation.id,
        room_name=reservation.room.name,
        status=reservation.status,
        starts_at=reservation.starts_at,
        ends_at=reservation.ends_at,
        cancel_reason=reservation.cancel_reason or None,
    )


@api.exception_handler(AppError)
def handle_app_error(request, exc: AppError):
    status, title = CODE_HTTP.get(
        exc.code, FAMILY_HTTP.get(exc.family, FAMILY_HTTP["domain"])
    )
    problem = ProblemDetailSchema.make(
        request=request,
        status=status,
        code=exc.code,
        title=title,
        detail=exc.detail,
        errors=exc.errors,
    )
    return api.create_response(request, problem.model_dump(), status=status)


@api.exception_handler(AuthenticationError)
def handle_authentication_error(request, exc: AuthenticationError):
    _ = exc
    return handle_app_error(request, AuthenticationRequiredError())


@api.exception_handler(ValidationError)
def handle_validation_error(request, exc: ValidationError):
    problem = ProblemDetailSchema.make(
        request=request,
        status=422,
        code="validation_error",
        title="Validation Error",
        detail="Invalid request payload.",
        errors=exc.errors,
    )
    return api.create_response(request, problem.model_dump(), status=422)


@auth_router.post(
    "/login",
    response={200: TokenResponse, 401: ProblemDetailSchema, 422: ProblemDetailSchema},
    auth=None,
)
def login(request, payload: LoginRequest):
    customer = ClientPortalAuthService().authenticate_client(
        email=payload.email,
        password=payload.password,
    )
    token = ClientTokenService.issue_access_token(customer=customer)
    return Status(200, TokenResponse(access_token=token))


@auth_router.get(
    "/me",
    response={200: ClientProfileSchema, 401: ProblemDetailSchema},
    auth=client_auth,
)
def me(request):
    customer = request.auth
    return ClientProfileSchema(
        id=customer.id,
        email=customer.user.email,
        display_name=customer.display_name,
    )


@reservation_router.get(
    "/",
    response={200: list[ReservationListItem], 401: ProblemDetailSchema},
    auth=client_auth,
)
def list_reservations(request):
    reservations = ClientReservationQueryService().get_customer_reservations(
        customer_id=request.auth.id
    )
    return [_to_reservation_item(reservation) for reservation in reservations]


@reservation_router.post(
    "/{reservation_id}/cancel",
    response={
        200: ReservationListItem,
        401: ProblemDetailSchema,
        404: ProblemDetailSchema,
        409: ProblemDetailSchema,
        422: ProblemDetailSchema,
    },
    auth=client_auth,
)
def cancel_reservation(
    request,
    reservation_id: UUID,
    payload: CancelReservationRequest,
):
    reservation = ReservationLifecycleService().cancel_reservation(
        reservation_id=reservation_id,
        customer_id=request.auth.id,
        reason=payload.reason,
    )
    return Status(200, _to_reservation_item(reservation))


api.add_router("/auth/", auth_router)
api.add_router("/reservations/", reservation_router)
