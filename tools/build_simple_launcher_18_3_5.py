#!/usr/bin/env python3
"""Create a reversible UI-only MINEVORA launcher cleanup from the verified 18.3.4 ZIP.

Hidden pages are left intact so game startup, account login, profiles, settings,
Minecraft installations and mod compatibility continue to work. No security
or network behavior is modified.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = "MINEVORA_18_3_ENCHANTED"
SOURCE = Path("input/MINEVORA_LAUNCHER_18_3_4_SHARP.zip")
SUMFILE = Path("input/MINEVORA_LAUNCHER_18_3_4_SHARP.zip.sha256")
OUT = Path("dist/MINEVORA_LAUNCHER_18_3_5_UPROSZCZONY.zip")
MAIN = f"{ROOT}/minevora_qt.py"

OLD_NAV_LOOP = (
    "  for name,fn in primary_navigation:\n"
    "   b=btn(name,fn);b.setObjectName('nav');b.setToolTip(name);nav_layout.addWidget(b);self.nav.append(b)"
)
NEW_NAV_LOOP = (
    "  # Keep all destinations in the internal list to preserve legacy tab indexes.\n"
    "  # Only hide redundant entries in the visible sidebar. All backend modules survive.\n"
    "  hidden_nav_labels=('Marketplace','Minigry','Discord','Wszystkie funkcje','Together','Co nowego')\n"
    "  for name,fn in primary_navigation:\n"
    "   b=btn(name,fn);b.setObjectName('nav');b.setToolTip(name);nav_layout.addWidget(b);self.nav.append(b)\n"
    "   if any(label in name for label in hidden_nav_labels):b.hide()"
)

OLD_SHORTCUTS = (
    "  for i,(name,description,fn) in enumerate([\n"
    "    ('♡ MINEVORA Together','Zapraszaj znajomych do gry',self.together),\n"
    "    ('◈ Mody','Modrinth i aktualizacje',self.mods),\n"
    "    ('▣ Marketplace','Mapy, rigi i modele',self.market),\n"
    "    ('🏆 Moje rangi','Poziomy i bonusy XP',self.creator_page),\n"
    "    ('⚔ PvP Arena','Serwery i trening',self.pvp),\n"
    "    ('🏆 Ranking graczy','Twórcy XP i PvP',self.leaderboard),\n"
    "    ('✧ Pomoc AI','Porady i rozwiązywanie błędów',self.ai_page),\n"
    "    ('🛡 Fair Play','Profile i alerty Guard',self.fairplay),\n"
    "    ('💾 Kopia danych','Backup przed zmianą komputera',self.open_backup_tool),\n"
    "    ('✦ Pozostałe','Znajdź dowolną funkcję',self.features_page)]):"
)
NEW_SHORTCUTS = (
    "  for i,(name,description,fn) in enumerate([\n"
    "    ('◈ Mody i dodatki','Modrinth i aktualizacje',self.mods),\n"
    "    ('♟ Skin Studio','Edytor skinów Minecraft 3D',self.skins),\n"
    "    ('⚔ PvP Mode','Mod i ustawienia PvP HUD',self.pvp_mod_menu),\n"
    "    ('🏆 Ranking','Rangi i statystyki gracza',self.leaderboard)]):"
)
OLD_MORE_BUTTON = "  hv.addWidget(btn('Wszystkie funkcje MINEVORA →',self.features_page))"
NEW_MORE_BUTTON = "  # Removed redundant shortcut to the full internal feature catalog."

README = """MINEVORA LAUNCHER 18.3.5 — UPROSZCZONY INTERFEJS
===================================================
Baza: publiczne, zweryfikowane wydanie MINEVORA 18.3.4 SHARP.

Widoczne menu: Start, Graj / Wersje, Mody i dodatki, Skiny 3D,
PvP, PvP Mod Menu, Ranking, Ustawienia, Pomoc.
Wciąż dostępny pozostaje przycisk Discord oraz logowanie Microsoft.

W menu ukryto: Marketplace, Minigry, powtórzony Discord,
Wszystkie funkcje, Together i Co nowego.
Na ekranie Start zostawiono cztery kafelki: Mody, Skin Studio,
PvP Mode i Ranking. Usunięto przycisk Wszystkie funkcje.

Moduły zaplecza NIE zostały skasowane. Zachowano wersje i profile,
przydział RAM, logowanie, aktualne źródła modów, przycisk GRAJ,
interfejs PvP HUD oraz ustawienia. Dostęp do katalogu dodatkowych
modułów przez Ctrl+K nadal może być możliwy.

Instalacja: rozpakuj archiwum i uruchom dołączony skrypt startowy.
Nie wyłączaj Windows Defendera ani innych zabezpieczeń.
Ta wersja dotyczy publicznej paczki 18.3.4; nie jest poprawką
lokalnej wersji 18.3.19 bez jej plików źródłowych.
"""

def once(src: str, old: str, new: str, label: str) -> str:
    n = src.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected one match, got {n}")
    return src.replace(old, new)

def patch_source(src: str) -> str:
    result = once(src, OLD_NAV_LOOP, NEW_NAV_LOOP, "Sidebar")
    result = once(result, OLD_SHORTCUTS, NEW_SHORTCUTS, "Home shortcut cards")
    result = once(result, OLD_MORE_BUTTON, NEW_MORE_BUTTON, "More features button")
    ast.parse(result)
    assert result.count("self.nav.append(b)") == 1
    for required in ("Graj / Wersje", "self.play,True", "self.ram=QComboBox()", "Zaloguj Microsoft",
                     "self.install_version", "self.pvp_mod_menu", "self.leaderboard"):
        assert required in result, f"Missing critical launcher feature: {required}"
    assert "if any(label in name for label in hidden_nav_labels):b.hide()" in result
    assert "('♟ Skin Studio','Edytor skinów Minecraft 3D',self.skins)" in result
    return result

def main() -> None:
    expected = SUMFILE.read_text(encoding="utf-8").strip().split()[0].lower()
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert expected == actual, f"Input checksum mismatch: {actual}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE) as source:
        assert source.testzip() is None
        names = source.namelist()
        assert names.count(MAIN) == 1
        oldbytes = source.read(MAIN)
        oldtext = oldbytes.decode("utf-8-sig")
        updated = patch_source(oldtext).encode("utf-8")
        with ZipFile(OUT, "w", ZIP_DEFLATED, compresslevel=7) as target:
            for item in source.infolist():
                content = updated if item.filename == MAIN else source.read(item)
                target.writestr(item, content)
            target.writestr(f"{ROOT}/README_18_3_5_UPROSZCZONE_MENU.txt", README.encode("utf-8"))
    with ZipFile(OUT) as result:
        assert result.testzip() is None
        ast.parse(result.read(MAIN).decode("utf-8"))
        for item in names:
            if item != MAIN:
                with ZipFile(SOURCE) as source:
                    assert result.read(item) == source.read(item), f"Unexpected modification: {item}"
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    checksum = OUT.with_name(OUT.name + ".sha256")
    checksum.write_text(f"{digest}  {OUT.name}\n", encoding="utf-8")
    print("SUCCESS:", OUT, OUT.stat().st_size, "bytes")
    print("SHA-256:", digest)
    print("Only changed application file:", MAIN)
    print("ZIP validation, Python AST and byte-exact remaining files: OK")

if __name__ == "__main__":
    main()
