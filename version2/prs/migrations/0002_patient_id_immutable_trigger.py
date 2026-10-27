"""Storage-level immutability of patient_id via a SQLite trigger."""
from django.db import migrations

CREATE = """
CREATE TRIGGER prs_patient_id_immutable
BEFORE UPDATE OF patient_id ON prs_patient
WHEN OLD.patient_id <> NEW.patient_id
BEGIN SELECT RAISE(ABORT, 'patient_id is immutable'); END;
"""


class Migration(migrations.Migration):
    """Add and remove the trigger."""

    dependencies = [("prs", "0001_initial")]
    operations = [migrations.RunSQL(CREATE, "DROP TRIGGER prs_patient_id_immutable;")]
