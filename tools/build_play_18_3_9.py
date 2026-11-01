#!/usr/bin/env python3
"""Build experimental MINEVORA 18.3.9: a prominent PLAY button wired to launcher.play.

Uses the published, checksum-verified 18.3.7 ZIP; retains its Minecraft
launch implementation unchanged. Carries over experimental 18.3.8 services.
Not a claim that Minecraft has been successfully launched on Windows.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from build_services_18_3_8 import INPUT, ROOT, SOURCE, TOOLS, patch_ui, verify_input

DASH = ROOT + "minevora_dashboard.py"
OUTPUT = Path("dist/MINEVORA_LAUNCHER_18_3_9_PLAY_EXPERIMENTAL.zip")
LABEL_OLD = r"self.hero_play=action('▶  GRAJ\nLauncher Windows',launcher.play,True)"
LABEL_NEW = r"self.hero_play=action('▶  PLAY\nMinecraft Java',launcher.play,True)"
OBJECT_NAME = "self.hero_play.setObjectName('heroPlay')"


class PlayBuildError(Exception):
    pass


def patch_dashboard(source: str) -> str:
    """Change only the PLAY label/accessibility; never substitute a fake click."""
    if source.count(LABEL_OLD) != 1 or source.count(OBJECT_NAME) != 1:
        raise PlayBuildError("Unexpected v18.3.7 Start screen; refusing patch.")
    if "self.hero_play.setAccessibleName(" in source:
        raise PlayBuildError("PLAY accessibility already patched.")
    source = source.replace(LABEL_OLD, LABEL_NEW, 1)
    source = source.replace(
        OBJECT_NAME,
        OBJECT_NAME
        + "\n        self.hero_play.setAccessibleName('PLAY — uruchom Minecraft Java')"
        + "\n        self.hero_play.setToolTip('Wybierz profil i wersję Minecrafta przed uruchomieniem.')"
        + "\n        self.hero_play.setAutoRepeat(False)",
        1,
    )
    ast.parse(source)
    assert source.count("launcher.play") >= 1
    assert "self.version_button=action(" in source
    assert "self.loader_button=action(" in source
    return source


def build() -> Path:
    verify_input()
    with ZipFile(INPUT) as src:
        assert src.testzip() is None
        names = set(src.namelist())
        if SOURCE not in names or DASH not in names:
            raise PlayBuildError("Base ZIP lacks required Qt/dashboard source.")
        extras = {ROOT + name: path.read_bytes() for name, path in TOOLS.items()}
        extras[ROOT + "MINEVORA_18_3_9_PLAY_README.txt"] = (
            "MINEVORA 18.3.9 — EKSPERYMENTALNA wersja PLAY\n\n"
            "Duży przycisk PLAY w zakładce Start wywołuje launcher.play\n"
            "z istniejącego, niezmodyfikowanego silnika gry.\n"
            "Karty wyboru wersji i loadera używają istniejących paneli.\n"
            "Dodano eksperymentalne narzędzia konta i dodatków z 18.3.8.\n"
            "To nie jest stabilne wydanie. Nie potwierdzono uruchomienia\n"
            "Minecrafta, logowania Microsoft ani instalacji gry na Windows 11.\n"
        ).encode("utf-8")
        if set(extras) & names:
            raise PlayBuildError("Base archive already contains an addon file.")
        main = patch_ui(src.read(SOURCE).decode("utf-8-sig"))
        dash = patch_dashboard(src.read(DASH).decode("utf-8-sig"))
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=8) as out:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == SOURCE:
                    data = main.encode("utf-8")
                elif item.filename == DASH:
                    data = dash.encode("utf-8")
                out.writestr(item, data)
            for name, data in extras.items():
                out.writestr(name, data)
    with ZipFile(OUTPUT) as built, ZipFile(INPUT) as baseline:
        if built.testzip() is not None:
            raise PlayBuildError("Output ZIP has corrupted files.")
        for filename in baseline.namelist():
            if filename not in (SOURCE, DASH):
                assert built.read(filename) == baseline.read(filename), filename
        assert LABEL_NEW in built.read(DASH).decode("utf-8")
        assert "_minevora_setup_services_menu" in built.read(SOURCE).decode("utf-8")
        ast.parse(built.read(SOURCE).decode("utf-8"))
        ast.parse(built.read(DASH).decode("utf-8"))
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    (OUTPUT.parent / (OUTPUT.name + ".sha256")).write_text(
        digest + "  " + OUTPUT.name + "\n", encoding="ascii"
    )
    print("MINEVORA 18.3.9 PLAY EXPERIMENTAL build verified:", OUTPUT, digest)
    return OUTPUT


if __name__ == "__main__":
    build()
