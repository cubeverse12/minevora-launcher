#!/usr/bin/env python3
"""Create MINEVORA 18.3.6: remove obsolete dashboard cards from verified 18.3.5.

The core launcher and its working menu are preserved exactly. Only the
EnchantedDashboard layout and its obsolete shortcuts are changed.
"""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

INPUT = Path("input/MINEVORA_LAUNCHER_18_3_5_UPROSZCZONY.zip")
CHECKSUM = Path("input/MINEVORA_LAUNCHER_18_3_5_UPROSZCZONY.zip.sha256")
OUTPUT = Path("dist/MINEVORA_LAUNCHER_18_3_6_CZYSTY_START.zip")
ROOT = "MINEVORA_18_3_ENCHANTED/"
DASHBOARD = ROOT + "minevora_dashboard.py"
MAIN = ROOT + "minevora_qt.py"

NEW_CARDS = """    SECTIONS=(
      ('▶','GRAJ / WERSJE','Instalacje Minecraft','versions','instances'),
      ('✦','MODY I DODATKI','Modrinth i shadery','mods','mods'),
      ('🏆','RANKING','Statystyki graczy','ranking','leaderboard'),
      ('⚔','PVP HUD','Instalacja i konfiguracja','pvp','pvp_mod_menu'),
    )
"""
NOTES = """MINEVORA 18.3.6 — UPROSZCZONY START I MENU
===========================================
Baza: oficjalna publiczna paczka 18.3.5 UPROSZCZONY.

Nowy Start ma tylko cztery kafelki:
 - Graj / Wersje
 - Mody i dodatki
 - Ranking
 - PvP HUD

Z głównego Start usunięto karty: Minigry, Marketplace, Together,
Ustawienia oraz osobny przycisk Minigry i panel Co nowego.

Menu boczne odziedziczone z 18.3.5 jest uproszczone.
NIE usunięto żadnego modułu launchera, logowania Microsoft,
listy profili, instalowania Minecrafta, ustawień RAM, loaderów,
PvP HUD ani Skin Studio. Ustawienia pozostają dostępne.

Rozpakuj plik ZIP i uruchom dołączony plik startowy BAT.
Nie wyłączaj zabezpieczeń Windows.
To wydanie bazuje na publicznej paczce 18.3.5, a nie na
ewentualnym lokalnym launcherze 18.3.19.
"""

def once(data: str, src: str, dest: str, description: str) -> str:
    n = data.count(src)
    if n != 1:
        raise AssertionError(f"{description}: expected exactly one occurrence, got {n}")
    return data.replace(src, dest, 1)

def patch_dashboard(source: str) -> str:
    begin = source.find("    SECTIONS=(\n")
    end = source.find("    def __init__(self, launcher, parent=None):", begin)
    if begin < 0 or end < 0 or end - begin > 1800:
        raise AssertionError("Could not safely locate dashboard SECTIONS")
    old = source[begin:end]
    for name in ("'MINIGRY'", "'MARKETPLACE'", "'TOGETHER'", "'USTAWIENIA'",
                 "'RANKING'", "'PVP HUD'"):
        if name not in old:
            raise AssertionError("Missing original dashboard card: " + name)
    source = source[:begin] + NEW_CARDS + source[end:]

    start = source.find("        release_row=QFrame();release_row.setObjectName('newsCard')")
    end_marker = "        self.root.addWidget(release_row)"
    last = source.find(end_marker, start)
    if start < 0 or last < 0 or last - start > 1100:
        raise AssertionError("Cannot find dashboard news banner safely")
    source = source[:start] + source[last + len(end_marker) + 1:]

    source = once(
        source,
        "        section.addWidget(title('Wszystkie funkcje • jeden styl',11,True))",
        "        section.addWidget(title('Najważniejsze funkcje',11,True))",
        "Dashboard title"
    )
    source = once(
        source,
        "        row.addWidget(action('Minigry',launcher.minigames,True))\n",
        "",
        "Extra Minigry action"
    )
    ast.parse(source)
    assert "class EnchantedDashboard" in source
    assert "'MINIGRY'" not in source[source.index("    SECTIONS=("):source.index("    def __init__(self, launcher, parent=None):")]
    assert "action('Minigry',launcher.minigames" not in source
    return source

def main() -> None:
    assert INPUT.is_file() and CHECKSUM.is_file(), "Missing verified 18.3.5 input"
    expected = CHECKSUM.read_text(encoding="utf-8").strip().split()[0].lower()
    actual = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    assert expected == actual, f"Input SHA-256 mismatch: {actual}"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(INPUT) as source, ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=7) as out:
        assert source.testzip() is None
        files = source.namelist()
        assert DASHBOARD in files and MAIN in files
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == DASHBOARD:
                payload = patch_dashboard(payload.decode("utf-8-sig")).encode("utf-8")
            out.writestr(info, payload)
        out.writestr(ROOT + "README_18_3_6_START.txt", NOTES.encode("utf-8"))
    with ZipFile(OUTPUT) as z, ZipFile(INPUT) as original:
        assert z.testzip() is None
        assert len(z.namelist()) == len(original.namelist()) + 1
        for entry in original.namelist():
            if entry != DASHBOARD:
                assert z.read(entry) == original.read(entry), f"Unintended change in {entry}"
        for entry in (MAIN, DASHBOARD):
            ast.parse(z.read(entry).decode("utf-8-sig"))
        qt = z.read(MAIN).decode("utf-8")
        assert "hidden_nav_labels=" in qt, "Simplified sidebar lost"
        assert "'▶  Graj / Wersje'" in qt, "Play control lost"
        assert "self.account_button=btn" in qt, "Login control lost"
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_name(OUTPUT.name + ".sha256").write_text(
        f"{digest}  {OUTPUT.name}\n", encoding="utf-8")
    print("SUCCESS", OUTPUT, OUTPUT.stat().st_size, "bytes", digest)
    print("Verified: full original archive retained; dashboard-only source change; AST OK")

if __name__ == "__main__":
    main()
