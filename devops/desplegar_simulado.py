"""Despliega el paquete aprobado en Compose, lo verifica y retira la simulacion."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent


def ensure(condition, message):
    if not condition:
        raise RuntimeError(message)


def http(base, route, method="GET", payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(base + route, data=body, method=method,
                  headers={"Content-Type": "application/json"})
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read()
        if not raw:
            return response.status, None
        try:
            content = json.loads(raw)
        except ValueError:
            content = raw.decode("utf-8", errors="replace")
        return response.status, content


def smoke(base, recreate_users):
    checks = []
    status, page = http(base, "/")
    ensure(status == 200 and "Microservicio de Usuarios" in page, "Frontend inaccesible")
    ensure(http(base, "/health")[0] == 200, "La API de usuarios no responde")
    ensure(http(base, "/users/") == (200, []), "El volumen temporal no esta vacio")
    empty = {"total_users": 0, "unique_domains": 0, "users_by_domain": {}}
    ensure(http(base, "/stats") == (200, empty), "El resumen inicial es incorrecto")
    checks.append("frontend, salud y resumen inicial")

    ids = []
    for name, email in (("Ana CI", "ana@example.com"), ("Luis CI", "luis@example.org")):
        status, user = http(base, "/users/", "POST", {"name": name, "email": email})
        ensure(status == 201 and user.get("email") == email, "No se pudo crear un usuario")
        ids.append(user["id"])
    ensure(http(base, f"/users/{ids[0]}")[0] == 200, "No se pudo consultar el usuario")
    initial = {"total_users": 2, "unique_domains": 2,
               "users_by_domain": {"example.com": 1, "example.org": 1}}
    ensure(http(base, "/stats") == (200, initial), "Fallo la comunicacion entre servicios")
    checks.append("creacion, consulta y comunicacion HTTP entre microservicios")

    status, user = http(base, f"/users/{ids[1]}", "PUT", {"email": "luis@example.com"})
    ensure(status == 200 and user.get("email") == "luis@example.com", "Fallo la actualizacion")
    updated = {"total_users": 2, "unique_domains": 1, "users_by_domain": {"example.com": 2}}
    ensure(http(base, "/stats") == (200, updated), "El resumen no refleja la actualizacion")
    checks.append("actualizacion reflejada en estadisticas")

    recreate_users()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            if http(base, "/stats") == (200, updated):
                break
        except (URLError, OSError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Los servicios no se recuperaron tras recrear usuarios")
    status, users = http(base, "/users/")
    ensure(status == 200 and {u["id"] for u in users} == set(ids), "Los registros no persistieron")
    checks.append("persistencia y recuperacion al recrear usuarios")

    for user_id in ids:
        ensure(http(base, f"/users/{user_id}", "DELETE")[0] == 204, "Fallo la eliminacion")
    ensure(http(base, "/stats") == (200, empty), "El resumen final no esta vacio")
    checks.append("eliminacion y resumen final")
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=os.getenv("GITHUB_SHA"), required=False)
    parser.add_argument("--simulate-failure", action="store_true",
                        help="Ensayo local de fallo posterior al arranque, con limpieza obligatoria")
    args = parser.parse_args()
    ensure(args.revision, "Indica --revision o configura GITHUB_SHA")
    ensure(not args.simulate_failure or os.getenv("GITHUB_ACTIONS") != "true",
           "El ensayo intencional de fallo solo se permite localmente")
    ensure(args.revision != "working-tree" or os.getenv("GITHUB_ACTIONS") != "true",
           "GitHub Actions debe desplegar una revision de commit")
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    suffix = "-fallo" if args.simulate_failure else ""
    prefix = f"despliegue-simulado{suffix}"
    project = f"ep2-deploy-{uuid4().hex[:12]}"
    report = {"project": project, "revision": args.revision, "status": "failed",
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "simulation": True, "intentional_failure": args.simulate_failure,
              "workflow_run_id": os.getenv("GITHUB_RUN_ID"),
              "workflow_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"), "stage": "artifact"}
    env = os.environ.copy()
    started = False
    success = False

    def run(*command, check=True, timeout=180):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        if check and result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result

    def compose(*command, **options):
        return run("docker", "compose", "--project-name", project,
                   "--file", str(ROOT / "compose.yaml"), *command, **options)

    def up(*options):
        compose("up", "-d", "--no-build", "--pull", "never", "--wait",
                "--wait-timeout", "90", *options)

    def containers():
        result = {}
        for service in ("usuarios", "estadisticas", "gateway"):
            ids = compose("ps", "-q", service).stdout.split()
            ensure(len(ids) == 1, f"Se esperaba un contenedor de {service}")
            result[service] = json.loads(run("docker", "inspect", ids[0]).stdout)[0]
        return result

    try:
        manifest = json.loads((ROOT / "artifacts/images-manifest.json").read_text(encoding="utf-8"))
        repository = os.getenv("GITHUB_REPOSITORY", "SebaOre/Devops_Ev-1")
        ensure(manifest.get("source") == f"https://github.com/{repository}", "Repositorio del paquete incorrecto")
        if os.getenv("GITHUB_ACTIONS") == "true":
            ensure(args.revision == os.getenv("GITHUB_SHA"), "La revision no coincide con GitHub Actions")
            ensure(run("git", "rev-parse", "HEAD").stdout.strip() == args.revision,
                   "El checkout de Compose no corresponde a las imagenes")
            ensure(not run("git", "status", "--porcelain").stdout.strip(), "El checkout contiene cambios")
            ensure(manifest.get("workflow_run", {}).get("id") == os.getenv("GITHUB_RUN_ID"),
                   "El paquete proviene de otra ejecucion")
            ensure(manifest.get("workflow_run", {}).get("attempt") == os.getenv("GITHUB_RUN_ATTEMPT"),
                   "El paquete proviene de otro intento")
        print("Verificando el paquete y cargando las imagenes aprobadas...", flush=True)
        verified = run(sys.executable, str(ROOT / "devops/verificar_artefactos.py"),
                       "--load", "--revision", args.revision, timeout=240)
        print(verified.stdout, end="", flush=True)
        report["artifact"] = manifest
        env.update(APP_PORT="0", USUARIOS_IMAGE=manifest["images"]["usuarios"]["reference"],
                   ESTADISTICAS_IMAGE=manifest["images"]["estadisticas"]["reference"])
        config = json.loads(compose("config", "--format", "json").stdout)
        for service, image in manifest["images"].items():
            ensure(config["services"][service]["image"] == image["reference"], "Compose cambio la imagen aprobada")
        gateway_image = config["services"]["gateway"]["image"]
        ensure(re.fullmatch(r"nginx:[a-zA-Z0-9._-]+@sha256:[0-9a-f]{64}", gateway_image),
               "La imagen del proxy debe estar fijada por digest")
        print("Preparando el proxy fijado por digest...", flush=True)
        run("docker", "pull", gateway_image)
        report["gateway_image"] = gateway_image
        report["stage"] = "startup"
        started = True
        print("Levantando Compose sin reconstruir las imagenes...", flush=True)
        up()
        current = containers()
        for service, container in current.items():
            ensure(container["State"].get("Health", {}).get("Status") == "healthy",
                   f"{service} no esta saludable")
            if service in manifest["images"]:
                ensure(container["Image"] == manifest["images"][service]["image_id"],
                       f"{service} no ejecuta la imagen del manifiesto")
                ensure(container["Config"]["Image"] == manifest["images"][service]["reference"],
                       f"{service} no usa la referencia aprobada")
                labels = container["Config"].get("Labels") or {}
                ensure(labels.get("org.opencontainers.image.revision") == args.revision,
                       f"{service} no corresponde al commit")
                ensure(labels.get("org.opencontainers.image.source") == manifest["source"],
                       f"{service} no corresponde al repositorio")
        report["containers"] = {service: {"id": c["Id"], "runtime_image_id": c["Image"],
                                          "image_reference": c["Config"]["Image"],
                                          "health": c["State"]["Health"]["Status"]}
                                for service, c in current.items()}
        binding = current["gateway"]["NetworkSettings"]["Ports"]["8080/tcp"][0]
        ensure(binding["HostIp"] == "127.0.0.1", "El puerto temporal debe ser local")
        base = f"http://127.0.0.1:{binding['HostPort']}"
        report["temporary_url"] = base
        print("OK: tres servicios saludables en el proyecto temporal", flush=True)
        if args.simulate_failure:
            raise RuntimeError("Fallo intencional para verificar diagnostico y limpieza")
        report["stage"] = "smoke"
        print("Probando APIs y persistencia al recrear usuarios...", flush=True)
        report["checks"] = smoke(base, lambda: up("--force-recreate", "--no-deps", "usuarios"))
        final = containers()
        ensure(current["usuarios"]["Id"] != final["usuarios"]["Id"], "Usuarios no fue recreado")
        report["recreated_users_container_id"] = final["usuarios"]["Id"]
        report["recreated_users_runtime_image_id"] = final["usuarios"]["Image"]
        for service, container in final.items():
            ensure(container["State"]["Health"]["Status"] == "healthy", f"Salud final incorrecta: {service}")
            if service in manifest["images"]:
                ensure(container["Image"] == manifest["images"][service]["image_id"],
                       f"La recreacion cambio la imagen de {service}")
        success = True
        print("OK: CRUD, comunicacion entre servicios y persistencia verificados", flush=True)
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        report["error"] = str(error)
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
    finally:
        if started:
            for command, extension in ((("logs", "--no-color", "--timestamps", "--tail", "100"), "log"),
                                       (("ps", "--all", "--format", "json"), "containers.json")):
                try:
                    result = compose(*command, check=False)
                    (reports / f"{prefix}.{extension}").write_text(result.stdout + result.stderr, encoding="utf-8")
                except (OSError, subprocess.TimeoutExpired) as error:
                    report.setdefault("diagnostic_errors", []).append(str(error))
            try:
                print("Retirando los recursos del proyecto temporal...", flush=True)
                compose("down", "--volumes", "--timeout", "10")
                remaining = {}
                for resource, options in (("container", ("ps", "-aq")),
                                          ("volume", ("volume", "ls", "-q")),
                                          ("network", ("network", "ls", "-q"))):
                    remaining[resource] = run("docker", *options, "--filter",
                                              f"label=com.docker.compose.project={project}").stdout.split()
                report["cleanup"] = {"completed": not any(remaining.values()), "remaining": remaining}
                ensure(report["cleanup"]["completed"], "Quedaron recursos del proyecto temporal")
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                success = False
                report["cleanup"] = {"completed": False, "error": str(error)}
                print(f"ERROR de limpieza: {error}", file=sys.stderr, flush=True)
        else:
            report["cleanup"] = {"completed": True, "resources_created": False}
        report["status"] = "passed" if success else "failed"
        if success:
            report["stage"] = "completed"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        (reports / f"{prefix}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write(f"## Despliegue simulado: {report['status']}\n\n")
                summary.write(f"Revision: `{args.revision}`\n\nProyecto temporal: `{project}`\n\n")
                for check in report.get("checks", []):
                    summary.write(f"- OK: {check}\n")
                summary.write(f"\nRecursos temporales retirados: {report['cleanup']['completed']}\n\n")
                summary.write("Los reportes y logs quedan en el artefacto de despliegue; el entorno del runner es temporal.\n")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
