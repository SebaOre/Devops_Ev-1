"""Audita cada servicio por separado y el entorno de pruebas y herramientas."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    failed = False
    for name, manifest in (
        ("usuarios", "backend/requirements.txt"),
        ("estadisticas", "estadisticas/requirements.txt"),
        ("entorno", None),
    ):
        command = [
            sys.executable, "-m", "pip_audit", "--strict",
            "--progress-spinner", "off", "--format", "json",
            "--output", str(reports / f"pip-audit-{name}.json"),
        ]
        if manifest:
            command.extend(["-r", str(ROOT / manifest)])
        print(f"Auditando {name}...", flush=True)
        result = subprocess.run(command, cwd=ROOT, timeout=300)
        failed = failed or result.returncode != 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
