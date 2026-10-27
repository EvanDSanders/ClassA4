"""Django forms (User Interface component)."""
from __future__ import annotations

from django import forms
from django.contrib.auth import password_validation


class DateInput(forms.DateInput):
    """HTML5 date picker widget."""

    input_type = "date"


class PatientRegistrationForm(forms.Form):
    """Staff form to register a patient, including the patient's initial password."""

    name = forms.CharField(max_length=120)
    address = forms.CharField(max_length=255, required=False)
    birthday = forms.DateField(widget=DateInput)
    phone = forms.CharField(max_length=30, required=False)
    password = forms.CharField(widget=forms.PasswordInput, label="Initial patient password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean(self) -> dict[str, object]:
        """Check the passwords match and satisfy the password policy."""
        data = super().clean()
        pw, confirm = data.get("password"), data.get("password_confirm")
        if pw and confirm and pw != confirm:
            self.add_error("password_confirm", "Passwords do not match.")
        elif pw:
            try:
                password_validation.validate_password(pw)
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        return data


class StaffPatientEditForm(forms.Form):
    """Staff edit of permitted patient fields (the Patient ID is not editable)."""

    name = forms.CharField(max_length=120)
    address = forms.CharField(max_length=255, required=False)
    birthday = forms.DateField(widget=DateInput)
    phone = forms.CharField(max_length=30, required=False)


class ChangeRequestForm(forms.Form):
    """Patient request to change name, address and phone."""

    name = forms.CharField(max_length=120)
    address = forms.CharField(max_length=255, required=False)
    phone = forms.CharField(max_length=30, required=False)


class VisitNoteForm(forms.Form):
    """Staff form for a visit note."""

    text = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))


class SearchForm(forms.Form):
    """Patient search by ID or name."""

    q = forms.CharField(required=False, label="Patient ID or name")
