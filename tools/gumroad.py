#!/usr/bin/env python3
"""
Legge i prodotti da Gumroad e li aggiunge (o aggiorna) in data.json,
nella famiglia "Digitale" (risorse digitali: texture, pennelli, modelli...).

    python3 tools/gumroad.py https://morvinator4.gumroad.com/l/botanical-textures

Per ogni prodotto salva la copertina in image/digitale/ e nel campo "gumroad"
della voce: prezzo, descrizione completa, valutazioni e venditore. Le voci gia'
presenti (stesso indirizzo) vengono aggiornate senza toccare i testi scritti a mano.
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
IMG_DIR = os.path.join(ROOT, "image", "digitale")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
FAMIGLIE = {"Progetti": 0, "Libri": 1, "App": 2, "Arte": 3, "Digitale": 4}
VALUTE = {"usd": "$", "eur": "€", "gbp": "£"}


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
    return re.sub(r"[ \t\xa0]+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def blocchi(descrizione_html):
    """HTML della descrizione Gumroad -> blocchi h / p / ul come le altre schede."""
    out = []
    for tag, corpo in re.findall(r"<(h\d|p|ul|ol)[^>]*>([\s\S]*?)</\1>", descrizione_html):
        if tag in ("ul", "ol"):
            voci = [testo(li) for li in re.findall(r"<li[^>]*>([\s\S]*?)</li>", corpo)]
            voci = [re.sub(r"\s+", " ", v) for v in voci if v]
            if voci:
                out.append({"ul": voci})
            continue
        t = re.sub(r"\s+", " ", testo(corpo))
        if not t or t.startswith("[") or t.lower().startswith("prezzo"):
            continue
        # Righe con spunte ✅ in fila: diventano un elenco
        righe = [r.strip() for r in testo(re.sub(r"<br\s*/?>", "\n", corpo)).split("\n") if r.strip()]
        if len(righe) > 1 and all(r.startswith("✅") for r in righe):
            out.append({"ul": [re.sub(r"\s+", " ", r.lstrip("✅ ")) for r in righe]})
        elif tag.startswith("h"):
            out.append({"h": t})
        else:
            out.append({"p": t})
    return out


def leggi(url):
    h = scarica(url)
    m = re.search(r'data-page="([^"]*)"', h)
    if not m:
        raise RuntimeError("pagina senza dati del prodotto")
    p = json.loads(htmllib.unescape(m.group(1)))["props"]["product"]
    simbolo = VALUTE.get(p.get("currency_code", ""), p.get("currency_code", "").upper())
    prezzo = f"{p['price_cents'] // 100},{p['price_cents'] % 100:02d} {simbolo}" if p.get("price_cents") else "Gratis"
    dati = {
        "nome": p["name"],
        "venditore": p["seller"]["name"],
        "negozio": p["seller"].get("profile_url", ""),
        "prezzo": prezzo,
        "sintesi": p.get("summary", ""),
        "descrizione": blocchi(p.get("description_html", "")),
        "aggiornato": date.today().isoformat(),
    }
    voti = p.get("ratings") or {}
    if voti.get("count"):
        dati["stelle"] = round(voti["average"], 1)
        dati["recensioni"] = voti["count"]
    if p.get("sales_count"):
        dati["vendite"] = p["sales_count"]
    copertine = [c for c in p.get("covers", []) if c.get("type") == "image"]
    dati["copertina_remota"] = (copertine[0].get("original_url") or copertine[0]["url"]) if copertine else ""
    return p.get("long_url") or url.split("?")[0], dati


def salva_immagine(url, percorso):
    from PIL import Image
    im = Image.open(io.BytesIO(scarica(url, binario=True))).convert("RGB")
    im.thumbnail((900, 900), Image.LANCZOS)
    im.save(os.path.join(ROOT, percorso), "JPEG", quality=84, optimize=True, progressive=True)
    return percorso


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    os.makedirs(IMG_DIR, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        voci = json.load(f)

    for indirizzo in sys.argv[1:]:
        indirizzo = indirizzo.split("?")[0]
        try:
            url, dati = leggi(indirizzo)
        except Exception as ex:
            print(f"  !!  {indirizzo}  {ex}")
            continue
        slug = url.rstrip("/").split("/")[-1]
        immagine = salva_immagine(dati.pop("copertina_remota"), f"image/digitale/{slug}.jpg") \
            if dati.get("copertina_remota") else ""
        dati.pop("copertina_remota", None)
        voce = next((v for v in voci if v.get("url") == url), None)
        if voce is None:
            titolo = dati["nome"]
            voce = {
                "id": max(v["id"] for v in voci) + 1,
                "title": titolo,
                "date": date.today().isoformat(),
                "image": immagine,
                "url": url,
                "alt": f"Copertina di {titolo}",
                "caption": "Vedi su Gumroad",
                "description": dati["sintesi"][:220],
                "publisher": dati["venditore"],
                "lang": "it",
                "type": "Pacchetto digitale",
                "category": "Risorse per artisti",
                "famiglia": "Digitale",
            }
            voci.append(voce)
            stato = "nuovo"
        else:
            stato = "aggiornato"
        voce["gumroad"] = dati
        print(f"  ok  {stato}  {dati['prezzo']}  {len(dati['descrizione'])} blocchi  {dati['nome']}")
        time.sleep(1.5)

    testa = voci[:1]
    resto = sorted(voci[1:], key=lambda v: (FAMIGLIE.get(v.get("famiglia", "Libri"), 9), v.get("date", "")))
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(testa + resto, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
