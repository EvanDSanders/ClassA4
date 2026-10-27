# PRS Version 1 (original AI-generated code, do not modify)

Requires Python 3.9+; no third-party packages.

    cd version1
    python3 main.py                  # default: qwen3.5:9b on expressgameserver (Ollama)
    python3 main.py --local llama3.2 # local Ollama model on localhost
    python3 main.py --keyword        # keyword fallback (test substitute, NOT an AI model)

If the AI server is unreachable, notes still save without a category.

Data persists in `prs.db` (SQLite). Demo users (synthetic):

| user    | password  | role       |
|---------|-----------|------------|
| nurse1  | nurse123  | nurse      |
| doctor1 | doctor123 | doctor     |
| super1  | super123  | supervisor |

Layout: `prs/models.py` (Patient, VisitNote, User), `database.py`, `auth.py`,
`services.py` (PatientService), `ai.py` (AIModel interface, classifiers, AIController), `cli.py`.
