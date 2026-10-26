from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from reservations.constants import (
    PERMISSION_HOLD_RESERVATION,
    RESERVATION_HOLDABLE_STATUSES,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.exceptions import ReservationNotFoundError
from reservations.forms import ReservationHoldForm, ReservationUpdateForm
from reservations.models import Reservation
from reservations.services import ReservationLifecycleService, ReservationUpdateService
from shared.errors import DomainError
from shared.mixins import AuthenticatedPermissionRequiredMixin

# Backoffice-facing (Spanish) messages for domain error codes. Unknown codes fall
# back to the error's own detail so new errors never surface as a 500.
DOMAIN_ERROR_MESSAGES = {
    "reservation_invalid_transition": (
        "La reserva no puede cambiar a ese estado desde su estado actual."
    ),
    "reservation_reason_required": "El motivo es obligatorio.",
    "reservation_reason_too_long": "El motivo es demasiado largo.",
}


def _domain_error_message(exc: DomainError) -> str:
    return DOMAIN_ERROR_MESSAGES.get(exc.code, exc.detail)


def _detail_context(
    request: HttpRequest,
    reservation: Reservation,
    hold_form: ReservationHoldForm | None = None,
) -> dict:
    can_change = request.user.has_perm("reservations.change_reservation")
    return {
        "reservation": reservation,
        "can_change": can_change,
        "can_confirm": can_change
        and reservation.status == RESERVATION_STATUS_REQUESTED,
        "can_hold": request.user.has_perm(PERMISSION_HOLD_RESERVATION)
        and reservation.status in RESERVATION_HOLDABLE_STATUSES,
        "hold_form": hold_form or ReservationHoldForm(),
    }


class ReservationListView(LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View):
    permission_required = "reservations.view_reservation"

    def get(self, request: HttpRequest) -> HttpResponse:
        reservations = Reservation.objects.select_related("customer__user", "room")
        return render(
            request,
            "reservations/list.html",
            {"reservations": reservations},
        )


class ReservationDetailView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.view_reservation"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(
            Reservation.objects.select_related("customer__user", "room"),
            pk=pk,
        )
        return render(
            request,
            "reservations/detail.html",
            _detail_context(request, reservation),
        )


class ReservationUpdateView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.change_reservation"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=pk)
        form = ReservationUpdateForm(instance=reservation)
        return render(
            request,
            "reservations/edit.html",
            {"reservation": reservation, "form": form},
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=pk)
        form = ReservationUpdateForm(request.POST, instance=reservation)
        if not form.is_valid():
            return render(
                request,
                "reservations/edit.html",
                {"reservation": reservation, "form": form},
                status=422,
            )

        ReservationUpdateService().update_reservation(
            reservation_id=reservation.id,
            room_id=form.cleaned_data["room"].id,
            starts_at=form.cleaned_data["starts_at"],
            ends_at=form.cleaned_data["ends_at"],
            internal_note=form.cleaned_data["internal_note"],
        )
        messages.success(request, "Reserva actualizada.")
        return redirect("reservation_detail", pk=reservation.id)


class ReservationConfirmView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.change_reservation"

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        try:
            ReservationLifecycleService().confirm_reservation(
                reservation_id=pk,
                actor_id=request.user.id,
            )
        except ReservationNotFoundError as exc:
            raise Http404 from exc
        except DomainError as exc:
            messages.error(request, _domain_error_message(exc))
            return redirect("reservation_detail", pk=pk)

        messages.success(request, "Reserva confirmada.")
        return redirect("reservation_detail", pk=pk)


class ReservationHoldView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = PERMISSION_HOLD_RESERVATION

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        form = ReservationHoldForm(request.POST)
        if not form.is_valid():
            reservation = get_object_or_404(
                Reservation.objects.select_related("customer__user", "room"),
                pk=pk,
            )
            return render(
                request,
                "reservations/detail.html",
                _detail_context(request, reservation, hold_form=form),
                status=422,
            )

        try:
            ReservationLifecycleService().hold_reservation(
                reservation_id=pk,
                reason=form.cleaned_data["hold_reason"],
                actor=request.user,
            )
        except ReservationNotFoundError as exc:
            raise Http404 from exc
        except DomainError as exc:
            messages.error(request, _domain_error_message(exc))
            return redirect("reservation_detail", pk=pk)

        messages.success(request, "Reserva puesta en espera.")
        return redirect("reservation_detail", pk=pk)
