#!/usr/bin/env python3
"""Build a non-destructive, simplified MINEVORA 18.3.5 launcher.

Input: the verified public release archive 18.3.4.
Changes only navigation presentation and dashboard shortcuts. Preserves all
modules, settings, user folders, game/version selection, and PvP installer.
"""
from __future__ import annotations

import ast
import hashlib
import io
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

SOURCE = Path("input/MINEVORA_LAUNCHER_18_3_4_SHARP.zip")
CHECKSUM = Path("input/MINEVORA_LAUNCHER_18_3_4_SHARP.zip.sha256")
OUTPUT = Path("dist/MINEVORA_LAUNCHER_18_3_5_CLEAN_MENU.zip")
ROOT = "MINEVORA_18_3_ENCHANTED/"
QT = ROOT + "minevora_qt.py"
DASHBOARD = ROOT + "minevora_dashboard.py"

NAVIGATION_OLD = (
    "   for name,fn in primary_navigation:\n"
    "    b=btn(name,fn);b.setObjectName('nav');b.setToolTip(name);nav_layout.addWidget(b);self.nav.append(b)"
)
NAVIGATION_NEW = (
    "   # Keep the full index mapping intact for legacy callbacks and highlight_nav.\n"
    "   # Only hide shortcuts that duplicate navigation or lead to unfinished demos.\n"
    "   hidden_shortcuts=('Marketplace','Minigry','Wszystkie funkcje','Together','Co nowego','Discord')\n"
    "   for name,fn in primary_navigation:\n"
    "    b=btn(name,fn);b.setObjectName('nav');b.setToolTip(name);nav_layout.addWidget(b);self.nav.append(b)\n"
    "    if any(label in name for label in hidden_shortcuts): b.hide()"
)

DASHBOARD_START = "    SECTIONS=(\n"
DASHBOARD_END = "    def __init__(self, launcher, parent=None):"
DASHBOARD_SECTIONS_NEW = """    SECTIONS=(
      ('▶','GRAJ / WERSJE','Instalacje Minecraft','versions','instances'),
      ('✦','MODY I DODATKI','Modrinth i shadery','mods','mods'),
      ('🏆','RANKING','Statystyki graczy','ranking','leaderboard'),
      ('⚔','PVP HUD','Instalacja i konfiguracja','pvp','pvp_mod_menu'),
    )
"""

NOTES = """MINEVORA Launcher 18.3.5 — PROSTE MENU
=====================================
Baza: publiczne wydanie MINEVORA 18.3.4 SHARP.

Uproszczono tylko interfejs. Usunięto z WIDOCZNEGO menu:
  • Marketplace
  • Minigry
  • Wszystkie funkcje
  • Together
  • Co nowego
  • powtórzony skrót Discord (pozostaje DOŁĄCZ NA DISCORD)

Ekran Start ma cztery karty: Graj/Wersje, Mody, Ranking, PvP HUD.
Usunięto też osobny przycisk Minigry i panel „Co nowego” ze Start.

Zachowane:
  • GRAJ, logowanie Microsoft, profile i wersje Minecrafta
  • Modrinth, instalowanie modów i zależności
  • Skin Studio, PvP HUD, Ranking
  • Ustawienia, RAM, wybór loadera, Pomoc, Discord
  • wszystkie oryginalne moduły, dane i pliki konfiguracyjne

Nie jest to aktualizacja instalowana automatycznie.
Rozpakuj ZIP do osobnego katalogu i użyj oryginalnego pliku
uruchamiającego .bat z paczki. Nie wyłączaj ochrony Windows.
"""


def replace_exact(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected once, found {count}")
    return src.replace(old, new, 1)


def update_qt(src: str) -> str:
    src = replace_exact(src, NAVIGATION_OLD, NAVIGATION_NEW, "Qt navigation")
    # Keep the settings entry accessible in the sidebar and Microsoft login intact.
    ast.parse(src)
    for required in ("('▶  Graj / Wersje',self.instances)", "('⚙  Ustawienia',self.settings)",
                     "self.account_button=btn('◉  Zaloguj Microsoft',self.login)",
                     "self.discord_invite_button=btn('💬  DOŁĄCZ NA DISCORD'", "hidden_shortcuts="):
        assert required in src, required
    return src


def update_dashboard(src: str) -> str:
    start = src.find(DASHBOARD_START)
    end = src.find(DASHBOARD_END, start)
    if start == -1 or end == -1 or not 0 < end - start < 2000:
        raise AssertionError("Dashboard card layout differs from inspected 18.3.4")
    old_section = src[start:end]
    for expected in ("'MINIGRY'", "'MARKETPLACE'", "'TOGETHER'", "'USTAWIENIA'", "'PVP HUD'"):
        assert expected in old_section, expected
    src = src[:start] + DASHBOARD_SECTIONS_NEW + src[end:]
    begin_marker = "        release_row=QFrame();release_row.setObjectName('newsCard')"
    end_marker = "        self.root.addWidget(release_row)"
    a = src.find(begin_marker)
    b = src.find(end_marker, a)
    if a == -1 or b == -1 or b - a > 1100:
        raise AssertionError("Optional news panel moved")
    src = src[:a] + src[b + len(end_marker) + 1:]
    src = replace_exact(src,
        "        section.addWidget(title('Wszystkie funkcje • jeden styl',11,True))",
        "        section.addWidget(title('Najważniejsze funkcje',11,True))",
        "Dashboard section heading")
    src = replace_exact(src,
        "        row.addWidget(action('Minigry',launcher.minigames,True))\n",
        "", "Minigames footer action")
    ast.parse(src)
    assert "class EnchantedDashboard" in src
    assert "SECTIONS=(" in src and "'PVP HUD'" in src
    assert "action('Minigry',launcher.minigames" not in src
    return src


def main() -> None:
    assert SOURCE.is_file(), f"Missing source: {SOURCE}"
    assert CHECKSUM.is_file(), f"Missing verified checksum: {CHECKSUM}"
    expected = CHECKSUM.read_text("utf-8").split()[0].lower()
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert expected == actual, "Release checksum mismatch"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    changes = []
    with ZipFile(SOURCE) as original, ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=7) as output:
        assert original.testzip() is None, "Damaged input ZIP"
        names = original.namelist()
        assert QT in names and DASHBOARD in names, "Required source missing"
        for item in original.infolist():
            if item.is_dir():
                output.writestr(item, b"")
                continue
            payload = original.read(item)
            if item.filename == QT:
                payload = update_qt(payload.decode("utf-8-sig")).encode("utf-8")
                changes.append(item.filename)
            elif item.filename == DASHBOARD:
                payload = update_dashboard(payload.decode("utf-8-sig")).encode("utf-8")
                changes.append(item.filename)
            output.writestr(item, payload)
        output.writestr(ROOT + "README_18_3_5_CLEAN_MENU.txt", NOTES.encode("utf-8"))
    with ZipFile(OUTPUT) as result:
        assert result.testzip() is None, "Built ZIP is corrupt"
        for name in (QT, DASHBOARD):
            ast.parse(result.read(name).decode("utf-8"))
        assert len(result.namelist()) == len(names) + 1
        assert set(names).issubset(result.namelist()), "Original files were lost"
        assert "hidden_shortcuts=" in result.read(QT).decode("utf-8")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_name(OUTPUT.name + ".sha256").write_text(
        f"{digest}  {OUTPUT.name}\n", encoding="utf-8")
    print("BUILT", OUTPUT, "SHA256", digest, "changed", changes)
    print("All original files retained, only 2 Python UIs modified")


if __name__ == "__main__":
    main()
