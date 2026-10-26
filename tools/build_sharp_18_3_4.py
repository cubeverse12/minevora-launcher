#!/usr/bin/env python3
"""Create MINEVORA 18.3.4 SHARP from verified official 18.3.3 release.
Preserves functionality; improves raster photo assets and Qt image scaling.
"""
from __future__ import annotations
import ast
import hashlib
import io
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image, ImageFilter, ImageOps

SOURCE = Path("input/MINEVORA_LAUNCHER_18_3_3_BEZ_ZBEDNYCH_PRZYCISKOW.zip")
OUT = Path("dist/MINEVORA_LAUNCHER_18_3_4_SHARP.zip")
EXPECTED = "ae519f1d81210ee71174f22a7ff38bcc08a5234a394d8954bebb9023d885b181"
README = """MINEVORA LAUNCHER 18.3.4 SHARP
================================
Bazą jest oficjalny launcher MINEVORA 18.3.3 z 23.10.2026.
Zachowano funkcje oraz menu PvP nowszego launchera.
Zmiany: wyższa jakość zapisu dużych zdjęć, umiarkowane wyostrzenie,
lepsza jakość skalowania miniaturek zdjęć przez Qt.
Małe grafiki pixel-art/skiny zachowują oryginalne piksele.

Rozpakuj ZIP, a następnie uruchom plik startowy .bat z paczki.
Nie instaluj ponownie starej wersji 12.2.
"""
def improve_file(name: str, payload: bytes) -> tuple[bytes, str | None]:
    lower = name.lower()
    if lower.endswith(".py"):
        try:
            src = payload.decode("utf-8-sig")
        except UnicodeError:
            return payload, None
        new = src
        # Avoid blurring intentionally pixelated Minecraft textures.
        if lower.endswith("minevora_qt.py"):
            new = new.replace(
                "Qt.KeepAspectRatioByExpanding,Qt.FastTransformation",
                "Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation",
            )
            new = new.replace(
                "Qt.KeepAspectRatio,Qt.FastTransformation",
                "Qt.KeepAspectRatio,Qt.SmoothTransformation",
            )
        if lower.endswith("minevora_visual_skin.py"):
            new = new.replace(
                "p=QPainter(self);p.drawPixmap(",
                "p=QPainter(self);p.setRenderHint(QPainter.SmoothPixmapTransform, True);p.drawPixmap(",
            )
        # Validate actual Python source before adding to archive.
        if new != src:
            ast.parse(new)
            return new.encode("utf-8"), "Qt smooth scaling"
        return payload, None

    # Preserve pixel-art PNGs and game skins exactly, sharpen only large photos.
    if not lower.endswith((".jpg", ".jpeg", ".webp")):
        return payload, None
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.load()
            if min(source.size) < 320:
                return payload, None
            img = ImageOps.exif_transpose(source)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.35, percent=115, threshold=3))
            buffer = io.BytesIO()
            if lower.endswith((".jpg",".jpeg")):
                img.convert("RGB").save(buffer, "JPEG", quality=95, subsampling=0, optimize=True)
            else:
                img.save(buffer, "WEBP", quality=96, method=6)
            return buffer.getvalue(), "photo sharpen"
    except (OSError, ValueError, SyntaxError):
        return payload, None

def main():
    assert SOURCE.exists(), f"Missing original archive: {SOURCE}"
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert actual == EXPECTED, f"Official archive checksum mismatch: {actual}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    updates=[]
    with ZipFile(SOURCE, "r") as original, ZipFile(OUT, "w", ZIP_DEFLATED, compresslevel=7) as patched:
        if original.testzip() is not None:
            raise RuntimeError("Corrupt original ZIP")
        names=original.namelist()
        assert any(n.endswith("minevora_qt.py") for n in names), "Launcher source not found"
        assert any(n.endswith("minevora_pvp_modmenu_qt.py") for n in names), "New PvP menu not found"
        for item in original.infolist():
            if item.is_dir():
                patched.writestr(item, b"")
                continue
            raw = original.read(item)
            processed, kind = improve_file(item.filename, raw)
            if kind:
                updates.append(f"{kind}: {item.filename}")
            patched.writestr(item, processed)
        root = names[0].split("/")[0] if "/" in names[0] else "MINEVORA"
        patched.writestr(f"{root}/README_18_3_4_SHARP.txt", README.encode("utf-8"))
    with ZipFile(OUT) as z:
        assert z.testzip() is None, "New ZIP failed validation"
        assert any(n.endswith("minevora_pvp_modmenu_qt.py") for n in z.namelist())
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    OUT.with_name(OUT.name + ".sha256").write_text(f"{digest}  {OUT.name}\n", encoding="utf-8")
    print("Completed", OUT, "SHA256", digest)
    print("Changes:", *updates, sep="\n - ")

if __name__ == "__main__":
    main()
