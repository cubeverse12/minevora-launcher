#!/usr/bin/env python3
"""MINEVORA: verified installer for a profile plan exported by the web preview.

This is a standalone integration component, NOT yet wired into the Qt launcher.
Dry run is the default. --apply is required to write files. It never installs
Minecraft, a mod loader, or a ready-made .mrpack modpack.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.modrinth.com/v2"
AGENT = "MINEVORA-Launcher/0.1 (https://github.com/cubeverse12/minevora-launcher)"
KINDS = {"Mod": ("mods", ".jar"),
         "Shader": ("shaderpacks", ".zip"),
         "Resource pack": ("resourcepacks", ".zip"),
         "Datapack": ("datapacks", ".zip")}
LOADERS = {"Fabric": "fabric", "Forge (plan)": "forge",
           "NeoForge (plan)": "neoforge", "Quilt (plan)": "quilt",
           "Vanilla": "minecraft"}
ID_RE = re.compile(r"^[A-Za-z0-9]{5,64}$")
SHA512_RE = re.compile(r"^[a-fA-F0-9]{128}$")
MAX_SIZE = 256 * 1024 * 1024
MAX_ITEMS = 100


class PlanError(Exception):
    """A plan cannot be installed safely."""


def _request_json(url, opener=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    try:
        with opener(request, timeout=20) as response:
            data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise PlanError("Za duża odpowiedź API Modrinth.")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PlanError("Nie udało się połączyć z Modrinth: " + str(exc)) from exc
    try:
        return json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PlanError("Odpowiedź Modrinth nie zawiera poprawnego JSON.") from exc


def read_plan(path):
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PlanError("Nie udało się odczytać planu JSON.") from exc
    if not isinstance(plan, dict):
        raise PlanError("Plan musi być obiektem JSON.")
    version = plan.get("minecraftVersion") or plan.get("version")
    loader = plan.get("loader")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z._-]{2,32}", version):
        raise PlanError("Brak prawidłowej wersji Minecrafta.")
    if loader not in LOADERS:
        raise PlanError("Nieznany loader w planie.")
    entries = plan.get("items")
    if not isinstance(entries, list) or len(entries) > MAX_ITEMS:
        raise PlanError("Nieprawidłowa lista dodatków lub przekroczony limit 100.")
    clean = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") not in KINDS:
            # Earlier preview builds allowed modpacks in this list. Those are
            # intentionally not installed as individual mods.
            raise PlanError("Plan zawiera nieobsługiwany typ (np. gotowy modpack).")
        version_id = entry.get("versionId")
        if not isinstance(version_id, str) or not ID_RE.fullmatch(version_id):
            raise PlanError("Dodatek '" + str(entry.get("name", "?"))[:60] +
                            "' nie ma identyfikatora wydania. Dodaj go ponownie z katalogu.")
        clean.append({"name": str(entry.get("name") or version_id)[:80],
                      "type": entry["type"], "versionId": version_id})
    return {"name": str(plan.get("name", "Profil"))[:60],
            "minecraftVersion": version, "loader": loader, "items": clean}


def _version_metadata(version_id, opener):
    version = _request_json(API + "/version/" + urllib.parse.quote(version_id), opener=opener)
    if not isinstance(version, dict) or version.get("id") != version_id:
        raise PlanError("Modrinth zwrócił niezgodne metadane wersji.")
    return version


def _choose_file(version, kind):
    files = version.get("files")
    if not isinstance(files, list):
        raise PlanError("Brak listy plików wydania.")
    ext = KINDS[kind][1]
    matches = []
    for data in files:
        if not isinstance(data, dict):
            continue
        filename = data.get("filename")
        digest = (data.get("hashes") or {}).get("sha512")
        size = data.get("size")
        url = data.get("url")
        if not isinstance(filename, str) or "/" in filename or "\\" in filename:
            continue
        if filename in (".", "..") or not filename.lower().endswith(ext):
            continue
        if not SHA512_RE.fullmatch(str(digest or "")):
            continue
        if not isinstance(size, int) or not 0 < size <= MAX_SIZE:
            continue
        parsed = urllib.parse.urlsplit(url if isinstance(url, str) else "")
        if parsed.scheme != "https" or parsed.hostname not in {"cdn.modrinth.com", "cdn-raw.modrinth.com"}:
            continue
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            continue
        matches.append(data)
    if not matches:
        raise PlanError("Nie znaleziono bezpiecznego pliku " + ext + " z SHA-512.")
    return next((f for f in matches if f.get("primary") is True), matches[0])


def validate_entries(plan, opener=urllib.request.urlopen):
    """Resolve ALL metadata before any file is written (fail closed)."""
    if plan["loader"] == "Vanilla" and any(e["type"] == "Mod" for e in plan["items"]):
        raise PlanError("Mody .jar wymagają loadera Fabric, Forge, NeoForge lub Quilt.")
    result = []
    known_versions = {entry["versionId"] for entry in plan["items"]}
    known_projects = set()
    for entry in plan["items"]:
        meta = _version_metadata(entry["versionId"], opener)
        if plan["minecraftVersion"] not in meta.get("game_versions", []):
            raise PlanError(entry["name"] + ": niezgodna wersja Minecrafta.")
        project_id = meta.get("project_id")
        if isinstance(project_id, str):
            known_projects.add(project_id)
        if entry["type"] == "Mod":
            expected = LOADERS[plan["loader"]]
            if expected not in meta.get("loaders", []):
                raise PlanError(entry["name"] + ": wydanie nie jest zgodne z loaderem " + plan["loader"] + ".")
        file = _choose_file(meta, entry["type"])
        result.append({"entry": entry, "meta": meta, "file": file})
    for resolved in result:
        deps = resolved["meta"].get("dependencies", [])
        if not isinstance(deps, list):
            raise PlanError("Nieprawidłowe zależności dodatku.")
        for dep in deps:
            if not isinstance(dep, dict) or dep.get("dependency_type") != "required":
                continue
            dep_v = dep.get("version_id")
            dep_p = dep.get("project_id")
            if (dep_v and dep_v not in known_versions) and (not dep_p or dep_p not in known_projects):
                raise PlanError(resolved["entry"]["name"] +
                                ": wymagana zależność nie jest na liście: " + str(dep_p or dep_v))
            if dep_p and dep_p not in known_projects and not dep_v:
                raise PlanError(resolved["entry"]["name"] +
                                ": brakuje wymaganej zależności projektu: " + str(dep_p))
            if not dep_v and not dep_p:
                raise PlanError(resolved["entry"]["name"] +
                                ": wymagana zewnętrzna zależność nie może zostać zweryfikowana.")
    return result


def _download_verified(file, destination, opener=urllib.request.urlopen):
    """Download to an adjacent temporary file and atomically move on verified hash."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected_hash = file["hashes"]["sha512"].lower()
    expected_size = file["size"]
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise PlanError("Niedozwolony istniejący plik: " + destination.name)
        digest = hashlib.sha512(destination.read_bytes()).hexdigest()
        if digest == expected_hash and destination.stat().st_size == expected_size:
            return "już zainstalowano"
        raise PlanError("Istniejący plik różni się od wybranego wydania: " + destination.name)
    request = urllib.request.Request(file["url"], headers={"User-Agent": AGENT})
    fd, temporary = tempfile.mkstemp(prefix=".minevora-", suffix=".part", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as target:
            digest = hashlib.sha512()
            total = 0
            try:
                with opener(request, timeout=45) as response:
                    final_url = urllib.parse.urlsplit(response.geturl())
                    if final_url.scheme != "https" or final_url.hostname not in {"cdn.modrinth.com", "cdn-raw.modrinth.com"}:
                        raise PlanError("Przekierowanie pobierania poza CDN Modrinth.")
                    while True:
                        chunk = response.read(1024 * 128)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_SIZE or total > expected_size:
                            raise PlanError("Pobrany plik przekroczył deklarowany rozmiar.")
                        digest.update(chunk)
                        target.write(chunk)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                raise PlanError("Błąd pobierania: " + str(exc)) from exc
        if total != expected_size or digest.hexdigest() != expected_hash:
            raise PlanError("Błędny rozmiar lub suma SHA-512. Plik nie został zainstalowany.")
        # Protect against unintended overwrites even when the file appeared while downloading.
        if destination.exists():
            raise PlanError("Plik pojawił się w trakcie pobierania — przerwano instalację.")
        os.replace(temporary, destination)
        return "zainstalowano"
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(plan, resolved, instance, world=None, apply=False, opener=urllib.request.urlopen):
    """Return actions. --apply only writes into the explicitly selected instance."""
    root = Path(instance).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise PlanError("Wskaż istniejący katalog instancji Minecrafta.")
    world_root = Path(world).expanduser().resolve() if world else None
    if world_root and not world_root.is_dir():
        raise PlanError("Katalog świata dla datapacków nie istnieje.")
    operations = []
    claimed = set()
    for item in resolved:
        kind = item["entry"]["type"]
        if kind == "Datapack":
            if world_root is None or root not in world_root.parents:
                raise PlanError("Datapack wymaga wskazania katalogu świata z tej instancji (--world).")
            folder = world_root / "datapacks"
        else:
            folder = root / KINDS[kind][0]
        destination = folder / item["file"]["filename"]
        if destination.name in (".", "..") or not str(destination.resolve()).startswith(str(folder.resolve()) + os.sep):
            raise PlanError("Niebezpieczna nazwa pliku.")
        if destination in claimed:
            raise PlanError("Dwa dodatki próbują zapisać plik o tej samej nazwie.")
        claimed.add(destination)
        operations.append((item, destination))
    output = []
    for item, destination in operations:
        result = _download_verified(item["file"], destination, opener) if apply else "planowane"
        output.append({"name": item["entry"]["name"], "path": str(destination), "status": result})
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="MINEVORA — instalator zweryfikowanych dodatków Modrinth")
    parser.add_argument("--plan", required=True, help="Plik JSON wyeksportowany z podglądu profilu")
    parser.add_argument("--instance", required=True, help="ISTNIEJĄCY katalog instancji Minecraft")
    parser.add_argument("--world", help="Katalog konkretnego świata (tylko datapacki)")
    parser.add_argument("--apply", action="store_true", help="Pobierz dodatki, zamiast tylko wyświetlić plan")
    args = parser.parse_args(argv)
    try:
        plan = read_plan(args.plan)
        data = validate_entries(plan)
        operations = install(plan, data, args.instance, args.world, args.apply)
        print(json.dumps({"profile": plan["name"], "minecraftVersion": plan["minecraftVersion"],
                          "loader": plan["loader"], "applied": args.apply, "operations": operations},
                         ensure_ascii=False, indent=2))
        return 0
    except PlanError as exc:
        print("MINEVORA: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
