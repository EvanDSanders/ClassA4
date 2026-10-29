"""Admin registrations (read-mostly)."""
from django.contrib import admin
from django.http import HttpRequest

from .models import AuditLog, ChangeRequest, Patient, StaffProfile, VisitNote

admin.site.register([StaffProfile, VisitNote, ChangeRequest, AuditLog])


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Patient admin without deletion (Patient IDs are permanent)."""

    def has_delete_permission(self, request: HttpRequest, obj: Patient | None = None) -> bool:
        """Never allow deleting patients."""
        return False
