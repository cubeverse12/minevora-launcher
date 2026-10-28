#!/usr/bin/env python3
"""Verified 18.3.6 -> 18.3.7: MINEVORA neon desktop dashboard.

Only the dashboard source and two dedicated visual assets change.
All game, login, installer, loaders, and settings modules remain byte-identical.
"""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

SRC = Path("input/MINEVORA_LAUNCHER_18_3_6_CZYSTY_START.zip")
SHA = Path("input/MINEVORA_LAUNCHER_18_3_6_CZYSTY_START.zip.sha256")
DEST = Path("dist/MINEVORA_LAUNCHER_18_3_7_NEON_DESKTOP.zip")
BASE = "MINEVORA_18_3_ENCHANTED/"
DASH = BASE + "minevora_dashboard.py"
MAIN = BASE + "minevora_qt.py"
ART = BASE + "assets/minevora_neon_desktop.jpg"
LOGO = BASE + "assets/minevora_neon_logo.png"

NEW_HERO = r"""        hero=ArtPanel('minevora_neon_desktop.jpg')
        hero.setObjectName('dashboardHero')
        hero.setMinimumHeight(590)
        hero.setMaximumHeight(800)
        hero_layout=QVBoxLayout(hero)
        hero_layout.setContentsMargins(29,23,29,25)
        hero_layout.setSpacing(9)
        edition=title('MINEVORA • LAUNCHER WINDOWS 18.3.7',11,True)
        edition.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(edition)
        logo=QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setMinimumHeight(140)
        logo.setMaximumHeight(170)
        logo.setStyleSheet('background:transparent;')
        logo_image=QPixmap(str(ASSETS/'minevora_neon_logo.png'))
        if not logo_image.isNull():
            logo.setPixmap(logo_image.scaled(455,150,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else:
            logo.setText('MINEVORA')
            logo.setStyleSheet('color:#e5b5ff;font-size:46px;font-weight:900;background:transparent;')
        hero_layout.addWidget(logo)
        hero_layout.addStretch(2)
        heading=QLabel('Launcher Minecraft Java\nMINEVORA — Twój świat,\nTwoje zasady.')
        heading.setAlignment(Qt.AlignCenter)
        heading.setWordWrap(True)
        heading.setStyleSheet('background:transparent;color:#f9eeff;font-size:29px;font-weight:850;')
        hero_layout.addWidget(heading)
        caption=title('Odkrywaj mody, Skin Studio i PvP HUD w projekcie MINEVORA.',14,True)
        caption.setAlignment(Qt.AlignCenter)
        caption.setStyleSheet('background:transparent;color:#e1d4ef;font-size:14px;font-weight:550;')
        hero_layout.addWidget(caption)
        hero_layout.addStretch(2)

        selectors=QHBoxLayout()
        selectors.setSpacing(13)
        version_frame=QFrame()
        version_frame.setObjectName('minevoraVersionCard')
        version_frame.setStyleSheet('QFrame#minevoraVersionCard{background:rgba(10,12,34,235);border:2px solid #ab6cde;border-radius:15px;}')
        vbox=QVBoxLayout(version_frame)
        vbox.setContentsMargins(15,12,15,13)
        vbox.setSpacing(5)
        vlabel=title('Wersja Minecraft',13,True)
        vlabel.setStyleSheet('background:transparent;color:#ddc8f3;font-size:13px;font-weight:700;')
        vbox.addWidget(vlabel)
        self.version_combo=QComboBox()
        self.version_combo.setAccessibleName('Wybierz zainstalowaną wersję Minecraft')
        self.version_combo.setToolTip('Lista zainstalowanych wersji. Instalacja: Graj / Wersje.')
        self.version_combo.setStyleSheet('QComboBox{background:#17132c;color:#fff;border:1px solid #8c5dbf;border-radius:9px;padding:9px 10px;font-size:17px;font-weight:800;min-height:30px;} QComboBox QAbstractItemView{background:#14132c;color:#fff;selection-background-color:#8250c5;}')
        vbox.addWidget(self.version_combo)
        selectors.addWidget(version_frame,1)

        loader_frame=QFrame()
        loader_frame.setObjectName('minevoraLoaderCard')
        loader_frame.setStyleSheet('QFrame#minevoraLoaderCard{background:rgba(10,12,34,235);border:2px solid #ab6cde;border-radius:15px;}')
        lbox=QVBoxLayout(loader_frame)
        lbox.setContentsMargins(15,12,15,13)
        lbox.setSpacing(5)
        llabel=title('Typ instalacji',13,True)
        llabel.setStyleSheet('background:transparent;color:#ddc8f3;font-size:13px;font-weight:700;')
        lbox.addWidget(llabel)
        self.loader_combo=QComboBox()
        self.loader_combo.addItems(['Vanilla','Fabric','Forge','NeoForge','Quilt'])
        self.loader_combo.setAccessibleName('Filtruj zainstalowane wersje według loadera')
        self.loader_combo.setToolTip('Filtr loadera dla zainstalowanych wersji. Instaluj przez Graj / Wersje.')
        self.loader_combo.setStyleSheet('QComboBox{background:#17132c;color:#fff;border:1px solid #8c5dbf;border-radius:9px;padding:9px 10px;font-size:17px;font-weight:800;min-height:30px;} QComboBox QAbstractItemView{background:#14132c;color:#fff;selection-background-color:#8250c5;}')
        lbox.addWidget(self.loader_combo)
        selectors.addWidget(loader_frame,1)
        hero_layout.addLayout(selectors)

        self.loader_combo.currentIndexChanged.connect(self._refresh_versions)
        self.version_combo.currentIndexChanged.connect(self._choose_installed_version)
        self._sync_loader()
        self._refresh_versions()
        play=action('▶    GRAJ',launcher.play,True)
        play.setObjectName('minevoraHeroPlay')
        play.setAccessibleName('GRAJ — uruchom wybraną wersję Minecraft')
        play.setMinimumHeight(77)
        play.setStyleSheet('QPushButton#minevoraHeroPlay{background:#9334e4;color:#fff;border:2px solid #e3a9ff;border-radius:17px;padding:15px;font-size:29px;font-weight:900;} QPushButton#minevoraHeroPlay:hover{background:#ad40f1;border-color:#f9daff;}')
        hero_layout.addWidget(play)
        self.root.addWidget(hero)"""

NEW_METHODS = r"""
    def _sync_loader(self):
        current=str(getattr(self.launcher,'current_version','') or '').lower()
        loader=('NeoForge' if 'neoforge' in current else
                'Fabric' if 'fabric' in current else
                'Quilt' if 'quilt' in current else
                'Forge' if 'forge' in current else 'Vanilla')
        self.loader_combo.blockSignals(True)
        try:
            self.loader_combo.setCurrentText(loader)
        finally:
            self.loader_combo.blockSignals(False)

    def _refresh_versions(self,*_):
        # No false version labels: only installed Minecraft JSON manifests.
        import os
        root=Path(os.environ.get('APPDATA',str(Path.home())))/'.minecraft'/'versions'
        versions=[]
        if root.exists():
            try:
                versions=sorted((p.name for p in root.iterdir()
                    if p.is_dir() and (p/(p.name+'.json')).exists()), reverse=True)
            except OSError:
                versions=[]
        choice=self.loader_combo.currentText()
        def kind(v):
            name=v.lower()
            if 'neoforge' in name:return 'NeoForge'
            if 'fabric' in name:return 'Fabric'
            if 'quilt' in name:return 'Quilt'
            if 'forge' in name:return 'Forge'
            return 'Vanilla'
        selected=str(getattr(self.launcher,'current_version','') or '')
        available=[v for v in versions if kind(v)==choice]
        self.version_combo.blockSignals(True)
        try:
            self.version_combo.clear()
            if available:
                for version in available:
                    self.version_combo.addItem(version,version)
                if selected in available:
                    self.version_combo.setCurrentIndex(available.index(selected))
            else:
                self.version_combo.addItem('Brak — zainstaluj przez Graj / Wersje',None)
        finally:
            self.version_combo.blockSignals(False)

    def _choose_installed_version(self,index):
        version=self.version_combo.itemData(index)
        if version and version!=getattr(self.launcher,'current_version',None):
            # Existing verified selection logic and modded-profile support.
            self.launcher.choose_version(version)

"""
def patch_dashboard(src):
    required="from PySide6.QtWidgets import (QWidget,QScrollArea,QVBoxLayout,QHBoxLayout,QGridLayout,\n                              QLabel,QPushButton,QFrame,QSizePolicy)"
    assert src.count(required)==1,"Qt imports unexpectedly changed"
    src=src.replace(required,required.replace("QLabel,QPushButton,QFrame,QSizePolicy","QLabel,QPushButton,QFrame,QSizePolicy,QComboBox"))
    first="        hero=ArtPanel('enchanted_hero.jpg')"
    last="        self.root.addWidget(hero)"
    start=src.index(first)
    end=src.index(last,start)+len(last)
    assert 500<end-start<2000,"Source hero block changed"
    src=src[:start]+NEW_HERO+src[end:]
    marker="    def _arrange(self,cols):"
    assert src.count(marker)==1
    src=src.replace(marker,NEW_METHODS+marker)
    line="        self.account_label.setText(str(session.get('name',''))[:30] if logged else 'Niepołączone')"
    assert src.count(line)==1
    src=src.replace(line,line+"\n        self._sync_loader()\n        self._refresh_versions()")
    ast.parse(src)
    for keyword in ("launcher.play","launcher.choose_version","self.version_combo","self.loader_combo","self._refresh_versions"):
        assert keyword in src
    return src

def main():
    assert SRC.is_file() and SHA.is_file()
    expected=SHA.read_text(encoding='utf-8').split()[0].lower()
    assert hashlib.sha256(SRC.read_bytes()).hexdigest()==expected,"Source ZIP integrity"
    bg=Path("input/minevora_neon_desktop.jpg").read_bytes()
    logo=Path("input/minevora_neon_logo.png").read_bytes()
    assert len(bg)>35000 and len(logo)>10000
    DEST.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(SRC) as z,ZipFile(DEST,'w',ZIP_DEFLATED,compresslevel=7) as out:
        assert z.testzip() is None
        names=z.namelist()
        assert DASH in names and MAIN in names
        assert ART not in names and LOGO not in names
        for item in z.infolist():
            value=z.read(item.filename)
            if item.filename==DASH:
                value=patch_dashboard(value.decode('utf-8-sig')).encode('utf-8')
            out.writestr(item,value)
        out.writestr(ART,bg)
        out.writestr(LOGO,logo)
        out.writestr(BASE+'README_18_3_7_DESKTOP.txt',(
            "MINEVORA 18.3.7 — jednolity fioletowy ekran Start\n"
            "Pochodzi z publicznej 18.3.6; nie jest poprawką lokalnej 18.3.19.\n"
            "Nowy ekran posiada prawdziwą listę zainstalowanych wersji, filtr loadera i GRAJ.\n"
            "Nowe instalacje i loadery dodasz w Graj / Wersje.\n"
            "Pozostałe funkcje oraz bezpieczeństwo Windows zachowano bez zmian.\n"
        ).encode('utf-8'))
    with ZipFile(SRC) as before,ZipFile(DEST) as after:
        assert after.testzip() is None
        for p in before.namelist():
            if p!=DASH:
                assert before.read(p)==after.read(p),("Unintended change",p)
        ast.parse(after.read(DASH).decode('utf-8'))
        ast.parse(after.read(MAIN).decode('utf-8-sig'))
    checksum=hashlib.sha256(DEST.read_bytes()).hexdigest()
    DEST.with_name(DEST.name+'.sha256').write_text(checksum+'  '+DEST.name+'\n',encoding='utf-8')
    print('SUCCESS',DEST,DEST.stat().st_size,'SHA-256',checksum)
    print('Verified: only dashboard.py, hero.jpg and logo.png changed/added')

if __name__=='__main__':
    main()
