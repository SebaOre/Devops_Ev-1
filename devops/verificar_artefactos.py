"""Comprueba integridad, revision e identidad de las imagenes del pipeline."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def validate_manifest(manifest, expected_revision=None):
    if manifest.get("schema_version") != 1:
        raise ValueError("Version de manifiesto no soportada")
    if expected_revision and manifest.get("revision") != expected_revision:
        raise ValueError("El manifiesto corresponde a otro commit")
    revision = manifest.get("revision", "")
    if revision == "working-tree":
        if not re.fullmatch(r"local-[0-9a-f]{12}", manifest.get("tag", "")):
            raise ValueError("Etiqueta de verificacion local invalida")
    elif not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        raise ValueError("Revision invalida")
    elif manifest.get("tag") != revision or manifest.get("working_tree_dirty") is not False:
        raise ValueError("La imagen de un commit debe proceder de un checkout limpio")
    if manifest.get("archive", {}).get("file") != "images.tar.gz":
        raise ValueError("Nombre de archivo inesperado")
    if not re.fullmatch(r"[0-9a-f]{64}", manifest["archive"].get("sha256", "")):
        raise ValueError("Checksum invalido")
    if set(manifest.get("images", {})) != {"usuarios", "estadisticas"}:
        raise ValueError("El paquete debe contener los dos microservicios")
    for service, image in manifest["images"].items():
        if image.get("reference") != f"ep2-{service}:{manifest.get('tag')}":
            raise ValueError("La referencia de imagen no coincide con el servicio")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image.get("image_id", "")):
            raise ValueError("Identificador de imagen invalido")


def verify_checksum(archive, expected):
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError("El archivo de imagenes fue modificado o esta incompleto")


def validate_image(actual, expected, manifest):
    labels = actual["Config"].get("Labels") or {}
    if actual["Id"] != expected["image_id"]:
        raise ValueError("La imagen cargada no coincide con el manifiesto")
    if labels.get("org.opencontainers.image.revision") != manifest["revision"]:
        raise ValueError("La etiqueta de revision de la imagen no coincide")
    if labels.get("org.opencontainers.image.source") != manifest["source"]:
        raise ValueError("La imagen no corresponde al repositorio esperado")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", action="store_true", help="Cargar el archivo antes de comprobar las imagenes")
    parser.add_argument("--revision", default=os.getenv("GITHUB_SHA"))
    args = parser.parse_args()
    output = ROOT / "artifacts"
    manifest = json.loads((output / "images-manifest.json").read_text(encoding="utf-8"))
    validate_manifest(manifest, args.revision)
    archive = output / manifest["archive"]["file"]
    verify_checksum(archive, manifest["archive"]["sha256"])
    if args.load:
        subprocess.run(["docker", "image", "load", "--input", str(archive)], check=True, timeout=180)
    for image in manifest["images"].values():
        result = subprocess.run(
            ["docker", "image", "inspect", image["reference"]],
            check=True, capture_output=True, text=True, timeout=30,
        )
        validate_image(json.loads(result.stdout)[0], image, manifest)
    print("OK: checksum, commit, etiquetas OCI e identificadores de ambas imagenes", flush=True)


if __name__ == "__main__":
    main()
