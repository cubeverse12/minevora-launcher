#!/usr/bin/env python3
"""Create an EXPERIMENTAL 18.3.8 Qt launcher package with a services menu.

Builds from the checksum-verified public 18.3.7 ZIP. Existing Minecraft
launcher code remains unchanged except for a visible Qt menu action that
opens the new standalone Microsoft/Modrinth services dialog.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

INPUT = Path("input/MINEVORA_LAUNCHER_18_3_7_NEON_DESKTOP.zip")
CHECKSUM = Path(str(INPUT) + ".sha256")
OUTPUT = Path("dist/MINEVORA_LAUNCHER_18_3_8_SERVICES_EXPERIMENTAL.zip")
ROOT = "MINEVORA_18_3_ENCHANTED/"
SOURCE = ROOT + "minevora_qt.py"
TOOLS = {
    "modrinth_plan_installer.py": Path("tools/modrinth_plan_installer.py"),
    "microsoft_minecraft_device_auth.py": Path("tools/microsoft_minecraft_device_auth.py"),
    "minevora_services_window.py": Path("tools/minevora_services_window.py"),
}

INJECT = '''
        # MINEVORA 18.3.8: optional Microsoft and Modrinth services window.
        from PySide6.QtGui import QAction, QKeySequence
        self._minevora_services_action = QAction("Konto Microsoft i dodatki…", self)
        self._minevora_services_action.setShortcut(QKeySequence("Ctrl+M"))
        self.menuBar().addAction(self._minevora_services_action)
        self._minevora_services_action.triggered.connect(self._minevora_open_services)

    def _minevora_open_services(self):
        from minevora_services_window import show_services
        self._minevora_services_dialog = show_services(self)
'''


class BuildError(Exception):
    pass


def verify_input():
    if not INPUT.is_file() or not CHECKSUM.is_file():
        raise BuildError("Missing verified v18.3.7 input and .sha256 file.")
    expected = CHECKSUM.read_text(encoding="utf-8").split()[0].lower()
    actual = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    if len(expected) != 64 or actual != expected:
        raise BuildError("Base v18.3.7 checksum mismatch; refusing build.")
    return actual


def patch_ui(text: str) -> str:
    tree = ast.parse(text)
    windows = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "Window"]
    if len(windows) != 1:
        raise BuildError("Expected precisely one Qt Window class.")
    cls = windows[0]
    methods = [x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == "__init__"]
    if len(methods) != 1:
        raise BuildError("Expected precisely one Window.__init__.")
    init = methods[0]
    if init.end_lineno <= init.lineno:
        raise BuildError("Expected multiline Window.__init__.")
    if "_minevora_open_services" in text:
        raise BuildError("Services menu already added; refusing duplicate patch.")
    lines = text.splitlines(keepends=True)
    if not lines[init.end_lineno - 1].endswith("\n"):
        raise BuildError("Unexpected non-newline ending on Window.__init__.")
    lines.insert(init.end_lineno, INJECT)
    updated = "".join(lines)
    newtree = ast.parse(updated)
    window = next(x for x in newtree.body if isinstance(x, ast.ClassDef) and x.name == "Window")
    if not any(isinstance(x, ast.FunctionDef) and x.name == "_minevora_open_services" for x in window.body):
        raise BuildError("Cannot find the new services action in Window class.")
    if not any(isinstance(x, ast.FunctionDef) and x.name == "__init__" for x in window.body):
        raise BuildError("Original Window.__init__ unexpectedly missing.")
    return updated


def build():
    base_hash = verify_input()
    required = {SOURCE} | {ROOT + name for name in TOOLS}
    with ZipFile(INPUT) as z:
        names = set(z.namelist())
        if SOURCE not in names:
            raise BuildError("The verified release does not contain the Qt source.")
        for key in required - {SOURCE}:
            if key in names:
                raise BuildError("Bundled file already exists and must not be replaced: " + key)
        original = z.read(SOURCE).decode("utf-8")
        updated = patch_ui(original)
        extras = {ROOT + name: file.read_bytes() for name, file in TOOLS.items()}
        extras[ROOT + "MINEVORA_SERVICES_INSTRUKCJA.txt"] = (
            "MINEVORA 18.3.8 — eksperymentalne narzędzia konta i dodatków\n\n"
            "Otwórz menu MINEVORA > Konto Microsoft i dodatki… albo Ctrl+M.\n"
            "Wymaga PySide6 i msal w środowisku Pythona uruchamiającym launcher.\n"
            "Logowanie kodem urządzenia: bez localhost i bez wpisywania hasła w launcherze.\n"
            "Właściciel projektu musi zarejestrować własny public client ID Microsoft,\n"
            "uzyskać wymagane uprawnienia usług Xbox/Minecraft i ustawić zmienną\n"
            "MINEVORA_MS_CLIENT_ID, zanim logowanie będzie mogło działać.\n"
            "Można sprawdzić plan JSON; zapis plików wymaga wyraźnego potwierdzenia.\n"
            "Funkcja NIE instaluje Minecrafta ani loaderów i nie rozwiązuje\n"
            "brakujących zależności. Nie zastępuje wydania stabilnego 18.3.7.\n"
        ).encode("utf-8")
        extras[ROOT + "START_KONTO_I_DODATKI.bat"] = (
            "@echo off\r\n"
            "cd /d \"%~dp0\"\r\n"
            "py -3 minevora_services_window.py\r\n"
            "if errorlevel 1 echo Zainstaluj brakujace zaleznosci: py -3 -m pip install PySide6 msal\r\n"
            "pause\r\n"
        ).encode("ascii")
        if any(k in names for k in extras):
            raise BuildError("An addon file already exists in source archive.")
        OUTPUT.parent.mkdir(exist_ok=True, parents=True)
        with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=8) as out:
            for info in z.infolist():
                out.writestr(info, updated.encode("utf-8") if info.filename == SOURCE else z.read(info))
            for name, value in extras.items():
                out.writestr(name, value)
    checksum = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_suffix(OUTPUT.suffix + ".sha256").write_text(
        checksum + "  " + OUTPUT.name + "\n", encoding="ascii"
    )
    print("EXPERIMENTAL SERVICES BUILD OK", OUTPUT, checksum, "base", base_hash)


if __name__ == "__main__":
    build()
