"""Domain models for the PRS (Version 1)."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

CATEGORIES = ("Respiratory", "Digestive", "Musculoskeletal", "General/Other")


class Role(Enum):
    NURSE = "nurse"
    DOCTOR = "doctor"
    SUPERVISOR = "supervisor"


@dataclass
class User:
    username: str
    role: Role


class Patient:
    def __init__(self, patient_id, name, address, birthday, phone=""):
        self._patient_id = patient_id
        self.name = name
        self.address = address
        self.birthday = birthday
        self.phone = phone

    @property
    def patient_id(self):
        return self._patient_id

    def __repr__(self):
        return f"Patient({self._patient_id}, {self.name})"


@dataclass
class VisitNote:
    patient_id: str
    text: str
    note_id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    category: Optional[str] = None
    category_status: str = "none"  # none | accepted | rejected
