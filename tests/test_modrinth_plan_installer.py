"""Offline tests for the MINEVORA Modrinth profile-plan installer."""
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "modrinth_plan_installer.py"
spec = importlib.util.spec_from_file_location("minevora_modrinth", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeResponse(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


class FakeModrinth:
    def __init__(self, metadata, files):
        self.metadata = metadata
        self.files = files
        self.calls = []

    def __call__(self, request, timeout=None):
        url = request.full_url
        self.calls.append(url)
        if url.startswith(mod.API + "/version/"):
            version_id = url.split("/")[-1]
            return FakeResponse(json.dumps(self.metadata[version_id]).encode("utf-8"), url)
        return FakeResponse(self.files[url], url)


def build_item(version_id, project_id, name, data, deps=None, loader="fabric"):
    file_url = f"https://cdn.modrinth.com/data/{project_id}/versions/{version_id}/{name}.jar"
    version = {
        "id": version_id,
        "project_id": project_id,
        "version_number": "1.0.0",
        "game_versions": ["1.21.1"],
        "loaders": [loader],
        "dependencies": deps or [],
        "files": [{
            "filename": name + ".jar",
            "url": file_url,
            "size": len(data),
            "hashes": {"sha512": hashlib.sha512(data).hexdigest()},
            "primary": True
        }]
    }
    return version, file_url


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "minecraft-profile"
        self.profile.mkdir()
        self.bytes = b"fake jar payload: only for offline unit tests"
        self.version, self.file_url = build_item("ABCDEF12", "PROJECT1", "sodium-test", self.bytes)
        self.api = FakeModrinth({"ABCDEF12": self.version}, {self.file_url: self.bytes})
        self.plan = {
            "format": "minevora-demo-plan-v2",
            "name": "Test Minecraft",
            "minecraftVersion": "1.21.1",
            "loader": "Fabric",
            "items": [{"type": "Mod", "name": "Sodium", "versionId": "ABCDEF12"}]
        }

    def write_plan(self, data=None):
        file = self.root / "plan.json"
        file.write_text(json.dumps(data if data is not None else self.plan), encoding="utf-8")
        return file

    def test_read_preview_json(self):
        plan = mod.read_plan(self.write_plan())
        self.assertEqual(plan["minecraftVersion"], "1.21.1")
        self.assertEqual(plan["items"][0]["versionId"], "ABCDEF12")

    def test_dry_run_never_writes(self):
        plan = mod.read_plan(self.write_plan())
        resolved = mod.validate_entries(plan, opener=self.api)
        result = mod.install(plan, resolved, self.profile, apply=False, opener=self.api)
        self.assertEqual(result[0]["status"], "planowane")
        self.assertFalse((self.profile / "mods").exists())

    def test_apply_verifies_hash_and_is_idempotent(self):
        plan = mod.read_plan(self.write_plan())
        resolved = mod.validate_entries(plan, opener=self.api)
        path = self.profile / "mods" / "sodium-test.jar"
        result = mod.install(plan, resolved, self.profile, apply=True, opener=self.api)
        self.assertEqual(result[0]["status"], "zainstalowano")
        self.assertEqual(path.read_bytes(), self.bytes)
        result = mod.install(plan, resolved, self.profile, apply=True, opener=self.api)
        self.assertEqual(result[0]["status"], "już zainstalowano")

    def test_bad_hash_never_installs(self):
        plan = mod.read_plan(self.write_plan())
        resolved = mod.validate_entries(plan, opener=self.api)
        self.api.files[self.file_url] = b"incorrect payload"
        with self.assertRaises(mod.PlanError):
            mod.install(plan, resolved, self.profile, apply=True, opener=self.api)
        self.assertFalse((self.profile / "mods" / "sodium-test.jar").exists())

    def test_missing_required_dependency_fails_before_install(self):
        plan = mod.read_plan(self.write_plan())
        self.version["dependencies"] = [{"project_id": "REQUIRED2", "version_id": None, "dependency_type": "required"}]
        with self.assertRaises(mod.PlanError):
            mod.validate_entries(plan, opener=self.api)
        self.assertFalse((self.profile / "mods").exists())

    def test_required_exact_version_cannot_be_replaced_by_other_version_of_same_project(self):
        self.version["dependencies"] = [
            {"project_id": "PROJECT1", "version_id": "OTHER999",
             "dependency_type": "required"}
        ]
        plan = mod.read_plan(self.write_plan())
        with self.assertRaisesRegex(mod.PlanError, "wymagana zależność"):
            mod.validate_entries(plan, opener=self.api)

    def test_required_project_cannot_be_replaced_by_different_project_version(self):
        self.version["dependencies"] = [
            {"project_id": "MISSING2", "version_id": "ABCDEF12",
             "dependency_type": "required"}
        ]
        plan = mod.read_plan(self.write_plan())
        with self.assertRaisesRegex(mod.PlanError, "zależności projektu"):
            mod.validate_entries(plan, opener=self.api)

    def test_wrong_game_version_fails(self):
        plan = mod.read_plan(self.write_plan())
        self.version["game_versions"] = ["1.20.1"]
        with self.assertRaises(mod.PlanError):
            mod.validate_entries(plan, opener=self.api)

    def test_wrong_loader_fails(self):
        plan = mod.read_plan(self.write_plan())
        self.version["loaders"] = ["forge"]
        with self.assertRaises(mod.PlanError):
            mod.validate_entries(plan, opener=self.api)

    def test_legacy_modpack_is_rejected(self):
        self.plan["items"][0]["type"] = "Modpack"
        with self.assertRaises(mod.PlanError):
            mod.read_plan(self.write_plan())

    def test_missing_version_id_is_rejected(self):
        del self.plan["items"][0]["versionId"]
        with self.assertRaises(mod.PlanError):
            mod.read_plan(self.write_plan())

    def test_unsafe_filename_is_rejected(self):
        self.version["files"][0]["filename"] = "../sodium.jar"
        plan = mod.read_plan(self.write_plan())
        with self.assertRaises(mod.PlanError):
            mod.validate_entries(plan, opener=self.api)

    def test_unsafe_download_host_is_rejected(self):
        self.version["files"][0]["url"] = "https://untrusted.example/mod.jar"
        plan = mod.read_plan(self.write_plan())
        with self.assertRaises(mod.PlanError):
            mod.validate_entries(plan, opener=self.api)

    def test_existing_modified_file_is_never_overwritten(self):
        plan = mod.read_plan(self.write_plan())
        resolved = mod.validate_entries(plan, opener=self.api)
        target = self.profile / "mods" / "sodium-test.jar"
        target.parent.mkdir()
        target.write_bytes(b"user content")
        with self.assertRaises(mod.PlanError):
            mod.install(plan, resolved, self.profile, apply=True, opener=self.api)
        self.assertEqual(target.read_bytes(), b"user content")

    def test_datapacks_need_explicit_world(self):
        data = b"zip sample"
        digest = hashlib.sha512(data).hexdigest()
        v = self.version
        v["files"] = [{"filename":"data.zip","url":"https://cdn.modrinth.com/data/PROJECT1/versions/ABCDEF12/data.zip","size":len(data),"hashes":{"sha512":digest},"primary":True}]
        self.plan["items"][0]["type"]="Datapack"
        plan = mod.read_plan(self.write_plan())
        resolved = mod.validate_entries(plan, opener=self.api)
        with self.assertRaises(mod.PlanError):
            mod.install(plan, resolved, self.profile, apply=False, opener=self.api)


if __name__ == "__main__":
    unittest.main()
