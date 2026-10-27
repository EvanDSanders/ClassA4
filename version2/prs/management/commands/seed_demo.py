"""Create synthetic demo staff accounts and one demo patient."""
from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from prs.models import Role, StaffProfile

DEMO_STAFF: tuple[tuple[str, str, str], ...] = (
    ("nurse1", "nurse-pass-123", Role.NURSE),
    ("doctor1", "doctor-pass-123", Role.DOCTOR),
    ("super1", "super-pass-123", Role.SUPERVISOR),
)


class Command(BaseCommand):
    """``manage.py seed_demo``."""

    help = "Create demo staff users (nurse1, doctor1, super1)."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create any missing demo staff users."""
        for username, password, role in DEMO_STAFF:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
                StaffProfile.objects.create(user=user, role=role)
                self.stdout.write(f"created {username}")
