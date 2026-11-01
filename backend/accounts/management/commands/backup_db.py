"""Back up the database into the backups/ folder with a timestamp.

SQLite: copies the database file.  PostgreSQL: runs pg_dump (must be on PATH).
"""
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a timestamped database backup in the backups/ folder."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(Path(settings.BASE_DIR).parent / "backups"))

    def handle(self, *args, **opts):
        out = Path(opts["dir"])
        out.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db = settings.DATABASES["default"]
        if db["ENGINE"].endswith("sqlite3"):
            target = out / f"hrms_{stamp}.sqlite3"
            shutil.copy2(db["NAME"], target)
        else:
            target = out / f"hrms_{stamp}.dump"
            env = {**os.environ, "PGPASSWORD": db["PASSWORD"]}
            cmd = ["pg_dump", "-Fc", "-h", db["HOST"], "-p", str(db["PORT"]), "-U", db["USER"], "-f", str(target), db["NAME"]]
            try:
                subprocess.run(cmd, env=env, check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise CommandError(f"pg_dump failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Backup written to {target}"))
