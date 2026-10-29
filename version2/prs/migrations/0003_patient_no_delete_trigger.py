"""Storage-level ban on deleting patients, so a Patient ID can never be reused."""
from django.db import migrations

CREATE = """
CREATE TRIGGER prs_patient_no_delete
BEFORE DELETE ON prs_patient
BEGIN SELECT RAISE(ABORT, 'patients cannot be deleted'); END;
"""


class Migration(migrations.Migration):
    """Add and remove the trigger."""

    dependencies = [("prs", "0002_patient_id_immutable_trigger")]
    operations = [migrations.RunSQL(CREATE, "DROP TRIGGER prs_patient_no_delete;")]
