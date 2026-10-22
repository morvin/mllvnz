#!/usr/bin/env python3
"""
Legge le opere di un artista da Fine Art America e le aggiunge (o aggiorna)
in data.json, nella famiglia "Arte".

    python3 tools/faa.py https://fineartamerica.com/profiles/vincenzo-morello

Per ogni opera salva l'immagine in image/arte/ e nel campo "faa" della voce:
tecnica, data di caricamento e tag. Le voci gia' presenti (stesso indirizzo)
vengono aggiornate senza toccare titolo, descrizione e testi scritti a mano.
"""
import html as htmllib
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data.json")
IMG_DIR = os.path.join(ROOT, "image", "arte")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TECNICHE = {"painting": "Dipinto", "photograph": "Fotografia", "digital art": "Arte digitale",
            "drawing": "Disegno", "mixed media": "Tecnica mista", "pastel": "Pastello",
            "sculpture": "Scultura", "relief": "Rilievo", "tapestry - textile": "Tessuto"}
MESI_EN = ["january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december"]
FAMIGLIE = {"Progetti": 0, "Libri": 1, "App": 2, "Arte": 3}


def contesto_ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def scarica(url, binario=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30, context=contesto_ssl()) as r:
        dati = r.read()
    return dati if binario else dati.decode("utf-8", "replace")


def testo(s):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def meta(h, nome):
    m = re.search(rf"<meta property=(['\"]){nome}\1 content=(['\"])(.*?)\2", h)
    return htmllib.unescape(m.group(3)).strip() if m else ""


def leggi(url):
    h = scarica(url)
    # og:title: "Naples by Vincenzo Morello"
    titolo, _, artista = meta(h, "og:title").rpartition(" by ")
    # og:description: "Naples Painting by Vincenzo Morello"
    tecnica_en = re.sub(rf"\s+by {re.escape(artista)}$", "", meta(h, "og:description"))
    tecnica_en = tecnica_en[len(titolo):].strip().lower() if tecnica_en.startswith(titolo) else tecnica_en.lower()
    dati = {"tecnica": TECNICHE.get(tecnica_en, tecnica_en.capitalize()), "artista": artista}
    m = re.search(r"[Uu]ploaded(?: on)?\s+(\w+)\s+(\d+)\w*,\s+(\d{4})", h)
    if m and m.group(1).lower() in MESI_EN:
        dati["caricata"] = f"{m.group(3)}-{MESI_EN.index(m.group(1).lower()) + 1:02d}-{int(m.group(2)):02d}"
    m = re.search(r">\s*Tags\s*<([\s\S]*?)More from", h)
    if m:
        tag = [testo(t) for t in re.findall(r"<a[^>]*>([^<]+)</a>", m.group(1))]
        dati["tag"] = [t for t in tag if t][:12]
    dati["immagine_remota"] = meta(h, "og:image")
    dati["aggiornato"] = date.today().isoformat()
    return titolo, dati


def salva_immagine(url, percorso):
    from PIL import Image
    im = Image.open(io.BytesIO(scarica(url, binario=True))).convert("RGB")
    im.thumbnail((900, 900), Image.LANCZOS)
    im.save(os.path.join(ROOT, percorso), "JPEG", quality=82, optimize=True, progressive=True)
    return percorso


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    profilo = sys.argv[1].rstrip("/")
    slug_artista = profilo.split("/profiles/")[1].split("?")[0]
    h = scarica(profilo + "/shop")
    # Solo le opere dell'artista: le altre in pagina sono suggerimenti del sito
    opere = sorted(set(re.findall(rf"/featured/[a-z0-9-]+-{re.escape(slug_artista)}\.html", h)))
    os.makedirs(IMG_DIR, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        voci = json.load(f)

    for percorso in opere:
        url = "https://fineartamerica.com" + percorso
        try:
            titolo, dati = leggi(url)
            artista = dati["artista"]
        except Exception as ex:
            print(f"  !!  {url}  {ex}")
            continue
        slug = percorso.split("/")[-1].replace(f"-{slug_artista}.html", "")
        immagine = salva_immagine(dati.pop("immagine_remota"), f"image/arte/{slug}.jpg")
        voce = next((v for v in voci if v.get("url") == url), None)
        if voce is None:
            voce = {
                "id": max(v["id"] for v in voci) + 1,
                "title": titolo,
                "date": dati.get("caricata") or date.today().isoformat(),
                "image": immagine,
                "url": url,
                "alt": f"{dati['tecnica']} «{titolo}» di {artista}.",
                "caption": "Vedi su Fine Art America",
                "description": f"{dati['tecnica']} di {artista}, disponibile come stampa su tela, "
                               "stampa incorniciata, poster e altri formati.",
                "publisher": artista,
                "lang": "it",
                "type": dati["tecnica"],
                "category": "Opere d'arte",
                "famiglia": "Arte",
            }
            voci.append(voce)
            stato = "nuova"
        else:
            stato = "aggiornata"
        voce["faa"] = dati
        print(f"  ok  {stato}  {dati['tecnica']:<14} {dati.get('caricata', '-')}  {titolo}")
        time.sleep(1.5)

    testa = voci[:1]
    resto = sorted(voci[1:], key=lambda v: (FAMIGLIE.get(v.get("famiglia", "Libri"), 9), v.get("date", "")))
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(testa + resto, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
