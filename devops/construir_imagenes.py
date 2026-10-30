"""Construye y empaqueta las dos imagenes con trazabilidad del commit."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent


def run(*args, capture=False):
    result = subprocess.run(
        args, cwd=ROOT, check=True, timeout=600,
        capture_output=capture, text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout.strip() if capture else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true", help="Verificar cambios locales sin atribuirlos a un commit")
    args = parser.parse_args()
    base_commit = run("git", "rev-parse", "HEAD", capture=True)
    dirty = bool(run("git", "status", "--porcelain", capture=True))
    if args.local:
        revision, tag = "working-tree", f"local-{uuid4().hex[:12]}"
    else:
        revision = os.getenv("GITHUB_SHA", "")
        if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
            raise RuntimeError("GITHUB_SHA debe contener el commit; para probar localmente usa --local")
        if revision != base_commit or dirty:
            raise RuntimeError("El checkout no coincide con el commit o tiene cambios sin registrar")
        tag = revision
    repository = os.getenv("GITHUB_REPOSITORY", "SebaOre/Devops_Ev-1")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise RuntimeError("Nombre de repositorio invalido")
    source = f"https://github.com/{repository}"
    if shutil.disk_usage(ROOT).free < 2_000_000_000:
        raise RuntimeError("Se necesitan al menos 2 GB libres para empaquetar las imagenes")

    manifest = {
        "schema_version": 1, "revision": revision, "tag": tag, "source": source,
        "base_commit": base_commit, "working_tree_dirty": dirty,
        "build_mode": "local-verification" if args.local else "github-actions",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_run": {
            "id": os.getenv("GITHUB_RUN_ID"), "attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
            "event": os.getenv("GITHUB_EVENT_NAME"),
        },
        "images": {},
    }
    for service, dockerfile in (
        ("usuarios", "backend/Dockerfile"),
        ("estadisticas", "estadisticas/Dockerfile"),
    ):
        reference = f"ep2-{service}:{tag}"
        print(f"Construyendo {reference}...", flush=True)
        run("docker", "build", "--build-arg", f"VCS_REF={revision}",
            "--build-arg", f"SOURCE_URL={source}", "-f", dockerfile, "-t", reference, ".")
        image = json.loads(run("docker", "image", "inspect", reference, capture=True))[0]
        labels = image["Config"].get("Labels") or {}
        if labels.get("org.opencontainers.image.revision") != revision:
            raise RuntimeError("La imagen no contiene la revision esperada")
        manifest["images"][service] = {"reference": reference, "image_id": image["Id"]}

    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    raw = output / "images.tar.partial"
    compressed = output / "images.tar.gz.partial"
    archive = output / "images.tar.gz"
    try:
        run("docker", "image", "save", "--output", str(raw),
            *(image["reference"] for image in manifest["images"].values()))
        with raw.open("rb") as incoming, compressed.open("wb") as target:
            with gzip.GzipFile(filename="images.tar", mode="wb", fileobj=target, mtime=0) as outgoing:
                shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
        compressed.replace(archive)
    finally:
        raw.unlink(missing_ok=True)
        compressed.unlink(missing_ok=True)
    with archive.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest["archive"] = {"file": archive.name, "sha256": checksum, "bytes": archive.stat().st_size}
    (output / "images-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"## Imagenes construidas\n\nCommit: `{revision}`\n\n")
            for image in manifest["images"].values():
                summary.write(f"- `{image['reference']}`: `{image['image_id']}`\n")
            summary.write(f"\nSHA-256 del archivo: `{checksum}`\n")
    print(f"Imagenes empaquetadas: {archive.name}, {archive.stat().st_size} bytes", flush=True)


if __name__ == "__main__":
    main()
