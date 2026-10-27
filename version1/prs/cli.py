"""Command-line user interface."""
import getpass

from .ai import AIController, OllamaClassifier
from .auth import AuthenticationService, PermissionDenied
from .database import Database
from .services import PatientService


class CLI:
    def __init__(self, db_path="prs.db", model=None):
        self.db = Database(db_path)
        self.auth = AuthenticationService(self.db)
        self.auth.seed_demo_users()
        self.patients = PatientService(self.db)
        self.ai = AIController(model or OllamaClassifier())
        self.user = None

    def run(self):
        self.login()
        actions = {"1": self.register, "2": self.view, "3": self.search, "4": self.update,
                   "5": self.add_note, "6": self.history, "7": self.logs}
        while self.user:
            print("\n1 Register  2 View by ID  3 Search name  4 Update  5 Add note  "
                  "6 Visit history  7 Logs  0 Quit")
            choice = input("> ").strip()
            if choice == "0":
                break
            action = actions.get(choice)
            if not action:
                continue
            try:
                action()
            except (PermissionDenied, ValueError, KeyError) as exc:
                print("Error:", exc)
        self.db.close()

    def login(self):
        while not self.user:
            name = input("Username: ")
            self.user = self.auth.login(name, getpass.getpass("Password: "))
            if not self.user:
                print("Invalid credentials")
        print(f"Logged in as {self.user.username} ({self.user.role.value})")

    def register(self):
        p = self.patients.register_patient(
            self.user, input("Name: "), input("Address: "), input("Birthday (YYYY-MM-DD): "),
            input("Phone: "))
        print("Registered with ID", p.patient_id)

    def view(self):
        p = self.patients.get_patient(self.user, input("Patient ID: ").strip())
        print(vars(p) if p else "Not found")

    def search(self):
        for p in self.patients.search_by_name(self.user, input("Name: ")):
            print(p.patient_id, p.name)

    def update(self):
        pid = input("Patient ID: ").strip()
        field = input("Field (name/address/birthday/phone): ").strip()
        self.patients.update_patient(self.user, pid, **{field: input("New value: ")})
        print("Updated")

    def add_note(self):
        pid = input("Patient ID: ").strip()
        patient = self.patients.get_patient(self.user, pid)
        if patient is None:
            raise KeyError(f"No patient {pid}")
        note = self.patients.add_note(self.user, pid, input("Note text: "))
        print(f"Note {note.note_id} saved.")
        suggestion, message = self.ai.suggest(note.text, f"{patient.name}, born {patient.birthday}")
        print(message)
        if suggestion:
            ans = input(f"Accept category '{suggestion.category}'? (y/n): ").lower()
            self.patients.resolve_category(self.user, note.note_id, suggestion.category, ans == "y")

    def history(self):
        for n in self.patients.get_notes(self.user, input("Patient ID: ").strip()):
            print(f"[{n.created_at}] #{n.note_id} ({n.category or 'uncategorized'}, "
                  f"{n.category_status}) {n.text}")

    def logs(self):
        for r in self.patients.get_logs(self.user):
            print(r["at"], r["username"], r["action"], r["detail"])
