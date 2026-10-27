"""Authentication component: role lookup and permission checks (FR-03, BR-02)."""
from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser

from .models import Role

PERMISSIONS: dict[str, frozenset[str]] = {
    Role.NURSE: frozenset({"register_patient", "view_patient", "update_patient", "add_note",
                           "view_notes", "review_requests"}),
    Role.DOCTOR: frozenset({"register_patient", "view_patient", "update_patient", "add_note",
                            "view_notes", "review_requests"}),
    Role.SUPERVISOR: frozenset({"register_patient", "view_patient", "update_patient", "add_note",
                                "view_notes", "review_requests", "view_logs"}),
}


class PermissionDenied(Exception):
    """Raised when a user lacks a required permission."""


class AccessValidator:
    """Decides what a user may do."""

    @staticmethod
    def staff_role(user: AbstractBaseUser) -> str | None:
        """Return the user's staff role, or None for patients/anonymous users."""
        profile = getattr(user, "staff_profile", None)
        return profile.role if profile else None

    @classmethod
    def can(cls, user: AbstractBaseUser, permission: str) -> bool:
        """Return True if the user holds ``permission``."""
        role = cls.staff_role(user)
        return role is not None and permission in PERMISSIONS[role]

    @classmethod
    def require(cls, user: AbstractBaseUser, permission: str) -> None:
        """Raise PermissionDenied unless the user holds ``permission``."""
        if not cls.can(user, permission):
            raise PermissionDenied(f"Permission '{permission}' denied")
