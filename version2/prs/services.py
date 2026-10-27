"""Patient component: PatientService holds all business rules and writes the audit log."""
from __future__ import annotations

from datetime import date
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, User
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from .access import AccessValidator
from .ai import AIController
from .models import (CATEGORIES, AuditLog, ChangeRequest, Patient, VisitNote, generate_patient_id)

STAFF_UPDATABLE: frozenset[str] = frozenset({"name", "address", "birthday", "phone"})
PATIENT_REQUESTABLE: tuple[str, ...] = ("name", "address", "phone")


class PatientService:
    """Application service for patients, notes and change requests."""

    def __init__(self, ai: AIController) -> None:
        """Use ``ai`` for note categorization."""
        self.ai = ai

    @staticmethod
    def _log(username: str, action: str, patient_id: str = "",
             previous: dict[str, Any] | None = None, current: dict[str, Any] | None = None) -> None:
        """Append an audit entry (FR-06)."""
        AuditLog.objects.create(username=username, action=action, patient_id=patient_id,
                                previous=previous or {}, current=current or {})

    @staticmethod
    def _snapshot(patient: Patient, fields: Any) -> dict[str, str]:
        """Return string values of ``fields`` on ``patient``."""
        return {f: str(getattr(patient, f)) for f in fields}

    @transaction.atomic
    def register_patient(self, staff: AbstractBaseUser, name: str, address: str, birthday: date,
                         phone: str, password: str) -> Patient:
        """Create a patient and their login account (username = Patient ID) (FR-01, UR-02)."""
        AccessValidator.require(staff, "register_patient")
        for _ in range(10):
            pid = generate_patient_id()
            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=pid, password=password)
                    patient = Patient.objects.create(patient_id=pid, user=user, name=name,
                                                     address=address, birthday=birthday, phone=phone)
                break
            except IntegrityError:
                continue
        else:
            raise RuntimeError("Could not generate a unique Patient ID")
        self._log(staff.get_username(), "register", pid,
                  current=self._snapshot(patient, STAFF_UPDATABLE))
        return patient

    @staticmethod
    def search(staff: AbstractBaseUser, query: str) -> QuerySet[Patient]:
        """Find patients by exact ID or name fragment (FR-02)."""
        AccessValidator.require(staff, "view_patient")
        query = query.strip()
        if not query:
            return Patient.objects.all().order_by("name")
        return Patient.objects.filter(Q(patient_id__iexact=query) | Q(name__icontains=query)).order_by("name")

    @staticmethod
    def get_patient(staff: AbstractBaseUser, patient_id: str) -> Patient:
        """Return a patient by ID; raises Patient.DoesNotExist."""
        AccessValidator.require(staff, "view_patient")
        return Patient.objects.get(patient_id=patient_id)

    def update_patient(self, staff: AbstractBaseUser, patient: Patient, **fields: Any) -> None:
        """Staff update of permitted fields; logs previous values (FR-06)."""
        AccessValidator.require(staff, "update_patient")
        bad = set(fields) - STAFF_UPDATABLE
        if bad:
            raise ValueError(f"Fields not updatable: {sorted(bad)}")
        previous = self._snapshot(patient, fields)
        for key, value in fields.items():
            setattr(patient, key, value)
        patient.save()
        self._log(staff.get_username(), "update", patient.patient_id, previous,
                  self._snapshot(patient, fields))

    def add_note(self, staff: AbstractBaseUser, patient: Patient, text: str) -> VisitNote:
        """Save a note first, then try AI categorization; AI failure never blocks saving (AIR-02)."""
        AccessValidator.require(staff, "add_note")
        note = VisitNote.objects.create(patient=patient, author=staff, text=text)
        context = f"Born {patient.birthday}"
        suggestion, message = self.ai.suggest(text, context)
        note.ai_message = message
        if suggestion:
            note.suggested_category = suggestion.category
            note.category_status = VisitNote.CategoryStatus.PENDING
        note.save()
        self._log(staff.get_username(), "add_note", patient.patient_id, current={"note": str(note.pk)})
        return note

    def resolve_category(self, staff: AbstractBaseUser, note: VisitNote, accepted: bool) -> None:
        """Accept or reject a pending AI suggestion (AIR-01)."""
        AccessValidator.require(staff, "add_note")
        if note.category_status != VisitNote.CategoryStatus.PENDING:
            raise ValueError("No pending suggestion on this note")
        if accepted and note.suggested_category not in CATEGORIES:
            raise ValueError("Invalid category")
        note.category = note.suggested_category if accepted else ""
        note.category_status = (VisitNote.CategoryStatus.ACCEPTED if accepted
                                else VisitNote.CategoryStatus.REJECTED)
        note.save()
        self._log(staff.get_username(), "category_accepted" if accepted else "category_rejected",
                  note.patient.patient_id, current={"note": str(note.pk), "category": note.category})

    @staticmethod
    def submit_change_request(patient: Patient, name: str, address: str, phone: str) -> ChangeRequest:
        """Queue a patient's change request for staff review."""
        request = ChangeRequest.objects.create(patient=patient, new_name=name, new_address=address,
                                               new_phone=phone)
        PatientService._log(patient.patient_id, "change_requested", patient.patient_id,
                            current={"request": str(request.pk)})
        return request

    @transaction.atomic
    def review_request(self, staff: AbstractBaseUser, request: ChangeRequest, approve: bool) -> None:
        """Approve (apply) or reject a pending change request (FR-04)."""
        AccessValidator.require(staff, "review_requests")
        if request.status != ChangeRequest.Status.PENDING:
            raise ValueError("Request already reviewed")
        patient = request.patient
        if approve:
            self.update_patient(staff, patient, name=request.new_name, address=request.new_address,
                                phone=request.new_phone)
        request.status = ChangeRequest.Status.APPROVED if approve else ChangeRequest.Status.REJECTED
        request.reviewed_by = staff  # type: ignore[assignment]
        request.reviewed_at = timezone.now()
        request.save()
        self._log(staff.get_username(), "request_approved" if approve else "request_rejected",
                  patient.patient_id, current={"request": str(request.pk)})

    @staticmethod
    def pending_requests() -> QuerySet[ChangeRequest]:
        """Return all requests awaiting review."""
        return ChangeRequest.objects.filter(status=ChangeRequest.Status.PENDING).select_related("patient")

    @staticmethod
    def logs(staff: AbstractBaseUser) -> QuerySet[AuditLog]:
        """Return the audit log (supervisors only, FR-07)."""
        AccessValidator.require(staff, "view_logs")
        return AuditLog.objects.all()
