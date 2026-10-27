"""Patient and visit-note services."""
import uuid

from .auth import AccessValidator
from .models import CATEGORIES, Patient, VisitNote

UPDATABLE = {"name", "address", "birthday", "phone"}


class PatientService:
    def __init__(self, db):
        self.db = db

    def _new_id(self):
        while True:
            pid = "P" + uuid.uuid4().hex[:8].upper()
            if not self.db.query("SELECT 1 FROM patients WHERE patient_id=?", (pid,)):
                return pid

    def _log(self, user, action, detail):
        self.db.execute("INSERT INTO audit_log (username, action, detail) VALUES (?,?,?)",
                        (user.username, action, detail))

    def register_patient(self, user, name, address, birthday, phone=""):
        AccessValidator.require(user, "register_patient")
        if not name.strip():
            raise ValueError("Name required")
        patient = Patient(self._new_id(), name, address, birthday, phone)
        self.db.execute("INSERT INTO patients VALUES (?,?,?,?,?)",
                        (patient.patient_id, name, address, birthday, phone))
        self._log(user, "register", patient.patient_id)
        return patient

    def get_patient(self, user, patient_id):
        AccessValidator.require(user, "view_patient")
        rows = self.db.query("SELECT * FROM patients WHERE patient_id=?", (patient_id,))
        if not rows:
            return None
        r = rows[0]
        return Patient(r["patient_id"], r["name"], r["address"], r["birthday"], r["phone"])

    def search_by_name(self, user, name):
        AccessValidator.require(user, "view_patient")
        rows = self.db.query("SELECT * FROM patients WHERE name LIKE ?", (f"%{name}%",))
        return [Patient(r["patient_id"], r["name"], r["address"], r["birthday"], r["phone"])
                for r in rows]

    def update_patient(self, user, patient_id, **fields):
        AccessValidator.require(user, "update_patient")
        bad = set(fields) - UPDATABLE
        if bad:
            raise ValueError(f"Fields not updatable: {sorted(bad)}")
        if self.get_patient(user, patient_id) is None:
            raise KeyError(f"No patient {patient_id}")
        for key, value in fields.items():
            self.db.execute(f"UPDATE patients SET {key}=? WHERE patient_id=?", (value, patient_id))
        self._log(user, "update", f"{patient_id}: {sorted(fields)}")

    def add_note(self, user, patient_id, text):
        AccessValidator.require(user, "add_note")
        if self.get_patient(user, patient_id) is None:
            raise KeyError(f"No patient {patient_id}")
        note = VisitNote(patient_id, text)
        cur = self.db.execute(
            "INSERT INTO visit_notes (patient_id, text, created_at) VALUES (?,?,?)",
            (patient_id, text, note.created_at))
        note.note_id = cur.lastrowid
        self._log(user, "add_note", f"{patient_id}#{note.note_id}")
        return note

    def resolve_category(self, user, note_id, category, accepted):
        AccessValidator.require(user, "add_note")
        if accepted:
            if category not in CATEGORIES:
                raise ValueError("Invalid category")
            self.db.execute("UPDATE visit_notes SET category=?, category_status='accepted' WHERE note_id=?",
                            (category, note_id))
        else:
            self.db.execute("UPDATE visit_notes SET category_status='rejected' WHERE note_id=?", (note_id,))
        self._log(user, "category_accepted" if accepted else "category_rejected", str(note_id))

    def get_notes(self, user, patient_id):
        AccessValidator.require(user, "view_notes")
        rows = self.db.query(
            "SELECT * FROM visit_notes WHERE patient_id=? ORDER BY created_at, note_id", (patient_id,))
        return [VisitNote(r["patient_id"], r["text"], r["note_id"], r["created_at"],
                          r["category"], r["category_status"]) for r in rows]

    def get_logs(self, user):
        AccessValidator.require(user, "view_logs")
        return self.db.query("SELECT * FROM audit_log ORDER BY id")
