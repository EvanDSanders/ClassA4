"""Views (UI controller layer). Staff and patient pages are separated by role checks."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import AccessValidator, PermissionDenied
from .ai import build_controller
from .forms import (ChangeRequestForm, PatientRegistrationForm, SearchForm, StaffPatientEditForm,
                    VisitNoteForm)
from .models import ChangeRequest, Patient, VisitNote
from .services import PatientService

ViewFunc = Callable[..., HttpResponse]
service = PatientService(build_controller())


def staff_required(view: ViewFunc) -> ViewFunc:
    """Decorator: require a logged-in staff user; others get a 403 page."""
    @wraps(view)
    @login_required
    def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        """Run ``view`` for staff, otherwise render 403."""
        if AccessValidator.staff_role(request.user) is None:
            return render(request, "prs/forbidden.html", status=403)
        try:
            return view(request, *args, **kwargs)
        except PermissionDenied:
            return render(request, "prs/forbidden.html", status=403)
    return wrapper


@login_required
def home(request: HttpRequest) -> HttpResponse:
    """Send each user to the right landing page for their role."""
    if AccessValidator.staff_role(request.user):
        return redirect("patient_search")
    return redirect("portal")


@staff_required
def patient_search(request: HttpRequest) -> HttpResponse:
    """Search patients by ID or name (FR-02)."""
    form = SearchForm(request.GET)
    query = form.cleaned_data["q"] if form.is_valid() else ""
    return render(request, "prs/patient_search.html", {
        "form": form, "patients": service.search(request.user, query),
        "pending_count": service.pending_requests().count()})


@staff_required
def patient_register(request: HttpRequest) -> HttpResponse:
    """Register a patient and set their initial password (FR-01, UR-02)."""
    form = PatientRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        patient = service.register_patient(request.user, d["name"], d["address"], d["birthday"],
                                           d["phone"], d["password"])
        messages.success(request, f"Registered. Patient ID (also their login): {patient.patient_id}")
        return redirect("patient_detail", patient_id=patient.patient_id)
    return render(request, "prs/patient_register.html", {"form": form})


@staff_required
def patient_detail(request: HttpRequest, patient_id: str) -> HttpResponse:
    """Show a patient's record, visit history and a note form (FR-02, UR-04)."""
    patient = get_object_or_404(Patient, patient_id=patient_id)
    AccessValidator.require(request.user, "view_notes")
    return render(request, "prs/patient_detail.html", {
        "patient": patient, "notes": patient.notes.all(), "note_form": VisitNoteForm(),
        "requests": patient.change_requests.all()})


@staff_required
def patient_edit(request: HttpRequest, patient_id: str) -> HttpResponse:
    """Staff edit of permitted fields."""
    patient = get_object_or_404(Patient, patient_id=patient_id)
    form = StaffPatientEditForm(request.POST or None, initial={
        "name": patient.name, "address": patient.address, "birthday": patient.birthday,
        "phone": patient.phone})
    if request.method == "POST" and form.is_valid():
        service.update_patient(request.user, patient, **form.cleaned_data)
        messages.success(request, "Patient updated.")
        return redirect("patient_detail", patient_id=patient_id)
    return render(request, "prs/patient_edit.html", {"form": form, "patient": patient})


@staff_required
@require_POST
def note_add(request: HttpRequest, patient_id: str) -> HttpResponse:
    """Add a visit note; AI suggestion (if any) is shown for review (UR-04, AIR-01)."""
    patient = get_object_or_404(Patient, patient_id=patient_id)
    form = VisitNoteForm(request.POST)
    if form.is_valid():
        note = service.add_note(request.user, patient, form.cleaned_data["text"])
        messages.info(request, f"Note saved. {note.ai_message}")
    else:
        messages.error(request, "Note text is required.")
    return redirect("patient_detail", patient_id=patient_id)


@staff_required
@require_POST
def note_resolve(request: HttpRequest, note_id: int) -> HttpResponse:
    """Accept or reject the AI category suggestion on a note."""
    note = get_object_or_404(VisitNote, pk=note_id)
    try:
        service.resolve_category(request.user, note, request.POST.get("decision") == "accept")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("patient_detail", patient_id=note.patient.patient_id)


@staff_required
def request_queue(request: HttpRequest) -> HttpResponse:
    """List pending patient change requests (FR-04)."""
    AccessValidator.require(request.user, "review_requests")
    return render(request, "prs/request_queue.html", {"requests": service.pending_requests()})


@staff_required
@require_POST
def request_review(request: HttpRequest, request_id: int) -> HttpResponse:
    """Approve or reject a change request."""
    change = get_object_or_404(ChangeRequest, pk=request_id)
    try:
        service.review_request(request.user, change, request.POST.get("decision") == "approve")
        messages.success(request, "Request reviewed.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("request_queue")


@staff_required
def audit_log(request: HttpRequest) -> HttpResponse:
    """Show the audit log to supervisors only (FR-07)."""
    return render(request, "prs/audit_log.html", {"entries": service.logs(request.user)[:500]})


@login_required
def portal(request: HttpRequest) -> HttpResponse:
    """Patient portal: own info, notes and change-request queue."""
    patient = getattr(request.user, "patient", None)
    if patient is None:
        return redirect("home")
    form = ChangeRequestForm(request.POST or None, initial={
        "name": patient.name, "address": patient.address, "phone": patient.phone})
    if request.method == "POST" and form.is_valid():
        service.submit_change_request(patient, **form.cleaned_data)
        messages.success(request, "Request submitted for staff review.")
        return redirect("portal")
    return render(request, "prs/portal.html", {
        "patient": patient, "notes": patient.notes.all(), "form": form,
        "requests": patient.change_requests.all()})
