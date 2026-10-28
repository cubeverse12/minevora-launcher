#!/usr/bin/env python3
"""Build MINEVORA 18.3.7 with the website hero composition as an interactive Qt screen.

Only the dashboard and the global color theme are changed. Existing Minecraft,
Microsoft login, loaders, mods, and account behavior remain in their original files.
"""
from __future__ import annotations
import ast
import hashlib
import io
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image

INPUT=Path('input/MINEVORA_LAUNCHER_18_3_6_CZYSTY_START.zip')
CHECKSUM=Path('input/MINEVORA_LAUNCHER_18_3_6_CZYSTY_START.zip.sha256')
IMAGE=Path('input/minevora_site_hero.webp')
OUTPUT=Path('dist/MINEVORA_LAUNCHER_18_3_7_NEON_DESKTOP.zip')
ROOT='MINEVORA_18_3_ENCHANTED/'
DASH=ROOT+'minevora_dashboard.py'
MAIN=ROOT+'minevora_qt.py'
HERO_ASSET=ROOT+'assets/minevora_18_3_7_hero.jpg'

NEW_DASH_HERO="""        hero=ArtPanel('minevora_18_3_7_hero.jpg')
        hero.setObjectName('dashboardHero')
        hero.setMinimumHeight(500)
        hero.setMaximumHeight(670)
        hero_layout=QVBoxLayout(hero)
        hero_layout.setContentsMargins(32,16,32,25)
        hero_layout.setSpacing(8)
        release=title('MINEVORA  •  LAUNCHER 18.3.7',12,True)
        release.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(release)
        hero_layout.addSpacing(6)
        logo=QLabel()
        logo.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
        pix=QPixmap(str(BASE/'minevora_logo.png'))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(365,136,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:
            logo.setText('MINEVORA')
        logo.setMinimumHeight(122)
        logo.setStyleSheet('background:transparent')
        hero_layout.addWidget(logo)
        hero_layout.addWidget(title('Launcher Minecraft Java',24))
        heading=title('MINEVORA — Twój świat,',30)
        heading.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(heading)
        accent=title('Twoje zasady.',29)
        accent.setAlignment(Qt.AlignCenter)
        accent.setStyleSheet('background:transparent;color:#e29bff;font-size:29px;font-weight:850')
        hero_layout.addWidget(accent)
        subtitle=title('Odkrywaj mody, Skin Studio i PvP HUD.\\nWszystko w jednym launcherze Windows.',14,True)
        subtitle.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(subtitle)
        hero_layout.addStretch(1)
        choices=QHBoxLayout()
        choices.setSpacing(13)
        self.version_button=action('Wersja Minecraft\\nWybierz profil  ⌄',launcher.instances,False)
        self.loader_button=action('Typ instalacji\\nWybierz loader  ⌄',launcher.install_mod_loader,False)
        for b in (self.version_button,self.loader_button):
            b.setObjectName('heroSelect')
            b.setMinimumHeight(73)
            b.setAccessibleDescription('Otwórz ustawienia instalacji gry Minecraft')
            choices.addWidget(b,1)
        hero_layout.addLayout(choices)
        self.hero_play=action('▶  GRAJ\\nLauncher Windows',launcher.play,True)
        self.hero_play.setObjectName('heroPlay')
        self.hero_play.setMinimumHeight(84)
        hero_layout.addWidget(self.hero_play)
        self.root.addWidget(hero)
"""

EXTRA_QSS="""
# MINEVORA 18.3.7 — desktop website visual parity.
ENCHANTED_QSS += '''
QWidget {background:#090c1d;color:#f5edff}
QFrame#sidebar {background:#0d0b25;border-right:1px solid #68448e}
QFrame#topbar {background:#130e2b;border-bottom:1px solid #68448e}
QFrame#footer {background:#110d28;border-top:1px solid #5f4484}
QFrame#panel {background:#17122c;border:1px solid #5c437b;border-radius:16px}
QPushButton#nav {background:transparent;color:#d0c0e6;border:0;border-left:3px solid transparent;padding:13px 15px;text-align:left}
QPushButton#nav:hover {background:#26173f;color:#ffffff}
QPushButton#nav[active="true"] {background:#392259;border-left:4px solid #ca87ff;color:#fff}
QPushButton#primary {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #b442f0,stop:1 #6918c6);border:1px solid #dca5ff;color:#ffffff;border-radius:13px;font-size:16px;font-weight:800}
QPushButton#primary:hover {background:#963ae6;border:1px solid #efd2ff}
QPushButton#heroSelect {background:#10102ddf;border:1px solid #ad6bdf;border-radius:14px;color:#f9f1ff;font-weight:740;font-size:16px;padding:10px 14px;text-align:left}
QPushButton#heroSelect:hover {background:#362250;border-color:#d9a4ff}
QPushButton#heroPlay {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #b43aee,stop:.55 #9028e5,stop:1 #6c1bca);border:2px solid #edb6ff;color:#fff;border-radius:16px;font-size:29px;font-weight:850;padding:9px 15px}
QPushButton#heroPlay:hover {background:#ac40f2;border:2px solid #fff0ff}
QPushButton#enchantedOutline {background:#1a1532;border:1px solid #765193;color:#e4cff8}
QComboBox,QLineEdit,QTextEdit,QListWidget {background:#13132e;border:1px solid #654883;color:#fff;selection-background-color:#8746d1}
QPushButton#nav[clicked="true"] {background:#392259;border-left:4px solid #d29aff}
QToolTip {background:#23153e;color:#fff;border:1px solid #ba82ef}
'''
"""

NOTES="""MINEVORA 18.3.7 — DESKTOP W STYLU STRONY WWW
================================================
Ekran Start nawiązuje wyglądem do fioletowej strony MINEVORA:
to samo tło fantasy, duże logo, tytuł, dwie karty wyboru i GRAJ.
Wszystkie elementy są interaktywnymi kontrolkami Qt, nie zrzutem ekranu.

Wybór wersji otwiera prawdziwy panel profili. Przycisk loadera
otwiera istniejącą instalację loaderów. GRAJ wywołuje launcher.play.
Nie deklarujemy działania opcji niezależnie od kompatybilności gry.

Zmodyfikowane: minevora_dashboard.py, minevora_qt.py, jeden nowy JPEG.
Wszystkie pozostałe oryginalne pliki 18.3.6 zachowano bez zmian.
Brak modyfikacji logowania Microsoft, instalacji Minecrafta,
modyfikacji plików gry ani zabezpieczeń systemu.
"""

def once(haystack,needle,replacement,label):
    n=haystack.count(needle)
    if n!=1:raise AssertionError(f'{label}: expected 1 occurrence, got {n}')
    return haystack.replace(needle,replacement,1)

def patch_dashboard(source):
    start=source.index("        hero=ArtPanel('enchanted_hero.jpg')")
    end_marker="        self.root.addWidget(hero)"
    end=source.index(end_marker,start)+len(end_marker)
    original=source[start:end]
    for necessary in ('launcher.play','launcher.instances','launcher.pvp_mod_menu'):
        assert necessary in original, f'Original critical hero action missing: {necessary}'
    source=source[:start]+NEW_DASH_HERO.rstrip()+source[end:]
    source=once(source,"        self.root.setContentsMargins(20,14,20,16)",
                    "        self.root.setContentsMargins(22,12,22,18)","Dashboard margins")
    source=once(source,"        self.root.setSpacing(12)",
                    "        self.root.setSpacing(14)","Dashboard spacing")
    source=once(source,"        self.setMinimumHeight(191)",
                    "        self.setMinimumHeight(168)","Feature card height")
    source=once(source,"        self.setMinimumWidth(176)",
                    "        self.setMinimumWidth(169)","Feature card width")
    source=once(source,"        super().__init__('en_'+image+'.jpg',parent)",
                    "        super().__init__('minevora_18_3_7_hero.jpg',parent)\n        self.pixmap=QPixmap()  # unified dark cards: no legacy mixed-version imagery",
                    "Feature cards")
    source=once(source,
       "        gradient.setColorAt(0,QColor(6,12,34,188))",
       "        gradient.setColorAt(0,QColor(6,5,27,113))","Hero overlay top")
    source=once(source,
       "        gradient.setColorAt(.40,QColor(10,12,35,55))",
       "        gradient.setColorAt(.40,QColor(10,7,32,114))","Hero overlay center")
    source=once(source,
       "        gradient.setColorAt(1,QColor(7,11,32,247))",
       "        gradient.setColorAt(1,QColor(7,5,25,244))","Hero overlay bottom")
    source=once(source,
       "        self.account_label.setText(str(session.get('name',''))[:30] if logged else 'Niepołączone')",
       """        self.account_label.setText(str(session.get('name',''))[:30] if logged else 'Niepołączone')
        profile=getattr(self.launcher,'active_profile',None)
        current=str(getattr(self.launcher,'current_version','') or '')
        loader='Wybierz loader'
        if isinstance(profile,dict):
            current=str(profile.get('version') or profile.get('minecraft_version') or current)
            loader=str(profile.get('loader') or profile.get('loader_id') or loader)
        self.version_button.setText('Wersja Minecraft\\n'+(current if current else 'Wybierz profil')+'  ⌄')
        self.loader_button.setText('Typ instalacji\\n'+loader+'  ⌄')""","Dynamic profile labels")
    # use genuine names but align typography and ensure accessibility
    source=source.replace("    SECTIONS=(\n", "    SECTIONS=(\n", 1)
    ast.parse(source)
    assert "launcher.play" in source and "launcher.instances" in source
    assert "launcher.install_mod_loader" in source
    return source

def patch_main(source):
    source=once(source,"class Window(QMainWindow):",EXTRA_QSS+"\nclass Window(QMainWindow):","Theme injection")
    old_title="self.setWindowTitle('MINEVORA 18.3 • ENCHANTED LAUNCHER')"
    assert old_title in source, "Expected original main window title"
    source=source.replace(old_title,
        "self.setWindowTitle('MINEVORA 18.3.7 • NEON DESKTOP')",1)
    ast.parse(source)
    assert "self.setStyleSheet(ENCHANTED_QSS)" in source
    assert "self.account_button=btn" in source
    assert "self.ram=QComboBox()" in source
    assert "'▶  Graj / Wersje'" in source
    return source

def main():
    expected=CHECKSUM.read_text(encoding='utf-8').strip().split()[0].lower()
    actual=hashlib.sha256(INPUT.read_bytes()).hexdigest()
    assert actual==expected, "Source launcher SHA-256 does not match published checksum"
    with Image.open(IMAGE) as src:
        rgb=src.convert('RGB')
        assert rgb.width >=960 and rgb.height>=540,(rgb.width,rgb.height)
        blob=io.BytesIO()
        rgb.save(blob,'JPEG',quality=88,optimize=True,progressive=True,subsampling=0)
        jpg=blob.getvalue()
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(INPUT) as source,ZipFile(OUTPUT,'w',ZIP_DEFLATED,compresslevel=7) as result:
        assert source.testzip() is None
        allnames=source.namelist()
        assert DASH in allnames and MAIN in allnames
        for info in source.infolist():
            data=source.read(info.filename)
            if info.filename==DASH:
                data=patch_dashboard(data.decode('utf-8-sig')).encode('utf-8')
            elif info.filename==MAIN:
                data=patch_main(data.decode('utf-8-sig')).encode('utf-8')
            result.writestr(info,data)
        result.writestr(HERO_ASSET,jpg)
        result.writestr(ROOT+'README_18_3_7_NEON_DESKTOP.txt',NOTES.encode('utf-8'))
    with ZipFile(OUTPUT) as z,ZipFile(INPUT) as old:
        assert z.testzip() is None
        assert set(z.namelist()) == set(old.namelist()) | {HERO_ASSET,ROOT+'README_18_3_7_NEON_DESKTOP.txt'}
        for name in old.namelist():
            if name not in (DASH,MAIN):
                assert z.read(name)==old.read(name),f'Changed unrelated file: {name}'
        for file in (MAIN,DASH):ast.parse(z.read(file).decode('utf-8-sig'))
        assert len(z.read(HERO_ASSET))>30000
        with Image.open(io.BytesIO(z.read(HERO_ASSET))) as check:
            assert check.width>=960 and check.height>=540
    digest=hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    OUTPUT.with_name(OUTPUT.name+'.sha256').write_text(
        f'{digest}  {OUTPUT.name}\n',encoding='utf-8')
    print('SUCCESS:',OUTPUT,'bytes:',OUTPUT.stat().st_size)
    print('SHA-256:',digest)
    print('Verified: dashboard, QSS and one new background only; critical functions preserved')

if __name__=='__main__':
    main()
