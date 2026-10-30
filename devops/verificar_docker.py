"""Verifica las dos imagenes locales usando recursos Docker temporales."""

import json
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def docker(*args):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=60
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def inspect(name):
    return json.loads(docker("inspect", name))[0]


def endpoint(name, port):
    binding = inspect(name)["NetworkSettings"]["Ports"][f"{port}/tcp"][0]
    return f"http://127.0.0.1:{binding['HostPort']}"


def request(base, route, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        base + route, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        body = error.read()
        try:
            details = json.loads(body)
        except ValueError:
            details = {"detail": body.decode("utf-8", errors="replace")}
        return error.code, details


def wait_healthy(name, base):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        state = inspect(name)["State"]
        if not state["Running"]:
            raise RuntimeError(docker("logs", name))
        try:
            if state.get("Health", {}).get("Status") == "healthy":
                if request(base, "/health")[0] == 200:
                    return
        except (URLError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"El contenedor {name} no alcanzo el estado healthy")


def main():
    prefix = f"ep2-check-{uuid4().hex[:12]}"
    network, volume = f"{prefix}-red", f"{prefix}-datos"
    users, stats = f"{prefix}-usuarios", f"{prefix}-estadisticas"
    containers = []
    network_created = volume_created = False

    def start_users():
        docker(
            "run", "-d", "--name", users, "--network", network,
            "--network-alias", "usuarios", "--health-interval", "2s",
            "--mount", f"type=volume,source={volume},target=/data",
            "-p", "127.0.0.1::8000", "ep2-usuarios:local",
        )
        containers.append(users)
        base = endpoint(users, 8000)
        wait_healthy(users, base)
        return base

    try:
        docker("network", "create", network)
        network_created = True
        docker("volume", "create", volume)
        volume_created = True
        users_base = start_users()
        docker(
            "run", "-d", "--name", stats, "--network", network,
            "--health-interval", "2s", "-p", "127.0.0.1::8001",
            "ep2-estadisticas:local",
        )
        containers.append(stats)
        stats_base = endpoint(stats, 8001)
        wait_healthy(stats, stats_base)
        print("OK: ambos HEALTHCHECK alcanzan el estado healthy", flush=True)

        for name in (users, stats):
            assert inspect(name)["Config"]["User"] == "10001:10001"
            assert docker("exec", name, "id", "-u") == "10001"
            docker("exec", name, "python", "-m", "pip", "check")
        print("OK: ambos procesos usan UID 10001 y sus dependencias son compatibles", flush=True)

        with urlopen(users_base + "/", timeout=10) as response:
            assert "Microservicio de Usuarios" in response.read().decode()
        docker(
            "exec", users, "python", "-c",
            "from pathlib import Path; "
            "assert not Path('/app/backend/.env').exists(); "
            "assert not Path('/app/backend/microservicio.db').exists(); "
            "assert Path('/data/microservicio.db').exists()",
        )
        assert request(stats_base, "/stats")[1]["total_users"] == 0
        print("OK: frontend disponible y base de datos nueva en /data", flush=True)

        for name, email in [("Ana", "ana@example.com"), ("Luis", "luis@example.org")]:
            assert request(users_base, "/users/", "POST", {"name": name, "email": email})[0] == 201
        expected = {
            "total_users": 2, "unique_domains": 2,
            "users_by_domain": {"example.com": 1, "example.org": 1},
        }
        assert request(stats_base, "/stats") == (200, expected)
        print("OK: estadisticas consulta usuarios por DNS interno:", json.dumps(expected), flush=True)

        docker("rm", "--force", users)
        containers.remove(users)
        users_base = start_users()
        assert len(request(users_base, "/users/")[1]) == 2
        assert request(stats_base, "/stats") == (200, expected)
        print("OK: los registros persisten al recrear el contenedor de usuarios", flush=True)

        docker("stop", users)
        assert request(stats_base, "/stats")[0] == 503
        assert request(stats_base, "/health")[0] == 200
        print("OK: HTTP 503 al detener usuarios; estadisticas mantiene su salud", flush=True)
        print("VERIFICACION DEL PASO 3/10 COMPLETADA", flush=True)
    except Exception:
        for name in containers:
            print(docker("logs", name), flush=True)
        raise
    finally:
        for name in reversed(containers):
            docker("rm", "--force", name)
        if volume_created:
            docker("volume", "rm", volume)
        if network_created:
            docker("network", "rm", network)


if __name__ == "__main__":
    main()
