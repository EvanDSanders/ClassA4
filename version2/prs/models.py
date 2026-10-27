"""Domain models and persistence for the PRS (Patient, VisitNote, ChangeRequest, ...)."""
from __future__ import annotations

import secrets
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

CATEGORIES: tuple[str, ...] = ("Respiratory", "Digestive", "Musculoskeletal", "General/Other")


class Role(models.TextChoices):
    """Staff roles (Assignment 2, elicitation item 4)."""

    NURSE = "nurse", "Nurse"
    DOCTOR = "doctor", "Doctor"
    SUPERVISOR = "supervisor", "Supervisor"


class ImmutableFieldError(Exception):
    """Raised when code tries to change a field that is permanent."""


class StaffProfile(models.Model):
    """Attaches a staff role to a Django user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="staff_profile")
    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self) -> str:
        """Return a readable label."""
        return f"{self.user.get_username()} ({self.role})"


def generate_patient_id() -> str:
    """Return a random candidate Patient ID such as ``P3F9A12C8``."""
    return "P" + secrets.token_hex(4).upper()


class Patient(models.Model):
    """A patient record. ``patient_id`` is unique, DB-enforced and immutable (FR-01)."""

    patient_id = models.CharField(max_length=12, unique=True, editable=False,
                                  default=generate_patient_id)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="patient", null=True, blank=True)
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255, blank=True)
    birthday = models.DateField()
    phone = models.CharField(max_length=30, blank=True)

    _original_patient_id: str | None = None

    @classmethod
    def from_db(cls, db: Any, field_names: Any, values: Any) -> "Patient":
        """Remember the ID loaded from the database so changes can be detected."""
        instance = super().from_db(db, field_names, values)
        instance._original_patient_id = instance.patient_id
        return instance

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save, refusing any change to an existing Patient ID."""
        if self.pk and self._original_patient_id and self.patient_id != self._original_patient_id:
            raise ImmutableFieldError("patient_id cannot be changed")
        super().save(*args, **kwargs)
        self._original_patient_id = self.patient_id

    def __str__(self) -> str:
        """Return a readable label."""
        return f"{self.patient_id} - {self.name}"


class VisitNote(models.Model):
    """A dated visit note belonging to exactly one existing patient (UR-04, BR2)."""

    class CategoryStatus(models.TextChoices):
        """Review state of the AI category suggestion."""

        NONE = "none", "No suggestion"
        PENDING = "pending", "Awaiting review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    suggested_category = models.CharField(max_length=30, blank=True)
    category = models.CharField(max_length=30, blank=True)
    category_status = models.CharField(max_length=10, choices=CategoryStatus.choices,
                                       default=CategoryStatus.NONE)
    ai_message = models.CharField(max_length=255, blank=True)

    class Meta:
        """Newest notes first."""

        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        """Return a readable label."""
        return f"Note {self.pk} for {self.patient.patient_id}"


class ChangeRequest(models.Model):
    """Patient-submitted request to change name/address/phone, held for staff review (FR-04)."""

    class Status(models.TextChoices):
        """Review state of a request."""

        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="change_requests")
    new_name = models.CharField(max_length=120)
    new_address = models.CharField(max_length=255, blank=True)
    new_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Oldest requests first so the queue is processed in order."""

        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        """Return a readable label."""
        return f"Request {self.pk} ({self.status}) for {self.patient.patient_id}"


class AuditLog(models.Model):
    """Append-only log with the previous values of changed data (FR-06)."""

    at = models.DateTimeField(default=timezone.now, editable=False)
    username = models.CharField(max_length=150)
    action = models.CharField(max_length=50)
    patient_id = models.CharField(max_length=12, blank=True)
    previous = models.JSONField(default=dict, blank=True)
    current = models.JSONField(default=dict, blank=True)

    class Meta:
        """Newest entries first."""

        ordering = ["-at", "-id"]

    def __str__(self) -> str:
        """Return a readable label."""
        return f"{self.at:%Y-%m-%d %H:%M} {self.username} {self.action}"
