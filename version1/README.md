# PRS Version 1 (original AI-generated code, do not modify)

Requires Python 3.9+; no third-party packages.

    cd version1
    python3 main.py            # keyword fallback classifier (NOT an AI model)
    python3 main.py --ollama   # local LLM via Ollama (needs `ollama serve` + `ollama pull llama3.2`)

Data persists in `prs.db` (SQLite). Demo users (synthetic):

| user    | password  | role       |
|---------|-----------|------------|
| nurse1  | nurse123  | nurse      |
| doctor1 | doctor123 | doctor     |
| super1  | super123  | supervisor |

Layout: `prs/models.py` (Patient, VisitNote, User), `database.py`, `auth.py`,
`services.py` (PatientService), `ai.py` (AIModel interface, classifiers, AIController), `cli.py`.
