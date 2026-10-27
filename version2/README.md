# PRS Version 2 (Django web GUI)

## Install and run
    cd version2
    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py seed_demo        # synthetic staff accounts
    python manage.py runserver        # http://127.0.0.1:8000/

## AI categorizer
Default: `qwen3.5:9b` on Ollama at `http://expressgameserver:11434`. Environment overrides:

    PRS_AI_URL=http://localhost:11434/api/generate PRS_AI_MODEL=llama3.2 python manage.py runserver
    PRS_AI_BACKEND=keyword python manage.py runserver   # rule-based fallback, NOT AI

If the AI is down or unsure, notes are still saved without a category.

## Accounts (synthetic)
| user | password | role |
|---|---|---|
| nurse1 | nurse-pass-123 | nurse |
| doctor1 | doctor-pass-123 | doctor |
| super1 | super-pass-123 | supervisor (also sees /logs/) |

Staff register patients at **Register**; the form asks for the patient's initial password. The patient logs in with
their generated Patient ID (shown after registration) and that password, sees their info and notes, and can submit
name/address/phone change requests. Staff approve/reject them under **Change requests**.

## Layout
`prs/models.py` (Patient, VisitNote, ChangeRequest, AuditLog, StaffProfile) · `services.py` (PatientService) ·
`access.py` (AccessValidator) · `ai.py` (AIModel, classifiers, AIController) · `views.py`/`forms.py`/`templates/` (UI).
Patient ID immutability: model `save()` guard + SQLite trigger (migration 0002) + UNIQUE constraint.
