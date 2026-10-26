from __future__ import annotations

from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from ninja.security import HttpBearer

from client_portal.exceptions import InvalidTokenError
from reservations.models import Customer


class ClientTokenService:
    @staticmethod
    def issue_access_token(*, customer: Customer) -> str:
        now = timezone.now()
        payload = {
            "sub": str(customer.user_id),
            "customer_id": str(customer.id),
            "email": customer.user.email,
            "type": "access",
            "iss": settings.API_JWT_ISSUER,
            "aud": settings.API_JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=8)).timestamp()),
        }
        return jwt.encode(payload, settings.API_JWT_SECRET, algorithm="HS256")

    @staticmethod
    def decode_access_token(token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                settings.API_JWT_SECRET,
                algorithms=["HS256"],
                audience=settings.API_JWT_AUDIENCE,
                issuer=settings.API_JWT_ISSUER,
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError() from exc

        if payload.get("type") != "access":
            raise InvalidTokenError()

        return payload


class ClientJWTAuth(HttpBearer):
    def authenticate(self, request, token: str) -> Customer:
        payload = ClientTokenService.decode_access_token(token)
        try:
            user = User.objects.select_related("customer_profile").get(pk=payload["sub"])
        except User.DoesNotExist as exc:
            raise InvalidTokenError() from exc

        if not user.is_active or not hasattr(user, "customer_profile"):
            raise InvalidTokenError()

        return user.customer_profile
