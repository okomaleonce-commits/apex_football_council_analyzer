#!/usr/bin/env python3
"""Build du pack produit Framework APEX.

Transforme le guide Markdown en PDF stylé, puis assemble le pack vendable
(PDF + worksheet) dans product/dist/APEX-Framework-Pack.zip.

Stratégie robuste :
  1. Guide Markdown  -> HTML autonome stylé (toujours, via pandoc).
  2. HTML            -> PDF (si un moteur est dispo : weasyprint ou wkhtmltopdf).
  3. PDF (ou HTML) + worksheet CSV -> ZIP.

Dépendances :
  - pandoc (système)             : https://pandoc.org/installing.html
  - weasyprint (pip, recommandé) : pip install -r product/requirements-build.txt
    (ou wkhtmltopdf installé sur le système)

Si aucun moteur PDF n'est trouvé, le pack contient le HTML : ouvre-le et fais
« Imprimer -> Enregistrer en PDF ». Le résultat est identique.

Usage :
    python product/build.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUIDE_MD = HERE / "guide" / "APEX-Framework-Guide.md"
PDF_CSS = HERE / "guide" / "pdf-style.css"
WORKSHEET = HERE / "templates" / "match-analysis-worksheet.csv"
DIST = HERE / "dist"
TITLE = "Framework APEX — Guide de méthode"


def _run(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        msg = getattr(e, "stderr", "") or str(e)
        print(f"  ⚠️  {' '.join(cmd[:2])}… a échoué : {msg.strip()[:200]}")
        return False


def _pdf_engine() -> str | None:
    """Retourne un moteur PDF utilisable par pandoc, ou None."""
    try:
        import weasyprint  # noqa: F401
        return "weasyprint"
    except ImportError:
        pass
    if shutil.which("wkhtmltopdf"):
        return "wkhtmltopdf"
    return None


def build() -> int:
    if not shutil.which("pandoc"):
        print("❌ pandoc introuvable. Installe-le : https://pandoc.org/installing.html")
        return 1
    if not GUIDE_MD.exists():
        print(f"❌ Guide introuvable : {GUIDE_MD}")
        return 1

    DIST.mkdir(exist_ok=True)
    html_out = DIST / "APEX-Framework.html"
    pdf_out = DIST / "APEX-Framework.pdf"

    # 1. HTML autonome stylé (toujours produit).
    print("→ Génération du HTML…")
    ok_html = _run([
        "pandoc", str(GUIDE_MD), "-o", str(html_out),
        "--standalone", "--embed-resources",
        "--metadata", f"title={TITLE}",
        "--css", str(PDF_CSS),
    ])
    if not ok_html:
        return 1
    print(f"  ✅ {html_out.name}")

    # 2. PDF si un moteur est disponible.
    engine = _pdf_engine()
    payload = html_out
    if engine:
        print(f"→ Génération du PDF (moteur : {engine})…")
        if _run([
            "pandoc", str(GUIDE_MD), "-o", str(pdf_out),
            f"--pdf-engine={engine}", "--metadata", f"title={TITLE}",
            "--css", str(PDF_CSS),
        ]):
            print(f"  ✅ {pdf_out.name}")
            payload = pdf_out
    else:
        print("  ℹ️  Aucun moteur PDF (weasyprint/wkhtmltopdf). Le pack contiendra")
        print("     le HTML — ouvre-le et fais « Imprimer → Enregistrer en PDF ».")

    # 3. ZIP du pack vendable.
    zip_out = DIST / "APEX-Framework-Pack.zip"
    print("→ Assemblage du pack…")
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(payload, payload.name)
        if WORKSHEET.exists():
            z.write(WORKSHEET, f"bonus/{WORKSHEET.name}")
    print(f"  ✅ {zip_out}")
    print("\n🎉 Pack prêt à uploader sur Gumroad / Lemon Squeezy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
