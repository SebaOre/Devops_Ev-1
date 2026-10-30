from copy import deepcopy
import hashlib

import pytest

from devops.verificar_artefactos import validate_image, validate_manifest, verify_checksum


@pytest.fixture
def manifest():
    revision = "a" * 40
    return {
        "schema_version": 1, "revision": revision, "tag": revision,
        "source": "https://github.com/SebaOre/Devops_Ev-1",
        "working_tree_dirty": False,
        "archive": {"file": "images.tar.gz", "sha256": hashlib.sha256(b"image-data").hexdigest()},
        "images": {
            "usuarios": {"reference": f"ep2-usuarios:{revision}", "image_id": "sha256:" + "b" * 64},
            "estadisticas": {"reference": f"ep2-estadisticas:{revision}", "image_id": "sha256:" + "c" * 64},
        },
    }


def test_valid_package_metadata_and_checksum(manifest, tmp_path):
    archive = tmp_path / "images.tar.gz"
    archive.write_bytes(b"image-data")
    validate_manifest(manifest, "a" * 40)
    verify_checksum(archive, manifest["archive"]["sha256"])


def test_wrong_commit_is_blocked(manifest):
    with pytest.raises(ValueError, match="otro commit"):
        validate_manifest(manifest, "d" * 40)


def test_tampered_archive_is_blocked(manifest, tmp_path):
    archive = tmp_path / "images.tar.gz"
    archive.write_bytes(b"modified-image-data")
    with pytest.raises(ValueError, match="modificado"):
        verify_checksum(archive, manifest["archive"]["sha256"])


def test_missing_service_is_blocked(manifest):
    del manifest["images"]["estadisticas"]
    with pytest.raises(ValueError, match="dos microservicios"):
        validate_manifest(manifest)


def test_dirty_checkout_cannot_claim_commit_identity(manifest):
    manifest["working_tree_dirty"] = True
    with pytest.raises(ValueError, match="checkout limpio"):
        validate_manifest(manifest)


@pytest.mark.parametrize("changed", ["image_id", "revision", "source"])
def test_loaded_image_must_match_identity_and_labels(manifest, changed):
    expected = manifest["images"]["usuarios"]
    actual = {
        "Id": expected["image_id"],
        "Config": {"Labels": {
            "org.opencontainers.image.revision": manifest["revision"],
            "org.opencontainers.image.source": manifest["source"],
        }},
    }
    validate_image(actual, expected, manifest)
    modified = deepcopy(actual)
    if changed == "image_id":
        modified["Id"] = "sha256:" + "e" * 64
    else:
        modified["Config"]["Labels"][f"org.opencontainers.image.{changed}"] = "incorrect"
    with pytest.raises(ValueError):
        validate_image(modified, expected, manifest)
