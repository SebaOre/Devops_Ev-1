"""Comprueba Compose, persistencia, seguridad y balanceo con un proyecto temporal."""

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.request import urlopen
from uuid import uuid4

from verificar_docker import inspect, request

ROOT = Path(__file__).resolve().parent.parent


def main():
    project = f"ep2-compose-check-{uuid4().hex[:10]}"
    env = os.environ.copy()
    env.update({
        "APP_PORT": "0",
        "USUARIOS_IMAGE": "ep2-usuarios:local",
        "ESTADISTICAS_IMAGE": "ep2-estadisticas:local",
    })

    def compose(*args, check=True):
        result = subprocess.run(
            ["docker", "compose", "--project-name", project,
             "--file", str(ROOT / "compose.yaml"), *args],
            cwd=ROOT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180,
        )
        if check and result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout

    def up(*args):
        compose("up", "-d", "--no-build", "--pull", "never",
                "--wait", "--wait-timeout", "90", *args)

    def ids(service):
        return compose("ps", "-q", service).split()

    def validate_container(container_id, memory, cpus, uid):
        container = inspect(container_id)
        host = container["HostConfig"]
        assert container["State"]["Health"]["Status"] == "healthy"
        assert container["Config"]["User"] == uid
        assert host["ReadonlyRootfs"] is True
        assert "ALL" in host["CapDrop"]
        assert any(option.startswith("no-new-privileges") for option in host["SecurityOpt"])
        assert host["Memory"] == host["MemorySwap"] == memory * 1024 ** 2
        assert host["NanoCpus"] == int(cpus * 1_000_000_000)
        assert host["LogConfig"]["Config"]["max-size"] == "5m"
        return container

    report = {"project": project, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        compose("config", "--quiet")
        up()
        users_id, stats_id, gateway_id = ids("usuarios")[0], ids("estadisticas")[0], ids("gateway")[0]
        users = validate_container(users_id, 256, 0.5, "10001:10001")
        stats = validate_container(stats_id, 128, 0.5, "10001:10001")
        gateway = validate_container(gateway_id, 64, 0.25, "101:101")
        assert not users["HostConfig"].get("PortBindings")
        assert not stats["HostConfig"].get("PortBindings")
        binding = gateway["NetworkSettings"]["Ports"]["8080/tcp"][0]
        assert binding["HostIp"] == "127.0.0.1"
        base = f"http://127.0.0.1:{binding['HostPort']}"
        with urlopen(base + "/", timeout=10) as response:
            assert "Microservicio de Usuarios" in response.read().decode()
        assert request(base, "/health")[0] == 200
        assert request(base, "/users") == (200, [])
        assert request(base, "/stats")[1]["total_users"] == 0
        print("OK: inicio saludable, frontend y ambas APIs por la puerta de entrada", flush=True)
        print("OK: UID sin privilegios, raiz de solo lectura, capacidades eliminadas y limites efectivos", flush=True)

        for name, email in [("Ana", "ana@example.com"), ("Luis", "luis@example.org")]:
            assert request(base, "/users/", "POST", {"name": name, "email": email})[0] == 201
        expected = {"total_users": 2, "unique_domains": 2,
                    "users_by_domain": {"example.com": 1, "example.org": 1}}
        assert request(base, "/stats") == (200, expected)

        up("--scale", "estadisticas=3")
        replicas = ids("estadisticas")
        assert len(replicas) == 3
        assert ids("gateway") == [gateway_id]
        addresses = set()
        for replica in replicas:
            container = validate_container(replica, 128, 0.5, "10001:10001")
            addresses.add(container["NetworkSettings"]["Networks"][f"{project}_servicios"]["IPAddress"])
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            for _ in range(12):
                assert request(base, "/stats") == (200, expected)
            logs = compose("logs", "--no-log-prefix", "gateway")
            served = Counter(re.findall(r"GET /stats status=200 upstream=([0-9.]+):8001", logs))
            if addresses.issubset(served):
                break
            time.sleep(1)
        else:
            raise AssertionError("El proxy no distribuyo solicitudes entre las tres replicas")
        report["stats_replicas"] = 3
        report["upstreams_observed"] = dict(served)
        print("OK: tres replicas atienden consultas sin recrear Nginx", flush=True)

        subprocess.run(["docker", "stop", "--timeout", "5", replicas[-1]], check=True, capture_output=True)
        deadline = time.monotonic() + 25
        consecutive = transient_errors = 0
        while time.monotonic() < deadline:
            if request(base, "/stats") == (200, expected):
                consecutive += 1
                if consecutive == 6:
                    break
            else:
                transient_errors += 1
                consecutive = 0
            time.sleep(0.5)
        else:
            raise AssertionError("El proxy no recupero trafico estable con dos replicas")
        report["transient_errors_after_replica_stop"] = transient_errors
        print("OK: trafico estable con dos replicas tras actualizar DNS; errores transitorios:", transient_errors, flush=True)

        compose("down", "--timeout", "10")
        up()
        gateway = inspect(ids("gateway")[0])
        binding = gateway["NetworkSettings"]["Ports"]["8080/tcp"][0]
        base = f"http://127.0.0.1:{binding['HostPort']}"
        assert len(request(base, "/users/")[1]) == 2
        assert request(base, "/stats") == (200, expected)
        report["persisted_after_down_up"] = True
        print("OK: los dos usuarios persisten despues de down y up", flush=True)

        compose("stop", "--timeout", "5", "usuarios")
        assert request(base, "/stats")[0] == 503
        with urlopen(base + "/proxy-health", timeout=10) as response:
            assert response.status == 200
        up("usuarios")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if request(base, "/stats") == (200, expected):
                break
            time.sleep(1)
        else:
            raise AssertionError("El resumen no se recupero al reiniciar usuarios")
        report["dependency_failure_returns_503"] = True
        report["recovers_after_users_restart"] = True
        report["status"] = "passed"
        (ROOT / "reports").mkdir(exist_ok=True)
        (ROOT / "reports/compose-verificacion.json").write_text(json.dumps(report, indent=2))
        print("OK: error 503 ante la caida de usuarios y recuperacion posterior", flush=True)
        print("VERIFICACION DEL PASO 6/10 COMPLETADA", flush=True)
    except Exception:
        print(compose("logs", "--no-color", "--tail", "40", check=False), flush=True)
        raise
    finally:
        compose("down", "--volumes", "--timeout", "10")


if __name__ == "__main__":
    main()
