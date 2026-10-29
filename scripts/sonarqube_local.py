"""Ejecuta SonarQube local o una instancia temporal para GitHub Actions."""

import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "devops-ep2"
LABEL = "devops.ep2.role=sonarqube"


def docker(*args, check=True):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=120,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def api(base, route, password=None, data=None):
    headers = {}
    if password is not None:
        credentials = base64.b64encode(f"admin:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    body = urlencode(data).encode() if data is not None else None
    req = Request(base + route, data=body, headers=headers)
    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        # No se imprimen el cuerpo enviado ni las credenciales de autenticacion.
        raise RuntimeError(f"SonarQube devolvio HTTP {error.code} en {route}") from error


def wait_ready(base, name):
    deadline = time.monotonic() + 360
    next_notice = 0
    while time.monotonic() < deadline:
        state = json.loads(docker("inspect", name).stdout)[0]["State"]
        if not state["Running"]:
            logs = docker("logs", "--tail", "50", name, check=False)
            raise RuntimeError(logs.stdout + logs.stderr)
        try:
            if api(base, "/api/system/status").get("status") == "UP":
                return
        except (URLError, OSError, RuntimeError):
            pass
        if time.monotonic() >= next_notice:
            print("Esperando que SonarQube inicie...", flush=True)
            next_notice = time.monotonic() + 30
        time.sleep(2)
    raise RuntimeError("SonarQube no inicio dentro de seis minutos")


def configure_project(base, password):
    projects = api(base, f"/api/projects/search?projects={PROJECT}", password)
    if not projects["components"]:
        api(base, "/api/projects/create", password, {
            "project": PROJECT, "name": "DevOps EP2", "visibility": "private",
        })

    gates = api(base, "/api/qualitygates/list", password)["qualitygates"]
    gate = next((gate for gate in gates if gate["name"] == "EP2 Security"), None)
    if gate is None:
        api(base, "/api/qualitygates/create", password, {"name": "EP2 Security"})
    gate = api(base, "/api/qualitygates/show?name=EP2%20Security", password)
    conditions = {condition["metric"]: condition for condition in gate["conditions"]}
    # Se evalua todo el codigo, incluso en el primer analisis del proyecto.
    for metric, op, value in [("security_rating", "GT", "1"), ("coverage", "LT", "90")]:
        if metric in conditions:
            condition = conditions[metric]
            if condition["op"] != op or condition["error"] != value:
                raise RuntimeError(f"El gate existente tiene otra condicion para {metric}")
        else:
            api(base, "/api/qualitygates/create_condition", password, {
                "gateName": "EP2 Security", "metric": metric, "op": op, "error": value,
            })
    api(base, "/api/qualitygates/select", password, {
        "projectKey": PROJECT, "gateName": "EP2 Security",
    })


def prepare_scan_context(destination):
    """Copia solo fuentes y configuracion, sin caches, bases ni credenciales."""
    for folder in ("backend/app", "estadisticas/app", "frontend", "tests"):
        shutil.copytree(
            ROOT / folder, destination / folder,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for filename in (
        "sonar-project.properties", ".coveragerc", "pytest.ini",
        "requirements-test.txt", "requirements-security.txt",
        "backend/requirements.txt", "estadisticas/requirements.txt",
        "backend/Dockerfile", "estadisticas/Dockerfile", "estadisticas/__init__.py",
        "reports/coverage.xml",
    ):
        target = destination / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / filename, target)
    destination.chmod(0o755)
    for entry in destination.rglob("*"):
        entry.chmod(0o755 if entry.is_dir() else 0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci", action="store_true", help="Eliminar la instancia al terminar")
    args = parser.parse_args()
    if docker("info", "--format", "{{.OSType}}").stdout.strip() != "linux":
        raise RuntimeError("Se necesita un motor Docker Linux disponible")
    images = json.loads((ROOT / "security/sonarqube-images.json").read_text())
    cached = all(
        docker("image", "inspect", image, check=False).returncode == 0
        for image in images.values()
    )
    minimum_gb = (4 if cached else 10) if args.ci else (10 if cached else 15)
    if shutil.disk_usage(ROOT).free < minimum_gb * 1000 ** 3:
        raise RuntimeError(f"Se necesitan al menos {minimum_gb} GB libres antes de iniciar SonarQube")
    prefix = f"ep2-sonar-{uuid4().hex[:10]}" if args.ci else "ep2-sonarqube"
    network, name = f"{prefix}-red", prefix
    state_file = ROOT / ".sonar-local/credentials.json"
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    if not (reports / "coverage.xml").is_file():
        raise RuntimeError("Ejecuta python -m pytest antes de analizar con SonarQube")
    created_network = created_container = False
    password = None
    token_name = None
    scanner_name = f"{prefix}-scanner-{uuid4().hex[:8]}"
    base = None
    result_code = 1
    try:
        existing = docker("inspect", name, check=False)
        if existing.returncode == 0:
            details = json.loads(existing.stdout)[0]
            if details["Config"].get("Labels", {}).get("devops.ep2.role") != "sonarqube":
                raise RuntimeError(f"El contenedor {name} no pertenece a este script")
            if not state_file.is_file():
                raise RuntimeError("Faltan las credenciales locales; no se modifica la instancia existente")
            password = json.loads(state_file.read_text())["password"]
            if not details["State"]["Running"]:
                docker("start", name)
        else:
            network_state = docker("network", "inspect", network, check=False)
            if network_state.returncode:
                docker("network", "create", "--label", LABEL, network)
                created_network = True
            command = [
                "run", "-d", "--name", name, "--label", LABEL,
                "--network", network, "--network-alias", "sonarqube",
                "--memory", "4g", "--ulimit", "nofile=131072:131072",
                "--ulimit", "nproc=8192:8192", "-p",
                "127.0.0.1::9000" if args.ci else "127.0.0.1:9000:9000",
            ]
            if not args.ci:
                for folder in ("data", "logs", "extensions"):
                    command.extend([
                        "--mount", f"type=volume,source={prefix}-{folder},target=/opt/sonarqube/{folder}",
                    ])
            docker(*command, images["server"])
            created_container = True

        details = json.loads(docker("inspect", name).stdout)[0]
        port = details["NetworkSettings"]["Ports"]["9000/tcp"][0]["HostPort"]
        base = f"http://127.0.0.1:{port}"
        wait_ready(base, name)
        if shutil.disk_usage(ROOT).free < 3 * 1000 ** 3:
            docker("stop", "--timeout", "15", name, check=False)
            raise RuntimeError("Queda poco espacio despues del arranque; SonarQube se detuvo")
        if password is None:
            password = secrets.token_urlsafe(32) + "Aa1!"
            api(base, "/api/users/change_password", "admin", {
                "login": "admin", "previousPassword": "admin", "password": password,
            })
            if not args.ci:
                state_file.parent.mkdir(exist_ok=True)
                state_file.write_text(json.dumps({"login": "admin", "password": password}))
                state_file.chmod(0o600)
        configure_project(base, password)
        token_name = f"ep2-scan-{uuid4().hex}"
        token = api(base, "/api/user_tokens/generate", password, {
            "name": token_name, "type": "PROJECT_ANALYSIS_TOKEN", "projectKey": PROJECT,
        })["token"]
        env = os.environ.copy()
        env["SONAR_TOKEN"] = token
        print("Ejecutando el analisis y esperando el Quality Gate...", flush=True)
        with tempfile.TemporaryDirectory(prefix="ep2-sonar-scan-") as directory:
            context = Path(directory)
            prepare_scan_context(context)
            command = [
                "docker", "run", "--rm", "--name", scanner_name,
                "--memory", "2g", "--network", network,
                "--mount", f"type=bind,source={context},target=/usr/src,readonly",
                "--env", "SONAR_TOKEN", "--env", "SONAR_HOST_URL=http://sonarqube:9000",
                "--env", "SONAR_SCANNER_JAVA_OPTS=-Xmx512m",
                images["scanner"], "-Dsonar.working.directory=/tmp/sonar-work",
                "-Dsonar.scm.disabled=true", "-Dsonar.javascript.node.maxspace=512",
            ]
            scan = subprocess.run(command, env=env, cwd=ROOT, timeout=900)
        result_code = scan.returncode
        if result_code:
            status = {
                "scannerExitCode": result_code,
                "projectStatus": {"status": "ANALYSIS_FAILED"},
            }
            (reports / "sonarqube-quality-gate.json").write_text(json.dumps(status, indent=2))
            print("El analisis fallo; no se reutiliza el Quality Gate de una ejecucion anterior", flush=True)
        else:
            status = api(base, f"/api/qualitygates/project_status?projectKey={PROJECT}", password)
            status["scannerExitCode"] = 0
            (reports / "sonarqube-quality-gate.json").write_text(json.dumps(status, indent=2))
            issues = api(base, f"/api/issues/search?componentKeys={PROJECT}&ps=500", password)
            (reports / "sonarqube-issues.json").write_text(json.dumps(issues, indent=2))
            hotspots = api(base, f"/api/hotspots/search?project={PROJECT}&ps=500", password)
            (reports / "sonarqube-hotspots.json").write_text(json.dumps(hotspots, indent=2))
            print("Quality Gate:", status["projectStatus"]["status"], flush=True)
            if status["projectStatus"]["status"] != "OK":
                result_code = 1
        if not args.ci:
            print(f"Panel local: {base}/dashboard?id={PROJECT}", flush=True)
            print("Credenciales de admin: .sonar-local/credentials.json (excluido de Git)", flush=True)
    finally:
        if token_name and password and base:
            try:
                api(base, "/api/user_tokens/revoke", password, {"name": token_name})
            except (RuntimeError, URLError, OSError):
                print("ERROR: no se pudo revocar el token temporal de analisis", file=sys.stderr)
                result_code = result_code or 1
        docker("rm", "--force", scanner_name, check=False)
        if args.ci and created_container:
            docker("rm", "--force", "--volumes", name, check=False)
        if args.ci and created_network:
            docker("network", "rm", network, check=False)
    return result_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
