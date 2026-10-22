#!/usr/bin/env python3
"""
Genera una pagina statica per ogni voce di data.json, dentro la cartella v/,
e la home dell'archivio (index.html), che e' la pagina della prima voce.

Le pagine sono complete gia' nell'HTML: Facebook, WhatsApp e compagnia non
eseguono JavaScript, quindi titolo, descrizione e copertina devono stare scritti
li'. JavaScript (voce.js) aggiunge solo comodita': Casuale, frecce della
tastiera, condivisione e copia del link.

Genera anche og/<id>.jpg: la copertina su una card 1200x630, la misura che
Facebook mostra grande invece di ridurre a francobollo, e qr/<id>.svg: il QR
code che porta al link della voce (la scheda Amazon, per i libri).

I dati della scheda Amazon (descrizione completa, pagine, ISBN, prezzo...) si
leggono a parte con tools/amazon.py, che li salva in data.json.

Da rilanciare ogni volta che si modifica data.json:

    python3 tools/build-pages.py
"""
import hashlib
import html
import json
import os
import random
import re
import shutil
import sys
import unicodedata
from urllib.parse import quote

import segno
from PIL import Image, ImageFilter, ImageEnhance

BASE_URL = "https://morvin.github.io/mllvnz/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_DIR = os.path.join(ROOT, "v")
CARDS_DIR = os.path.join(ROOT, "og")
QR_DIR = os.path.join(ROOT, "qr")

CARD_W, CARD_H = 1200, 630
# Da cambiare se si modifica il modo di comporre la card: obbliga a rifarle tutte.
CARD_VERSIONE = 1
MANIFEST = os.path.join(CARDS_DIR, "manifest.json")

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
LINGUE = {"it": "Italiano", "en": "Inglese", "de": "Tedesco"}
FONTS = ("https://fonts.googleapis.com/css2?family=Young+Serif&family=Public+Sans:"
         "ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap")
ICONA = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E"
         "%3Crect width='16' height='16' rx='3' fill='%232c6a4e'/%3E%3Crect x='4' y='4' width='8' "
         "height='8' fill='none' stroke='%23fff' stroke-width='1.5'/%3E%3C/svg%3E")

e = lambda s: html.escape(str(s), quote=True)


def versione(nome):
    """Impronta corta del file: va nell'indirizzo (style.css?v=...) cosi' browser
    e Cloudflare riscaricano il file appena cambia, invece di tenerlo in cache ore."""
    with open(os.path.join(ROOT, nome), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def aggiorna_versioni(nome_html):
    """Stesse versioni nei file HTML scritti a mano (il catalogo)."""
    percorso = os.path.join(ROOT, nome_html)
    with open(percorso, encoding="utf-8") as f:
        testo = f.read()
    for risorsa in ("style.css", "common.js", "catalogo.js"):
        testo = re.sub(rf'(["\'])({re.escape(risorsa)})(\?v=[0-9a-f]+)?(["\'])',
                       rf"\1\2?v={versione(risorsa)}\4", testo)
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(testo)


def data_italiana(value):
    """2026-04-17 -> 17 aprile 2026"""
    try:
        anno, mese, giorno = (int(p) for p in str(value).split("-"))
        return f"{giorno} {MESI[mese - 1]} {anno}"
    except (ValueError, IndexError):
        return ""


def crea_card(cover_path, dest_path):
    """Copertina centrata su sfondo sfocato, 1200x630."""
    cover = Image.open(cover_path).convert("RGB")

    # Sfondo: la copertina ingrandita fino a coprire tutta la card, poi sfocata.
    scala = max(CARD_W / cover.width, CARD_H / cover.height)
    sfondo = cover.resize((int(cover.width * scala), int(cover.height * scala)), Image.LANCZOS)
    sinistra = (sfondo.width - CARD_W) // 2
    alto = (sfondo.height - CARD_H) // 2
    sfondo = sfondo.crop((sinistra, alto, sinistra + CARD_W, alto + CARD_H))
    sfondo = sfondo.filter(ImageFilter.GaussianBlur(28))
    sfondo = ImageEnhance.Brightness(sfondo).enhance(0.72)

    # Primo piano: la copertina intera, alta quanto la card meno un margine.
    altezza = CARD_H - 80
    larghezza = round(cover.width * altezza / cover.height)
    primo_piano = cover.resize((larghezza, altezza), Image.LANCZOS)

    x = (CARD_W - larghezza) // 2
    y = (CARD_H - altezza) // 2
    bordo = Image.new("RGB", (larghezza + 6, altezza + 6), (17, 17, 17))
    sfondo.paste(bordo, (x - 3, y - 3))
    sfondo.paste(primo_piano, (x, y))

    sfondo.save(dest_path, "JPEG", quality=82, optimize=True, progressive=True)


def crea_qr(url, dest_path):
    # Bordo e colori pieni: i lettori di QR vogliono contrasto, non stile.
    segno.make(url, error="m").save(dest_path, kind="svg", scale=4, border=2,
                                    dark="#111111", light="#ffffff", xmldecl=False)


def meta(prop, content, attr="property"):
    if not content:
        return ""
    return f'    <meta {attr}="{prop}" content="{e(content)}">\n'


# ---------------------------------------------------------------------------
# Pezzi della pagina
# ---------------------------------------------------------------------------

def dividi_titolo(titolo):
    """'Miti Greci - Parole Intrecciate (Vol. 122)' -> ('Miti Greci', 'Parole Intrecciate · Vol. 122')"""
    vol = re.search(r"\s*\(Vol\.\s*(\d+)\)", titolo)
    resto = titolo.replace(vol.group(0), "") if vol else titolo
    parti = re.split(r" - |: ", resto, maxsplit=1)
    sotto = [parti[1]] if len(parti) > 1 else []
    if vol:
        sotto.append(f"Vol. {vol.group(1)}")
    return parti[0].strip(), " · ".join(sotto)


ARTICOLI = {"il", "lo", "la", "l", "i", "gli", "le", "the", "a", "an", "der", "die", "das"}
VUOTE = {"di", "del", "della", "dei", "e", "a", "al", "all", "alla", "per", "con", "in",
         "of", "and", "for", "to", "und", "fur"}


def parola_trovata(principale):
    """Le lettere che si 'illuminano' nella riga del crucipuzzle."""
    s = unicodedata.normalize("NFKD", principale).encode("ascii", "ignore").decode()
    parole = [p for p in re.split(r"[^A-Za-z0-9]+", s) if p]
    if parole and parole[0].lower() in ARTICOLI:
        parole = parole[1:]
    lettere = ""
    for p in parole:
        if p.lower() in VUOTE:
            continue
        if lettere and len(lettere) + len(p) > 14:
            break
        lettere += p.upper()
    return lettere[:16] or "ARCHIVIO"


def riga_lettere(voce, principale):
    parola = parola_trovata(principale)
    caso = random.Random(voce["id"])
    alfabeto = "ABCDEFGHILMNOPRSTUVZ"
    totale, inizio = 48, 20
    celle = []
    for i in range(totale):
        k = i - inizio
        if 0 <= k < len(parola):
            celle.append(f'<span class="hit" style="--i:{k}">{parola[k]}</span>')
        else:
            celle.append(f"<span>{caso.choice(alfabeto)}</span>")
    return f'<div class="grid-strip" aria-hidden="true">{"".join(celle)}</div>'


def dominio(url):
    m = re.search(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else ""


def nome_sito(url):
    d = dominio(url)
    if "amazon." in d:
        return "Amazon"
    if "facebook." in d:
        return "Facebook"
    return d


def scheda(voce, a, collane, prefisso):
    righe = []

    def riga(nome, valore, testo=False):
        if valore:
            classe = ' class="txt"' if testo else ""
            righe.append(f"<dt>{e(nome)}</dt><dd{classe}>{valore}</dd>")

    for nome, valore in voce.get("scheda", []):
        riga(nome, e(valore), testo=True)
    riga("Autore", e(", ".join(a.get("autori", []))), testo=True)
    if voce.get("publisher") and voce.get("publisher") not in a.get("autori", []):
        riga("Editore", e(voce["publisher"]), testo=True)
    riga("Formato", e(a.get("formato", "")), testo=True)
    serie = a.get("serie")
    if serie:
        # Una casella per volume: porta alla pagina di quel volume nell'archivio
        volumi = collane.get(serie["nome"], {})
        caselle = []
        for n in range(1, serie["di"] + 1):
            if n == serie["numero"]:
                caselle.append(f'<span class="on" aria-current="page" title="Questo volume">{n}</span>')
            elif n in volumi:
                vid, vtitolo = volumi[n]
                caselle.append(f'<a href="{prefisso}v/{vid}.html" title="{e(vtitolo)}" '
                               f'aria-label="Libro {n}: {e(vtitolo)}">{n}</a>')
            else:
                caselle.append(f'<span class="assente" title="Non ancora in archivio">{n}</span>')
        riga("Collana", f'<div class="serie">{e(serie["nome"])}, libro {serie["numero"]} di {serie["di"]}</div>'
                        + (f'<nav class="volumi" aria-label="Altri libri della collana">{"".join(caselle)}</nav>'
                           if serie["di"] > 1 else ""), testo=True)
    riga("Pagine", e(a.get("pagine", "")))
    riga("Dimensioni", e(a.get("dimensioni", "")))
    riga("Peso", e(a.get("peso", "")))
    riga("File", e(a.get("file", "")))
    riga("ISBN-13", e(a.get("isbn13", "")))
    riga("ISBN-10", e(a.get("isbn10", "")))
    asin = re.search(r"/dp/([A-Z0-9]{10})", voce.get("url", ""))
    if asin:
        riga("ASIN", e(asin.group(1)))
    if a.get("stelle"):
        n = a.get("recensioni")
        stelle = f"{a['stelle']:.1f}".replace(".", ",")
        riga("Valutazione", e(f"{stelle} su 5" + (f" ({n} {'recensione' if n == 1 else 'recensioni'})" if n else "")))
    if a.get("classifica"):
        voci = []
        for c in a["classifica"]:
            m = re.match(r"^((?:n\.|#)\s?[\d.,]+) (in .+)$", c)
            voci.append(f"<li>{e(m.group(1))} <span>{e(m.group(2))}</span></li>" if m else f"<li>{e(c)}</li>")
        riga("Classifica", f'<ul class="rank">{"".join(voci)}</ul>')
    if not righe:
        return ""
    titolo = "Scheda del libro" if a else "Scheda"
    return (f'\n            <section aria-labelledby="h-scheda">\n'
            f'                <h2 id="h-scheda">{titolo}</h2>\n'
            f'                <dl class="scheda">{"".join(righe)}</dl>\n            </section>')


def descrizione(a):
    blocchi = []
    for b in a.get("descrizione", []):
        if "h" in b:
            blocchi.append(f"<h3>{e(b['h'])}</h3>")
        elif "p" in b:
            blocchi.append(f"<p>{e(b['p'])}</p>")
        elif "ul" in b:
            blocchi.append("<ul>" + "".join(f"<li>{e(v)}</li>" for v in b["ul"]) + "</ul>")
    if not blocchi:
        return ""
    return ('\n            <section aria-labelledby="h-desc">\n'
            '                <h2 id="h-desc">Descrizione</h2>\n'
            f'                <div class="desc">{"".join(blocchi)}</div>\n            </section>')


def altri_formati(voce, a):
    url = voce.get("url", "")
    altri = [f for f in a.get("formati", []) if f.get("asin") and f["asin"] not in url]
    if not altri:
        return ""
    base = url.split("/dp/")[0]
    voci = "".join(
        f'<li><a href="{e(base)}/dp/{e(f["asin"])}" target="_blank" rel="noopener">{e(f["formato"])}'
        + (f' <span>{e(f["prezzo"])}</span>' if f.get("prezzo") else "") + "</a></li>"
        for f in altri)
    return ('\n            <section aria-labelledby="h-formati">\n'
            '                <h2 id="h-formati">Altri formati</h2>\n'
            f'                <ul class="formati">{voci}</ul>\n            </section>')


def condivisione(url_voce, titolo, descrizione_breve, card_url):
    u = quote(url_voce, safe="")
    t = quote(f"{titolo}: {descrizione_breve}" if descrizione_breve else titolo, safe="")
    social = [
        ("Facebook", f"https://www.facebook.com/sharer/sharer.php?u={u}"),
        ("WhatsApp", f"https://wa.me/?text={t}%20{u}"),
        ("X", f"https://twitter.com/intent/tweet?url={u}&text={t}"),
        ("Telegram", f"https://t.me/share/url?url={u}&text={t}"),
    ]
    if card_url:
        social.append(("Pinterest", f"https://pinterest.com/pin/create/button/?url={u}"
                                    f"&media={quote(card_url, safe='')}&description={t}"))
    social.append(("LinkedIn", f"https://www.linkedin.com/sharing/share-offsite/?url={u}"))
    link = "".join(f'<a class="soc" href="{e(h)}" target="_blank" rel="noopener">{n}</a>' for n, h in social)
    return f"""
            <div class="share" aria-label="Condividi questa pagina">
                <span class="share-lbl">Condividi</span>
                <button type="button" class="soc native" data-azione="sistema" hidden>Condividi&hellip;</button>
                {link}
                <button type="button" class="soc" data-azione="instagram">Instagram</button>
                <button type="button" class="soc" data-azione="copia">Copia link</button>
                <span class="share-msg" role="status"></span>
            </div>"""


def costruisci_pagina(voce, indice, voci, card_url, prefisso, collane):
    """prefisso: '../' per le pagine in v/, '' per la home."""
    ids = [v["id"] for v in voci]
    titolo = voce.get("title", "Senza titolo")
    principale, sotto = dividi_titolo(titolo)
    breve = voce.get("description", "")
    url_voce = f"{BASE_URL}v/{voce['id']}.html"
    url = voce.get("url", "")
    a = voce.get("amazon") or {}
    sito = nome_sito(url)

    testa = ""
    testa += meta("description", breve, attr="name")
    testa += meta("og:site_name", "Il Mio Archivio")
    testa += meta("og:type", "article")
    testa += meta("og:title", titolo)
    testa += meta("og:description", breve)
    testa += meta("og:url", url_voce)
    if card_url:
        testa += meta("og:image", card_url)
        testa += meta("og:image:width", CARD_W)
        testa += meta("og:image:height", CARD_H)
        testa += meta("og:image:alt", voce.get("alt") or f"Copertina di {titolo}")
        testa += meta("twitter:card", "summary_large_image", attr="name")
    else:
        testa += meta("twitter:card", "summary", attr="name")
    testa += meta("twitter:title", titolo, attr="name")
    testa += meta("twitter:description", breve, attr="name")

    # --- Navigazione ---
    pagina = lambda i: f"{prefisso}v/{i}.html"

    def bottone(classe, testo, target, etichetta, icona=False):
        cls = f"btn{' icon' if icona else ''} {classe}"
        if target is None:
            return f'<span class="{cls} disabled" aria-disabled="true" aria-label="{e(etichetta)}">{testo}</span>'
        return f'<a class="{cls}" href="{pagina(target)}" aria-label="{e(etichetta)}">{testo}</a>'

    prec = ids[indice - 1] if indice > 0 else None
    succ = ids[indice + 1] if indice < len(ids) - 1 else None
    casuale = next((i for i in ids if i != voce["id"]), voce["id"])
    nome_prec = voci[indice - 1]["title"] if prec else ""
    nome_succ = voci[indice + 1]["title"] if succ else ""
    pager = f"""<nav class="pager" aria-label="Navigazione tra le voci">
        <div class="side">
            {bottone('first', '|&lsaquo;', ids[0] if indice > 0 else None, 'Prima voce', icona=True)}
            {bottone('prev', '&lsaquo; <span class="lbl">Indietro</span>', prec, f'Voce precedente: {nome_prec}')}
        </div>
        <div class="where"><b>{indice + 1}</b> di {len(ids)} <a class="btn random" href="{pagina(casuale)}" data-azione="casuale">Casuale</a></div>
        <div class="side end">
            {bottone('next', '<span class="lbl">Avanti</span> &rsaquo;', succ, f'Voce successiva: {nome_succ}')}
            {bottone('last', '&rsaquo;|', ids[-1] if succ else None, 'Ultima voce', icona=True)}
        </div>
    </nav>"""

    # --- Colonna sinistra: copertina e QR ---
    if voce.get("image"):
        img = (f'<img src="{prefisso}{e(voce["image"])}" alt="{e(voce.get("alt") or titolo)}" decoding="async">')
        copertina = (f'<a class="cover" href="{e(url)}" target="_blank" rel="noopener" '
                     f'aria-label="{e(principale)}: apri su {e(sito)}">{img}</a>' if url
                     else f'<span class="cover">{img}</span>')
    else:
        copertina = ""
    qr = ""
    if url:
        cosa = "il libro" if sito == "Amazon" else "la pagina"
        qr = f"""<div class="qr">
                <img src="{prefisso}qr/{voce['id']}.svg" alt="QR code: {e(url)}" width="96" height="96">
                <div><strong>Inquadra col telefono</strong>e {cosa} si apre su {e(sito)}.</div>
            </div>"""

    # --- Etichette, che portano al catalogo filtrato ---
    tag = []
    for campo, param, valore in (("type", "tipo", voce.get("type")),
                                 ("category", "categoria", voce.get("category")),
                                 ("lang", "lingua", voce.get("lang"))):
        if valore:
            testo = LINGUE.get(valore, valore) if campo == "lang" else valore
            tag.append(f'<a class="tag" href="{prefisso}catalogo.html?{param}={quote(valore)}">{e(testo)}</a>')

    if a:
        quando = f"Pubblicato il {data_italiana(voce.get('date'))}"
        if voce.get("publisher"):
            quando += f" · {voce['publisher']}"
    else:
        quando = f"In archivio dal {data_italiana(voce.get('date'))}"

    cta = ""
    if url:
        etichetta = "Apri su Amazon" if sito == "Amazon" else (voce.get("caption") or f"Apri su {sito}")
        prezzo = ""
        if a.get("prezzo"):
            prezzo = (f'<div class="price">{e(a["prezzo"])}'
                      f'<small>prezzo al {e(data_italiana(a.get("aggiornato")))}</small></div>')
        cta = f"""
            <div class="buy">
                <a class="cta" href="{e(url)}" target="_blank" rel="noopener">{e(etichetta)} &rarr;</a>
                {prezzo}
            </div>"""

    dati_js = json.dumps({
        "id": voce["id"], "voci": ids, "url": url_voce, "titolo": titolo,
        "immagine": f"{prefisso}{voce['image']}" if voce.get("image") else "",
        "prec": pagina(prec) if prec else "", "succ": pagina(succ) if succ else "",
        "base": f"{prefisso}v/",
    }, ensure_ascii=False)

    # Sulla home, i vecchi indirizzi ?p=ID portano alla pagina della voce
    redirect = ""
    if prefisso == "":
        redirect = ("\n    <script>(function () { var p = new URLSearchParams(location.search).get('p');"
                    " if (p && /^\\d+$/.test(p)) location.replace('v/' + p + '.html'); })();</script>")

    return f"""<!DOCTYPE html>
<html lang="{e(voce.get('lang', 'it'))}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{e(titolo)} - Il Mio Archivio</title>{redirect}
{testa}    <meta name="theme-color" content="#2c6a4e">
    <link rel="canonical" href="{url_voce}">
    <link rel="icon" href="{ICONA}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="{FONTS}">
    <link rel="stylesheet" href="{prefisso}style.css?v={versione('style.css')}">
</head>
<body>
<a href="#scheda" class="skip-link">Salta al contenuto</a>
<div class="wrap">
    <header class="top">
        <a class="brand" href="{prefisso or './'}">Il Mio Archivio <small>un posto per collezionare le mie cose</small></a>
        <nav aria-label="Sezioni"><a href="{pagina(ids[0])}" aria-current="page">Sfoglia</a><a href="{prefisso}catalogo.html">Catalogo</a></nav>
    </header>

    {pager}

    {riga_lettere(voce, principale)}

    <main class="book" id="scheda">
        <aside class="aside">
            {copertina}
            {qr}
        </aside>

        <article>
            <div class="tags">{"".join(tag)}</div>
            <h1>{e(principale)}{f'<span class="vol">{e(sotto)}</span>' if sotto else ''}</h1>
            <p class="date">{e(quando)}</p>
            <p class="lead">{e(breve)}</p>{cta}{condivisione(url_voce, titolo, breve, card_url)}{scheda(voce, a, collane, prefisso)}{descrizione(a)}{altri_formati(voce, a)}
        </article>
    </main>

    <footer class="foot"><span>&copy; 2026 Il Mio Archivio</span><span>Voce {indice + 1} di {len(ids)}</span></footer>
</div>
<script>window.VOCE = {dati_js};</script>
<script src="{prefisso}voce.js?v={versione('voce.js')}"></script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Home: presentazione dell'archivio
# ---------------------------------------------------------------------------

# Parole nascoste nella griglia della home: (parola, riga, colonna, categoria)
PAROLE_HOME = [
    ("NATURA", 0, 9, "Natura e stagioni"),
    ("MITI", 1, 2, "Miti e classici"),
    ("ARCHIVIO", 3, 5, None),
    ("VIAGGI", 4, 0, "Luoghi e viaggi"),
    ("VINO", 4, 13, "Cucina e vino"),
    ("CINEMA", 6, 9, "Cinema"),
    ("MUSICA", 7, 1, "Musica"),
]
GRIGLIA_COLONNE, GRIGLIA_RIGHE = 18, 8


def griglia_home():
    caso = random.Random(2026)
    alfabeto = "ABCDEFGHILMNOPRSTUVZ"
    celle = [[(caso.choice(alfabeto), "") for _ in range(GRIGLIA_COLONNE)] for _ in range(GRIGLIA_RIGHE)]
    for parola, r, c, categoria in PAROLE_HOME:
        classe = "hit" if categoria is None else "word"
        for k, lettera in enumerate(parola):
            celle[r][c + k] = (lettera, classe)
    out = []
    ordine = 0
    for riga in celle:
        for lettera, classe in riga:
            if classe == "hit":
                out.append(f'<span class="hit" style="--i:{ordine}">{lettera}</span>')
                ordine += 1
            elif classe:
                out.append(f'<span class="{classe}">{lettera}</span>')
            else:
                out.append(f"<span>{lettera}</span>")
    return (f'<div class="board" aria-hidden="true" style="--cols:{GRIGLIA_COLONNE}">'
            + "".join(out) + "</div>")


def crea_card_home(voci, dest_path):
    """Anteprima social della home: le ultime copertine in fila su carta da schedario."""
    sfondo = Image.new("RGB", (CARD_W, CARD_H), (242, 244, 241))
    ultime = [v for v in sorted(voci, key=lambda v: v.get("date", ""), reverse=True) if v.get("image")][:5]
    altezza = 400
    copertine = []
    for v in ultime:
        img = Image.open(os.path.join(ROOT, v["image"])).convert("RGB")
        copertine.append(img.resize((round(img.width * altezza / img.height), altezza), Image.LANCZOS))
    spazio = 24
    totale = sum(c.width for c in copertine) + spazio * (len(copertine) - 1)
    x = (CARD_W - totale) // 2
    y = (CARD_H - altezza) // 2
    for c in copertine:
        ombra = Image.new("RGB", (c.width + 4, c.height + 4), (205, 212, 207))
        sfondo.paste(ombra, (x - 2, y + 2))
        sfondo.paste(c, (x, y))
        x += c.width + spazio
    sfondo.save(dest_path, "JPEG", quality=84, optimize=True, progressive=True)


def costruisci_home(voci, collane, card_url):
    ids = [v["id"] for v in voci]
    categorie = {}
    for v in voci:
        categorie[v.get("category") or "Varie"] = categorie.get(v.get("category") or "Varie", 0) + 1
    numeri = [(len(voci), "voci"), (len(categorie), "categorie"), (len(collane), "collane")]
    numeri_html = "".join(f"<div><b>{n}</b><span>{nome}</span></div>" for n, nome in numeri)

    ultime = [v for v in sorted(voci, key=lambda v: (v.get("date", ""), v["id"]), reverse=True) if v.get("image")][:6]
    ultime_html = "".join(
        f'<a class="card" href="v/{v["id"]}.html"><img src="{e(v["image"])}" alt="{e(v.get("alt") or v["title"])}" '
        f'loading="lazy" decoding="async"><span class="card-title">{e(dividi_titolo(v["title"])[0])}</span>'
        f'<span class="card-date">{e(data_italiana(v.get("date")))}</span></a>'
        for v in ultime)

    trovate = "".join(
        f'<a class="tag" href="catalogo.html?categoria={quote(cat)}">{e(parola.capitalize())}</a>'
        for parola, _, _, cat in PAROLE_HOME if cat)

    primo = voci[0]
    titolo = "Il Mio Archivio"
    breve = (f"{len(voci)} voci da sfogliare: parole intrecciate, quaderni, guide di viaggio e libri "
             "di cinema, ognuno con la sua scheda.")
    testa = ""
    testa += meta("description", breve, attr="name")
    testa += meta("og:site_name", titolo)
    testa += meta("og:type", "website")
    testa += meta("og:title", titolo)
    testa += meta("og:description", breve)
    testa += meta("og:url", BASE_URL)
    if card_url:
        testa += meta("og:image", card_url)
        testa += meta("og:image:width", CARD_W)
        testa += meta("og:image:height", CARD_H)
        testa += meta("twitter:card", "summary_large_image", attr="name")
    dati_js = json.dumps({"id": None, "voci": ids, "url": BASE_URL, "titolo": titolo,
                          "immagine": "", "prec": "", "succ": "", "base": "v/"})

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{titolo}</title>
    <script>(function () {{ var p = new URLSearchParams(location.search).get('p');
        if (p && /^\\d+$/.test(p)) location.replace('v/' + p + '.html'); }})();</script>
{testa}    <meta name="theme-color" content="#2c6a4e">
    <link rel="canonical" href="{BASE_URL}">
    <link rel="icon" href="{ICONA}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="{FONTS}">
    <link rel="stylesheet" href="style.css?v={versione('style.css')}">
</head>
<body>
<a href="#porte" class="skip-link">Salta al contenuto</a>
<div class="wrap">
    <header class="top">
        <a class="brand" href="./">Il Mio Archivio <small>un posto per collezionare le mie cose</small></a>
        <nav aria-label="Sezioni"><a href="v/{primo['id']}.html">Sfoglia</a><a href="catalogo.html">Catalogo</a></nav>
    </header>

    <main class="home">
        <section class="hero">
            {griglia_home()}
            <div class="intro">
                <h1>Il Mio Archivio</h1>
                <p class="lead">Un posto per collezionare le mie cose: libri di parole intrecciate,
                quaderni, guide di viaggio e cinema. Ogni voce ha la sua scheda, con la copertina,
                i dettagli e il link per averla.</p>
                <div class="numeri">{numeri_html}</div>
            </div>
        </section>

        <nav class="porte" id="porte" aria-label="Da dove cominciare">
            <a class="porta" href="v/{primo['id']}.html">
                <span class="porta-n">1 di {len(ids)}</span>
                <strong>Comincia dal primo</strong>
                <span>Si parte da {e(primo['title'])} e si va avanti una voce alla volta.</span>
            </a>
            <a class="porta" href="v/{ids[len(ids) // 2]}.html" data-azione="casuale">
                <span class="porta-n">? di {len(ids)}</span>
                <strong>Pesca a caso</strong>
                <span>Una voce qualsiasi dell'archivio, diversa a ogni clic.</span>
            </a>
            <a class="porta" href="catalogo.html">
                <span class="porta-n">{len(categorie)} categorie</span>
                <strong>Apri il catalogo</strong>
                <span>Tutte le voci insieme, da filtrare per categoria, tipo e lingua.</span>
            </a>
        </nav>

        <section class="trovate" aria-labelledby="h-trovate">
            <h2 id="h-trovate">Parole trovate nella griglia</h2>
            <div class="tags">{trovate}</div>
        </section>

        <section aria-labelledby="h-ultimi">
            <h2 id="h-ultimi">Ultimi arrivi</h2>
            <div class="grid">{ultime_html}</div>
        </section>
    </main>

    <footer class="foot"><span>&copy; 2026 Il Mio Archivio</span><span>{len(voci)} voci</span></footer>
</div>
<script>window.VOCE = {dati_js};</script>
<script src="voce.js?v={versione('voce.js')}"></script>
</body>
</html>
"""


def main():
    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)

    voci = [d for d in data if isinstance(d.get("id"), int) and (d.get("image") or d.get("url"))]
    if not voci:
        sys.exit("data.json non contiene voci utilizzabili")

    # Le pagine e i QR sono testo: si riscrivono sempre, sono veloci e deterministici.
    shutil.rmtree(PAGES_DIR, ignore_errors=True)
    os.makedirs(PAGES_DIR)
    shutil.rmtree(QR_DIR, ignore_errors=True)
    os.makedirs(QR_DIR)
    os.makedirs(CARDS_DIR, exist_ok=True)

    # Le card invece si rifanno solo se serve: due compressioni JPEG della stessa
    # immagine non danno file identici, e senza questo controllo ogni esecuzione
    # sporcherebbe il repository con 70 immagini "modificate" ma uguali.
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        manifest = {}

    pagine = card = rifatte = qr = 0
    card_urls = {}

    for voce in voci:
        if voce.get("image"):
            sorgente = os.path.join(ROOT, voce["image"])
            if os.path.exists(sorgente):
                nome = f"{voce['id']}.jpg"
                destinazione = os.path.join(CARDS_DIR, nome)
                with open(sorgente, "rb") as f:
                    impronta = f"{CARD_VERSIONE}:{hashlib.sha1(f.read()).hexdigest()}"
                if manifest.get(nome) != impronta or not os.path.exists(destinazione):
                    crea_card(sorgente, destinazione)
                    manifest[nome] = impronta
                    rifatte += 1
                card_urls[voce["id"]] = f"{BASE_URL}og/{nome}"
                card += 1
            else:
                print(f"  ! immagine mancante: {voce['image']} (voce {voce['id']})")
        if voce.get("url"):
            crea_qr(voce["url"], os.path.join(QR_DIR, f"{voce['id']}.svg"))
            qr += 1

    # Collane: nome -> {numero del libro: (id, titolo)}
    collane = {}
    for voce in voci:
        sr = (voce.get("amazon") or {}).get("serie")
        if sr:
            collane.setdefault(sr["nome"], {})[sr["numero"]] = (voce["id"], voce.get("title", ""))

    for i, voce in enumerate(voci):
        html_pagina = costruisci_pagina(voce, i, voci, card_urls.get(voce["id"]), "../", collane)
        with open(os.path.join(PAGES_DIR, f"{voce['id']}.html"), "w", encoding="utf-8") as f:
            f.write(html_pagina)
        pagine += 1

    # La home: presentazione dell'archivio, con la sua anteprima social.
    crea_card_home(voci, os.path.join(CARDS_DIR, "home.jpg"))
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(costruisci_home(voci, collane, f"{BASE_URL}og/home.jpg"))

    aggiorna_versioni("catalogo.html")

    # Via le card di voci cancellate o rimaste senza immagine.
    attese = {f"{v['id']}.jpg" for v in voci if v.get("image")}
    for nome in list(manifest):
        if nome not in attese:
            del manifest[nome]
    rimosse = 0
    for nome in os.listdir(CARDS_DIR):
        if nome.endswith(".jpg") and nome not in attese and nome != "home.jpg":
            os.remove(os.path.join(CARDS_DIR, nome))
            rimosse += 1

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"{pagine} pagine scritte in v/ più index.html, {card} card in og/ "
          f"({rifatte} rifatte, {rimosse} rimosse), {qr} QR code in qr/")
    print(f"Indirizzo da condividere: {BASE_URL}v/<id>.html")


if __name__ == "__main__":
    main()
