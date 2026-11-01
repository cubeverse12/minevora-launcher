#!/usr/bin/env python3
"""MINEVORA 18.3.10 START GLOW — UI-only patch on the tested 18.3.9 PLAY build.

The Minecraft launch engine, login flow, loader selection and every other file
are copied byte-for-byte. No new gameplay features are claimed.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = "MINEVORA_18_3_ENCHANTED/"
DASH = ROOT + "minevora_dashboard.py"
INPUT = Path("dist/MINEVORA_LAUNCHER_18_3_9_PLAY_EXPERIMENTAL.zip")
OUTPUT = Path("dist/MINEVORA_LAUNCHER_18_3_10_START_GLOW_EXPERIMENTAL.zip")
NOTES = ROOT + "MINEVORA_18_3_10_START_GLOW_README.txt"

BUTTON_UPGRADE = """        self.hero_play.setMinimumHeight(104)
        self.hero_play.setCursor(Qt.PointingHandCursor)
        self.hero_play.setStyleSheet(
            'QPushButton {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #c95bff,stop:.48 #9a35f1,stop:1 #6424c5);'
            'border:2px solid #dfb4ff;border-radius:19px;color:#ffffff;font-size:30px;font-weight:900;padding:12px 20px;}'
            'QPushButton:hover {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #d777ff,stop:1 #8b2be2);'
            'border:2px solid #fff0ff;}'
            'QPushButton:pressed {background:#6526b2;border:2px solid #af7bfc;}'
        )
        # Animated glow is strictly decorative; failure must never block PLAY.
        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve
            from PySide6.QtGui import QColor
            self._play_glow = QGraphicsDropShadowEffect(self.hero_play)
            self._play_glow.setColor(QColor(169, 77, 252, 185))
            self._play_glow.setOffset(0, 0)
            self.hero_play.setGraphicsEffect(self._play_glow)
            self._play_pulse = QPropertyAnimation(self._play_glow, b'blurRadius', self)
            self._play_pulse.setStartValue(16.0)
            self._play_pulse.setEndValue(30.0)
            self._play_pulse.setDuration(1700)
            self._play_pulse.setEasingCurve(QEasingCurve.InOutSine)
            self._play_pulse.setLoopCount(-1)
            self._play_pulse.start()
        except Exception:
            pass"""

SELECT_UPGRADE = """            b.setMinimumHeight(79)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                'QPushButton {background:rgba(10,12,37,220);border:1px solid #9c69d6;'
                'border-radius:15px;color:#f9efff;font-size:15px;font-weight:700;'
                'padding:12px 17px;text-align:left;}'
                'QPushButton:hover {background:#33204e;border:1px solid #e0afff;}'
                'QPushButton:pressed {background:#452366;}'
            )"""

STATUS = """        status=QLabel('MINECRAFT JAVA  •  WYBIERZ PROFIL I URUCHOM')
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet('background:transparent;color:#e2baff;font-size:12px;font-weight:700')
        hero_layout.addWidget(status)
        choices=QHBoxLayout()"""


class StartBuildError(Exception):
    pass


def replace_once(source: str, old: str, new: str, label: str) -> str:
    n = source.count(old)
    if n != 1:
        raise StartBuildError(f"{label}: expected 1 occurrence, found {n}")
    return source.replace(old, new, 1)


def patch_start(source: str) -> str:
    """Re-skin Start without altering the original launcher callbacks."""
    if "MINEVORA 18.3.10 START GLOW" in source or "self._play_pulse" in source:
        raise StartBuildError("Start appearance is already patched.")
    for expected in ("launcher.play,True", "launcher.instances", "launcher.install_mod_loader",
                     "self.hero_play.setObjectName('heroPlay')"):
        if expected not in source:
            raise StartBuildError(f"Missing vital existing launcher action: {expected}")
    original_callbacks = source.count("launcher.play")
    source = replace_once(
        source,
        "release=title('MINEVORA  •  LAUNCHER 18.3.7',12,True)",
        "release=title('MINEVORA  •  LAUNCHER 18.3.10',12,True)",
        "version label",
    )
    source = replace_once(source, "hero.setMaximumHeight(670)", "hero.setMaximumHeight(700)", "hero maximum")
    source = replace_once(
        source, "hero_layout.setContentsMargins(32,16,32,25)",
        "hero_layout.setContentsMargins(36,18,36,26)", "hero margins",
    )
    source = replace_once(source, "        choices=QHBoxLayout()", STATUS, "status above controls")
    source = replace_once(
        source, "            b.setMinimumHeight(73)", SELECT_UPGRADE,
        "version/loader selectors",
    )
    source = replace_once(
        source, "        self.hero_play.setMinimumHeight(84)", BUTTON_UPGRADE,
        "PLAY glow and styling",
    )
    ast.parse(source)
    if source.count("launcher.play") != original_callbacks:
        raise StartBuildError("PLAY callback count changed unexpectedly.")
    assert "launcher.play,True" in source
    assert "launcher.instances" in source and "launcher.install_mod_loader" in source
    return source


def build() -> Path:
    if not INPUT.is_file():
        raise StartBuildError(f"Run tools/build_play_18_3_9.py first: {INPUT}")
    with ZipFile(INPUT) as baseline:
        if baseline.testzip() is not None:
            raise StartBuildError("Source ZIP is corrupted.")
        if DASH not in baseline.namelist() or NOTES in baseline.namelist():
            raise StartBuildError("Unexpected 18.3.9 archive structure.")
        original = baseline.read(DASH).decode("utf-8-sig")
        patched = patch_start(original).encode("utf-8")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=8) as result:
            for item in baseline.infolist():
                result.writestr(item, patched if item.filename == DASH else baseline.read(item.filename))
            result.writestr(
                NOTES,
                (
                    "MINEVORA 18.3.10 — START GLOW (testowa)\n\n"
                    "Nowy styl Start: duży fioletowy PLAY, subtelna animacja świetlna,\n"
                    "dopracowane przyciski wersji/loadera i odstępy, zachowane tło 18.3.7.\n"
                    "Wszystkie mechanizmy gry i pozostałe pliki są identyczne z 18.3.9.\n"
                    "Funkcje logowania Microsoft, modów i loaderów pozostają rozwojowe.\n"
                ).encode("utf-8"),
            )
    with ZipFile(INPUT) as old, ZipFile(OUTPUT) as out:
        if out.testzip() is not None:
            raise StartBuildError("Built ZIP is corrupted.")
        assert set(out.namelist()) == set(old.namelist()) | {NOTES}
        for name in old.namelist():
            if name != DASH:
                assert out.read(name) == old.read(name), f"Unexpected change: {name}"
        ast.parse(out.read(DASH).decode("utf-8"))
        assert b"launcher.play,True" in out.read(DASH)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_name(OUTPUT.name + ".sha256").write_text(
        digest + "  " + OUTPUT.name + "\n", encoding="ascii"
    )
    print("START GLOW build verified:", OUTPUT, digest)
    return OUTPUT


if __name__ == "__main__":
    build()
