"""Admin registrations (read-mostly)."""
from django.contrib import admin

from .models import AuditLog, ChangeRequest, Patient, StaffProfile, VisitNote

admin.site.register([StaffProfile, Patient, VisitNote, ChangeRequest, AuditLog])
