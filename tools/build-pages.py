#!/usr/bin/env python3
"""
Genera una pagina statica per ogni voce di data.json, dentro la cartella v/.

Serve per le anteprime dei social: Facebook, WhatsApp e compagnia non eseguono
JavaScript, quindi titolo, descrizione e copertina devono stare gia' scritti
nell'HTML. Le pagine v/<id>.html hanno tutto dentro, e funzionano anche a
JavaScript spento.

Genera anche og/<id>.jpg: la copertina su una card 1200x630, la misura che
Facebook mostra grande invece di ridurre a francobollo.

Da rilanciare ogni volta che si modifica data.json:

    python3 tools/build-pages.py
"""
import html
import json
import os
import shutil
import sys
from PIL import Image, ImageFilter, ImageEnhance

BASE_URL = "https://morvin.github.io/mllvnz/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_DIR = os.path.join(ROOT, "v")
CARDS_DIR = os.path.join(ROOT, "og")

CARD_W, CARD_H = 1200, 630
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


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


def meta(prop, content, attr="property"):
    if not content:
        return ""
    return f'    <meta {attr}="{prop}" content="{html.escape(str(content), quote=True)}">\n'


def costruisci_pagina(voce, precedente, successiva, prima, ultima, ids, card_url):
    titolo = voce.get("title", "Senza titolo")
    descrizione = voce.get("description", "")
    url_voce = f"{BASE_URL}v/{voce['id']}.html"

    e = lambda s: html.escape(str(s), quote=True)

    testa = ""
    testa += meta("description", descrizione, attr="name")
    testa += meta("og:site_name", "Il Mio Archivio")
    testa += meta("og:type", "article")
    testa += meta("og:title", titolo)
    testa += meta("og:description", descrizione)
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
    testa += meta("twitter:description", descrizione, attr="name")

    # --- Navigazione: link statici alle altre pagine ---
    def bottone(classe, testo, target, etichetta):
        if target is None:
            return (f'<li><a class="nav-btn {classe} disabled" aria-disabled="true"'
                    f' aria-label="{e(etichetta)}">{testo}</a></li>')
        return (f'<li><a class="nav-btn {classe}" href="{target}.html"'
                f' aria-label="{e(etichetta)}">{testo}</a></li>')

    casuale = ids[0] if len(ids) == 1 else next(i for i in ids if i != voce["id"])

    def barra(nascosta=False):
        aria = ' aria-hidden="true"' if nascosta else ' aria-label="Navigazione contenuti"'
        return f"""            <nav class="post-nav"{aria}>
                <ul>
                    {bottone('nav-first', '|&lt; Primo', prima, 'Primo contenuto')}
                    {bottone('nav-prev', '&lt; Indietro', precedente, 'Contenuto precedente')}
                    <li><a class="nav-btn nav-random" href="{casuale}.html" aria-label="Contenuto casuale">Casuale</a></li>
                    {bottone('nav-next', 'Avanti &gt;', successiva, 'Contenuto successivo')}
                    {bottone('nav-last', 'Ultimo &gt;|', ultima, 'Ultimo contenuto')}
                </ul>
            </nav>"""

    # --- Contenuto: copertina cliccabile, immagine sola o link in evidenza ---
    if voce.get("image"):
        alt = e(voce.get("alt") or titolo)
        img = f'<img src="../{e(voce["image"])}" alt="{alt}" decoding="async">'
        if voce.get("url"):
            media = (f'<a class="image-link" href="{e(voce["url"])}" target="_blank"'
                     f' rel="noopener" aria-label="{e(titolo)}: apri il link">{img}</a>')
        else:
            media = f'<span class="image-link">{img}</span>'
    else:
        media = (f'<a class="big-link" style="display:block" href="{e(voce["url"])}"'
                 f' target="_blank" rel="noopener">{e(voce["url"])}</a>')

    return f"""<!DOCTYPE html>
<html lang="{e(voce.get('lang', 'it'))}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(titolo)} - Il Mio Archivio</title>
{testa}    <meta name="theme-color" content="#ffffff">
    <link rel="canonical" href="{url_voce}">
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' fill='%23fff'/%3E%3Crect x='2.5' y='2.5' width='11' height='11' fill='none' stroke='%23111' stroke-width='1.5'/%3E%3C/svg%3E">
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <a href="#main-content" class="skip-link">Salta al contenuto principale</a>

    <header class="site-header">
        <h1><a href="../">Il Mio Archivio</a></h1>
        <p>Un posto per collezionare le mie cose.</p>
        <p class="site-nav"><a href="../catalogo.html">Vedi tutto il catalogo</a></p>
    </header>

    <main id="main-content" class="container">
        <article class="content-post">
            <h2 id="post-title">{e(titolo)}</h2>
            <p class="post-date">{e(data_italiana(voce.get('date')))}</p>

{barra()}

            <div class="content-media">
                {media}
            </div>

{barra(nascosta=True)}

            <div class="content-text">
                <h3>{e(voce.get('caption') or 'Dettagli')}</h3>
                <p>{e(descrizione)}</p>
            </div>
        </article>
    </main>

    <footer class="site-footer">
        <p>&copy; <span id="footer-year">2026</span> Il Mio Archivio.</p>
    </footer>

    <script src="../common.js"></script>
    <script>
        // Sfondo casuale e anno del footer, come nel resto del sito.
        Archivio.setBackground();
        Archivio.setFooterYear();
        // Senza JavaScript "Casuale" porta comunque a un'altra voce;
        // con JavaScript ne sceglie una diversa ad ogni clic.
        var VOCI = {json.dumps(ids)};
        document.querySelectorAll('.nav-random').forEach(function (btn) {{
            btn.addEventListener('click', function (ev) {{
                ev.preventDefault();
                var altre = VOCI.filter(function (i) {{ return i !== {voce['id']}; }});
                if (!altre.length) return;
                window.location.href = altre[Math.floor(Math.random() * altre.length)] + '.html';
            }});
        }});
    </script>
</body>
</html>
"""


def main():
    with open(os.path.join(ROOT, "data.json"), encoding="utf-8") as f:
        data = json.load(f)

    voci = [d for d in data if isinstance(d.get("id"), int) and (d.get("image") or d.get("url"))]
    if not voci:
        sys.exit("data.json non contiene voci utilizzabili")

    # Ripartiamo da zero: le pagine di voci cancellate non devono sopravvivere.
    for cartella in (PAGES_DIR, CARDS_DIR):
        shutil.rmtree(cartella, ignore_errors=True)
        os.makedirs(cartella)

    ids = [v["id"] for v in voci]
    pagine = card = 0

    for i, voce in enumerate(voci):
        card_url = None
        if voce.get("image"):
            sorgente = os.path.join(ROOT, voce["image"])
            if os.path.exists(sorgente):
                nome = f"{voce['id']}.jpg"
                crea_card(sorgente, os.path.join(CARDS_DIR, nome))
                card_url = f"{BASE_URL}og/{nome}"
                card += 1
            else:
                print(f"  ! immagine mancante: {voce['image']} (voce {voce['id']})")

        pagina = costruisci_pagina(
            voce,
            precedente=ids[i - 1] if i > 0 else None,
            successiva=ids[i + 1] if i < len(voci) - 1 else None,
            prima=ids[0] if i > 0 else None,
            ultima=ids[-1] if i < len(voci) - 1 else None,
            ids=ids,
            card_url=card_url,
        )
        with open(os.path.join(PAGES_DIR, f"{voce['id']}.html"), "w", encoding="utf-8") as f:
            f.write(pagina)
        pagine += 1

    print(f"{pagine} pagine scritte in v/ e {card} card in og/")
    print(f"Indirizzo da condividere: {BASE_URL}v/<id>.html")


if __name__ == "__main__":
    main()
