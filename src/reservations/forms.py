from django import forms

from reservations.constants import RESERVATION_REASON_MAX_LENGTH
from reservations.models import Reservation


class ReservationUpdateForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ("room", "starts_at", "ends_at", "internal_note")
        widgets = {
            "starts_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "internal_note": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["ends_at"].input_formats = ("%Y-%m-%dT%H:%M",)

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if starts_at and ends_at and ends_at <= starts_at:
            raise forms.ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio."
            )

        return cleaned_data


class ReservationHoldForm(forms.Form):
    hold_reason = forms.CharField(
        label="Motivo de la espera",
        max_length=RESERVATION_REASON_MAX_LENGTH,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={
            "required": "El motivo es obligatorio.",
            "max_length": (
                f"El motivo no puede superar los {RESERVATION_REASON_MAX_LENGTH} caracteres."
            ),
        },
    )
