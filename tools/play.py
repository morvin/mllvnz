#!/usr/bin/env python3
"""
Legge le app da Google Play e le aggiunge (o aggiorna) in data.json.

    python3 tools/play.py "https://play.google.com/store/apps/developer?id=Ollerom+Apps"
    python3 tools/play.py com.ollerom.napoli com.ollerom.tokyo

Per ogni app salva icona e prime schermate in image/app/, e nel campo "play"
della voce: descrizione completa, download, date di uscita e aggiornamento,
PEGI, annunci, novità e schermate. Le voci gia' presenti (stesso id pacchetto)
vengono aggiornate senza toccare titolo, categoria e testi scritti a mano.
"""
import html as htmllib
import json
import os
import random
import re
import ssl
import sys
import time
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data.json")
IMG_DIR = os.path.join(ROOT, "image", "app")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SCHERMATE = 6
MESI = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
        "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}
PAROLE_IT = re.compile(r"\b(che|della|delle|anche|senza|tempo reale|città|mappa|per|con)\b", re.I)


def contesto_ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def scarica(url, binario=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9"})
    with urllib.request.urlopen(req, timeout=30, context=contesto_ssl()) as r:
        dati = r.read()
    return dati if binario else dati.decode("utf-8", "replace")


def testo(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = htmllib.unescape(re.sub(r"<[^>]+>", "", s))
    return re.sub(r"[ \t\xa0]+", " ", s).strip()


def data_iso(t):
    """'6 feb 2026' -> '2026-02-06'"""
    m = re.match(r"(\d{1,2}) (\w{3})\w* (\d{4})", t or "")
    if not m or m.group(2).lower() not in MESI:
        return None
    return f"{m.group(3)}-{MESI[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"


TITOLETTO = re.compile(r"^([^\wÀ-ÿ]*[A-ZÀ-Ý0-9&'’ /-]{4,}[A-ZÀ-Ý](?:\s*\([^)]*\))?:?)\s+(?=\S)")


def blocchi(desc):
    """Testo con a capo -> blocchi come quelli della scheda Amazon (h, p, ul).
    Nelle schede Play i titoletti stanno in testa alla riga ("🚆 MAPPE OFFLINE
    (...) Testo...") e gli elenchi sono spesso spunte ✅ sulla stessa riga."""
    out, voci = [], []

    def chiudi_elenco():
        nonlocal voci
        if voci:
            out.append({"ul": voci})
            voci = []

    for riga in [r.strip() for r in desc.split("\n")]:
        if not riga:
            continue
        if re.match(r"^[-•✅✔▪]", riga):
            voci.append(re.sub(r"^[-•✅✔▪\ufe0f]+\s*", "", riga))
            continue
        chiudi_elenco()
        m = TITOLETTO.match(riga)
        if m and not riga.isupper():
            out.append({"h": m.group(1).rstrip(":")})
            riga = riga[m.end():]
        elif re.sub(r"[^A-Za-zÀ-ÿ]", "", riga).isupper() and len(riga) < 120:
            out.append({"h": riga.rstrip(":")})
            continue
        if riga.count("✅") >= 2:
            testa, *spunte = re.split(r"\s*✅\s*", riga)
            if testa.strip():
                out.append({"p": testa.strip()})
            voci.extend(v.strip() for v in spunte if v.strip())
            chiudi_elenco()
        else:
            out.append({"p": riga})
    chiudi_elenco()
    return out


def leggi(pacchetto):
    url = f"https://play.google.com/store/apps/details?id={pacchetto}&hl=it&gl=IT"
    h = scarica(url)
    ld = None
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>([\s\S]*?)</script>', h):
        j = json.loads(m.group(1))
        if j.get("@type") == "SoftwareApplication":
            ld = j
    if not ld:
        raise RuntimeError("scheda senza dati")
    dati = {"pacchetto": pacchetto, "nome": ld.get("name", ""), "breve": ld.get("description", "")}
    if ld.get("contentRating"):
        dati["pegi"] = ld["contentRating"]
    autore = ld.get("author") or {}
    if autore.get("name"):
        dati["sviluppatore"] = autore["name"]
    if autore.get("url"):
        dati["sito"] = autore["url"]
    voto = ld.get("aggregateRating") or {}
    if voto.get("ratingValue"):
        dati["stelle"] = round(float(voto["ratingValue"]), 1)
        if voto.get("ratingCount"):
            dati["recensioni"] = int(voto["ratingCount"])
    gratis = all(str(o.get("price")) in ("0", "0.0") for o in ld.get("offers", []))
    dati["prezzo"] = "Gratis" if gratis else ""
    dati["icona"] = ld.get("image", "")

    m = re.search(r'data-g-id="description"[^>]*>([\s\S]*?)</div>', h)
    if m:
        dati["descrizione"] = blocchi(testo(m.group(1)))
    for valore, etichetta in re.findall(r'<div class="ClM7O">([\s\S]*?)</div><div class="g1rdde">([\s\S]*?)</div>', h):
        if testo(etichetta).startswith("Download"):
            dati["download"] = testo(valore)
    m = re.search(r'<div class="xg1aie">([^<]*)</div>', h)
    if m and data_iso(m.group(1)):
        dati["aggiornata"] = data_iso(m.group(1))
    # Data di uscita: la data piu' vecchia citata nei dati della pagina
    date_pagina = [data_iso(d) for d in re.findall(r'"(\d{1,2} (?:gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic) \d{4})"', h)]
    date_pagina = sorted(d for d in date_pagina if d)
    if date_pagina:
        dati["uscita"] = date_pagina[0]
    dati["annunci"] = "Contiene annunci" in h
    dati["acquisti"] = "Acquisti in-app" in h
    m = re.search(r'itemprop="description"[^>]*>([\s\S]*?)</div>', h[h.find("Novità"):] if "Novità" in h else "")
    if m:
        dati["novita"] = [r.strip(" -") for r in testo(m.group(1)).split("\n") if r.strip(" -")]
    schermate = re.findall(r'<img src="(https://play-lh\.googleusercontent\.com/[^"=]+)[^"]*"[^>]*alt="Immagine screenshot"', h)
    dati["schermate_remote"] = list(dict.fromkeys(schermate))[:SCHERMATE]
    dati["aggiornato"] = date.today().isoformat()
    return dati


def salva_immagine(url, percorso):
    """Scarica e riduce: icona 256px, schermate larghe al massimo 400px."""
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(scarica(url, binario=True)))
    destinazione = os.path.join(ROOT, percorso)
    if percorso.endswith(".png"):
        im = im.convert("RGBA")
        im.thumbnail((256, 256), Image.LANCZOS)
        im.save(destinazione, optimize=True)
    else:
        im = im.convert("RGB")
        im.thumbnail((400, 900), Image.LANCZOS)
        im.save(destinazione, "JPEG", quality=78, optimize=True, progressive=True)
    return percorso


def pacchetti_da(argomenti):
    out = []
    for a in argomenti:
        if "developer?id=" in a:
            h = scarica(a if "hl=" in a else a + "&hl=it")
            out += re.findall(r'href="/store/apps/details\?id=([\w.]+)', h)
        else:
            out.append(a)
    return list(dict.fromkeys(out))


def main():
    pacchetti = pacchetti_da(sys.argv[1:])
    if not pacchetti:
        sys.exit(__doc__)
    os.makedirs(IMG_DIR, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        voci = json.load(f)

    for p in pacchetti:
        try:
            dati = leggi(p)
        except Exception as ex:
            print(f"  !!  {p}  {ex}")
            continue
        slug = p.split(".")[-1]
        dati["icona"] = salva_immagine(dati.pop("icona") + "=s512", f"image/app/{slug}.png")
        dati["schermate"] = [salva_immagine(u + "=w720", f"image/app/{slug}-{i + 1}.jpg")
                             for i, u in enumerate(dati.pop("schermate_remote"))]
        # Le icone di uno stesso sviluppatore si somigliano tutte: come
        # immagine della voce va la seconda schermata (di solito la mappa).
        copertina = dati["schermate"][1] if len(dati["schermate"]) > 1 else dati["icona"]
        url = f"https://play.google.com/store/apps/details?id={p}"
        voce = next((v for v in voci if v.get("url", "").endswith(f"id={p}")), None)
        if voce is None:
            nome = dati["nome"]
            voce = {
                "id": max(v["id"] for v in voci) + 1,
                "title": nome,
                "date": dati.get("uscita") or dati.get("aggiornata") or date.today().isoformat(),
                "image": copertina,
                "url": url,
                "alt": f"Schermata dell'app {nome}: la mappa con le strade e i punti di interesse.",
                "caption": "Apri su Google Play",
                "description": dati["breve"],
                "publisher": dati.get("sviluppatore", ""),
                "lang": "it" if PAROLE_IT.search(dati["breve"] + json.dumps(dati.get("descrizione", []))) else "en",
                "type": "App",
                "category": "App Trasporti",
                "famiglia": "App",
            }
            voci.append(voce)
            stato = "nuova"
        else:
            stato = "aggiornata"
        voce["play"] = dati
        print(f"  ok  {p}  {stato}  {dati.get('download', '-')} download  "
              f"{len(dati['schermate'])} schermate  {dati['nome']}")
        time.sleep(random.uniform(1.5, 3))

    # Ordine: la prima voce resta in testa, poi libri e app, ognuno per data
    famiglie = {"Progetti": 0, "Libri": 1, "App": 2, "Arte": 3}
    testa = voci[:1]
    resto = sorted(voci[1:], key=lambda v: (famiglie.get(v.get("famiglia", "Libri"), 9), v.get("date", "")))
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(testa + resto, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
