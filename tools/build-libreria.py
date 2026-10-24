"""Prepara i dati della Libreria (libreria/): un JSON con i libri e le copertine in alta definizione.

Le copertine HD vengono dalla scena per le dirette (STREAM_LAB/libreria/prepara.py le ricava dai PDF di stampa);
qui si ricomprimono per il web. Le immagini A+ sono quelle già nell'archivio (image/galleria/).
Uso: python3 tools/build-libreria.py
"""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STREAM = Path.home() / "1PROGETTI" / "trading" / "STREAM_LAB" / "public" / "libreria"
OUT = ROOT / "libreria"


def main():
    scena = {b["id"]: b for b in json.loads((STREAM / "libri.json").read_text(encoding="utf-8"))}
    libri = []
    for x in json.loads((ROOT / "data.json").read_text(encoding="utf-8")):
        b = scena.get(x["id"])
        if not b:
            continue
        dest = OUT / "copertine" / f'{x["id"]}.jpg'
        sorg = STREAM / "copertine" / f'{x["id"]}.jpg'
        if sorg.exists() and (not dest.exists() or dest.stat().st_mtime < sorg.stat().st_mtime):
            subprocess.run(["magick", str(sorg), "-resize", "x960", "-strip", "-interlace", "Plane", "-quality", "80", str(dest)], check=True)
        libri.append({**{k: b[k] for k in ("id", "titolo", "categoria", "tipo", "pagine", "formato", "frase", "url", "colori")},
                      "copertina": f'copertine/{x["id"]}.jpg',
                      "aplus": ["../" + (g["src"] if isinstance(g, dict) else g) for g in (x.get("galleria") or [])]})
    (OUT / "libri.json").write_text(json.dumps(libri, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(libri), "libri nella libreria")


if __name__ == "__main__":
    main()
