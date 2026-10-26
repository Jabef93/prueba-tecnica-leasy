from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from reservations.models import Customer, Reservation, Room


class Command(BaseCommand):
    help = "Create demo users, groups, rooms and reservations for the assessment."

    def handle(self, *args, **options):
        manager_group, _ = Group.objects.get_or_create(name="manager")
        operator_group, _ = Group.objects.get_or_create(name="operator")

        view_permission = Permission.objects.get(codename="view_reservation")
        change_permission = Permission.objects.get(codename="change_reservation")
        hold_permission = Permission.objects.get(codename="hold_reservation")

        manager_group.permissions.set([view_permission, change_permission, hold_permission])
        operator_group.permissions.set([view_permission, change_permission])

        self._create_user(
            username="manager",
            email="manager@example.com",
            password="demo1234",
            is_staff=True,
            group=manager_group,
        )
        self._create_user(
            username="operator",
            email="operator@example.com",
            password="demo1234",
            is_staff=True,
            group=operator_group,
        )

        alice_user = self._create_user(
            username="alice",
            email="alice@example.com",
            password="demo1234",
            is_staff=False,
        )
        bob_user = self._create_user(
            username="bob",
            email="bob@example.com",
            password="demo1234",
            is_staff=False,
        )

        alice = Customer.objects.get_or_create(
            user=alice_user,
            defaults={"display_name": "Alice Stone"},
        )[0]
        bob = Customer.objects.get_or_create(
            user=bob_user,
            defaults={"display_name": "Bob Reed"},
        )[0]

        room_a = Room.objects.get_or_create(
            name="Room A",
            defaults={"floor": 2, "capacity": 6},
        )[0]
        room_b = Room.objects.get_or_create(
            name="Room B",
            defaults={"floor": 3, "capacity": 10},
        )[0]

        now = timezone.now().replace(minute=0, second=0, microsecond=0)

        Reservation.objects.get_or_create(
            customer=alice,
            room=room_a,
            defaults={
                "starts_at": now + timedelta(days=2),
                "ends_at": now + timedelta(days=2, hours=2),
                "status": "requested",
                "internal_note": "VIP customer. Handle gently.",
            },
        )
        Reservation.objects.get_or_create(
            customer=alice,
            room=room_b,
            defaults={
                "starts_at": now + timedelta(days=4),
                "ends_at": now + timedelta(days=4, hours=1),
                "status": "confirmed",
                "internal_note": "Already confirmed by manager.",
            },
        )
        Reservation.objects.get_or_create(
            customer=bob,
            room=room_a,
            defaults={
                "starts_at": now + timedelta(days=3),
                "ends_at": now + timedelta(days=3, hours=3),
                "status": "requested",
                "internal_note": "May need projectors.",
            },
        )

        self.stdout.write(self.style.SUCCESS("Assessment demo data created."))
        self.stdout.write(
            "Staff users: manager/demo1234, operator/demo1234. "
            "Customer emails: alice@example.com and bob@example.com."
        )

    def _create_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        is_staff: bool,
        group: Group | None = None,
    ) -> User:
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": is_staff,
            },
        )
        user.email = email
        user.is_staff = is_staff
        user.is_active = True
        user.set_password(password)
        user.save()

        if group is not None:
            user.groups.add(group)

        return user
