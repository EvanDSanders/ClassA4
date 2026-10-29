"""runserver wrapper that refuses to start until migrate and seed_demo have been run."""
from __future__ import annotations

from typing import Any

from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as BaseCommand
from django.db import connection

from prs.models import Role, StaffProfile


def setup_problem() -> str | None:
    """Return a description of what setup is missing, or None if ready."""
    tables = set(connection.introspection.table_names())
    needed = {"auth_user", StaffProfile._meta.db_table}
    if needed - tables:
        return "Database is not migrated. Run: python manage.py migrate"
    present = set(StaffProfile.objects.values_list("role", flat=True))
    missing = [r.label for r in Role if r.value not in present]
    if missing:
        return (f"No staff account for role(s): {', '.join(missing)}. "
                "Run: python manage.py seed_demo")
    return None


class Command(BaseCommand):
    """``manage.py runserver`` with a setup check."""

    def handle(self, *args: Any, **options: Any) -> None:
        """Abort with a clear message if setup is incomplete, else start the server."""
        problem = setup_problem()
        if problem:
            raise CommandError(problem)
        super().handle(*args, **options)
