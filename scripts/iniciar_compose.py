"""Construye las imagenes locales y levanta el proyecto mediante Compose."""

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    images = {
        "USUARIOS_IMAGE": "ep2-usuarios:local",
        "ESTADISTICAS_IMAGE": "ep2-estadisticas:local",
    }
    env = os.environ.copy()
    env.update(images)
    for dockerfile, image in (
        ("backend/Dockerfile", images["USUARIOS_IMAGE"]),
        ("estadisticas/Dockerfile", images["ESTADISTICAS_IMAGE"]),
    ):
        print(f"Construyendo {image}...", flush=True)
        subprocess.run(
            ["docker", "build", "-f", dockerfile, "-t", image, "."],
            cwd=ROOT, env=env, check=True, timeout=600,
        )
    print("Iniciando los servicios y comprobando su salud...", flush=True)
    subprocess.run(
        ["docker", "compose", "up", "-d", "--no-build", "--wait", "--wait-timeout", "90"],
        cwd=ROOT, env=env, check=True, timeout=180,
    )


if __name__ == "__main__":
    main()
