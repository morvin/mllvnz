#!/usr/bin/env python3
"""
Legge dalla scheda Amazon di ogni voce tutto quello che serve alla pagina:
descrizione completa, scheda tecnica, formati, prezzo, classifica e recensioni.
Il risultato va nel campo "amazon" di ogni voce in data.json.

    python3 tools/amazon.py            # tutte le voci con un link Amazon
    python3 tools/amazon.py B0GXKGRKB4 # solo questi ASIN

Le schede vengono lette con calma (qualche secondo tra una e l'altra) per non
farsi bloccare. Se Amazon risponde con un captcha la voce viene saltata e
tenuta com'era.
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

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
# Lingua e valuta per dominio. Il cookie serve solo ad amazon.com, che senza
# mostra i prezzi in euro; su amazon.it lo stesso cookie fa arrivare una pagina
# ridotta, senza scheda tecnica.
DOMINI = {
    "amazon.it": ("it-IT,it;q=0.9", ""),
    "amazon.com": ("en-US,en;q=0.9", "i18n-prefs=USD; lc-main=en_US"),
    "amazon.de": ("en-GB,en;q=0.9", ""),
}
FORMATI = {
    "paperback": "Copertina flessibile", "copertina flessibile": "Copertina flessibile",
    "hardcover": "Copertina rigida", "copertina rigida": "Copertina rigida",
    "kindle": "eBook Kindle", "kindle edition": "eBook Kindle", "formato kindle": "eBook Kindle",
}
# Frasi promozionali da non riportare nella descrizione
PROMO = re.compile(r"^(scorri verso l'alto|scroll up|clicca su|click .*buy|acquista ora|buy now)", re.I)


def contesto_ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def scarica(url):
    dominio = re.search(r"(amazon\.\w+)", url).group(1)
    lingua, cookie = DOMINI.get(dominio, DOMINI["amazon.it"])
    intestazioni = {"User-Agent": UA, "Accept-Language": lingua,
                    "Accept": "text/html,application/xhtml+xml"}
    if cookie:
        intestazioni["Cookie"] = cookie
    req = urllib.request.Request(url, headers=intestazioni)
    with urllib.request.urlopen(req, timeout=30, context=contesto_ssl()) as r:
        return r.read().decode("utf-8", "replace")


def testo(frammento):
    s = re.sub(r"<br\s*/?>", "\n", frammento)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s).replace("‎", "").replace("‏", "")
    return re.sub(r"[ \t\r\f\v\xa0]+", " ", s).strip()


def blocco(h, ident, lunghezza=20000):
    i = h.find(f'id="{ident}"')
    return h[i:i + lunghezza] if i >= 0 else ""


def paragrafo(t):
    """Un paragrafo con righe "- voce" diventa testo + elenco."""
    righe = [r.strip() for r in t.split("\n") if r.strip()]
    trattini = [r for r in righe if re.match(r"^[-•–]\s", r)]
    if len(trattini) < 2:
        return [{"p": " ".join(righe)}]
    out, voci = [], []
    for r in righe:
        if re.match(r"^[-•–]\s", r):
            voci.append(r[2:].strip())
        else:
            if voci:
                out.append({"ul": voci}); voci = []
            out.append({"p": r})
    if voci:
        out.append({"ul": voci})
    return out


def descrizione(h):
    b = blocco(h, "bookDescription_feature_div")
    m = re.search(r'a-expander-content[^>]*>([\s\S]*?)</div>', b)
    if not m:
        return []
    out = []
    pezzi = re.split(r"(<(?:ul|ol)[^>]*>[\s\S]*?</(?:ul|ol)>)", m.group(1))
    for pezzo in pezzi:
        if re.match(r"<(ul|ol)", pezzo):
            voci = [testo(li) for li in re.findall(r"<li[^>]*>([\s\S]*?)</li>", pezzo)]
            voci = [re.sub(r"\s+", " ", v) for v in voci if v]
            if voci:
                out.append({"ul": voci})
            continue
        # Paragrafi: <p>, due <br> di fila, oppure un titoletto in grassetto isolato
        for parte in re.split(r"</?p[^>]*>|<br\s*/?>\s*(?:</span>\s*<span[^>]*>\s*)?<br\s*/?>|<h\d[^>]*>|</h\d>", pezzo):
            t = testo(parte)
            if not t or PROMO.match(t):
                continue
            senza_bold = re.sub(r'<span class="a-text-bold">[\s\S]*?</span>', "", parte)
            if not testo(senza_bold) and len(t) < 160:
                out.append({"h": re.sub(r"\s+", " ", t)})
            else:
                out.extend(paragrafo(t))
    return out


def pollici(v):
    return f"{float(v) * 2.54:.1f}".replace(".", ",")


def dimensioni(v):
    nums = re.findall(r"[\d.,]+", v)
    if "inch" in v.lower():
        nums = [pollici(n) for n in nums]
    else:
        nums = [f"{float(n.replace(',', '.')):.1f}".replace(".", ",") for n in nums]
    return " × ".join(nums) + " cm" if nums else v


def peso(v):
    n = re.search(r"[\d.,]+", v)
    if not n:
        return v
    x = float(n.group(0).replace(",", "."))
    if "ounce" in v.lower():
        x *= 28.35
    elif "pound" in v.lower():
        x *= 453.6
    elif "kg" in v.lower():
        x *= 1000
    return f"{round(x)} g"


def scheda(h):
    b = blocco(h, "detailBullets_feature_div", 15000)
    righe = re.findall(r'<span class="a-text-bold">([\s\S]*?)</span>\s*(?:<a[^>]*>\s*)?<span[^>]*>([\s\S]*?)</span>', b)
    out = {}
    for k, v in righe:
        k = re.sub(r"\s+", " ", testo(k)).strip(" :").lower()
        v = re.sub(r"\s+", " ", testo(v))
        if not v:
            continue
        if k in ("lunghezza stampa", "print length"):
            n = re.search(r"\d+", v)
            if n:
                out["pagine"] = int(n.group(0))
        elif k in ("isbn-13", "isbn-10"):
            out[k.replace("-", "")] = v
        elif k in ("dimensioni", "dimensions"):
            out["dimensioni"] = dimensioni(v)
        elif k in ("peso articolo", "item weight"):
            out["peso"] = peso(v)
        elif k in ("dimensioni file", "file size"):
            out["file"] = v
        elif re.match(r"^(libro|book) \d+ (di|of) \d+$", k):
            n = re.findall(r"\d+", k)
            out["serie"] = {"nome": v, "numero": int(n[0]), "di": int(n[1])}
    # Classifica: righe "n. 1.504.555 in Libri" / "#1,234,567 in Books"
    c = re.search(r"(Posizione nella classifica Bestseller di Amazon|Best Sellers Rank)([\s\S]*?)</ul>", b)
    if c:
        t = re.sub(r"\(\s*(Visualizza|See) [^)]*\)", "", testo(re.sub(r"<li", "\n<li", c.group(2))))
        posti = [re.sub(r"\s+", " ", r).strip(" :") for r in re.split(r"\n|(?=(?:n\.|#)\s?[\d.,]+ in )", t)]
        posti = [p for p in posti if re.match(r"^(n\.|#)\s?[\d.,]+ in ", p)]
        if posti:
            out["classifica"] = posti
    return out


def normalizza_prezzo(t):
    """'EUR 12.50', '$14.00', '13,99 €' -> '12,50 €', '14,00 $', '13,99 €'"""
    t = t.replace("\xa0", " ").strip()
    n = re.search(r"\d[\d.,]*", t)
    if not n:
        return None
    num = n.group(0)
    parti = re.match(r"^([\d.,]*?)(?:[.,](\d{2}))?$", num)
    intero = re.sub(r"[.,]", "", parti.group(1)) or "0"
    dec = parti.group(2)
    valuta = "$" if ("$" in t or "USD" in t) else "£" if "£" in t else "€"
    return f"{intero},{dec or '00'} {valuta}"


def prezzo_principale(h):
    i = h.find("apex-pricetopay-value")
    if i < 0:
        return None
    b = h[i:i + 1500]
    w = re.search(r'a-price-whole">([\d.,]+)', b)
    f = re.search(r'a-price-fraction">(\d+)', b)
    sym = re.search(r'a-price-symbol">([^<]+)', b)
    if not w:
        return None
    return normalizza_prezzo(f"{sym.group(1) if sym else ''}{w.group(1).rstrip('.,')}.{f.group(1) if f else '00'}")


def formati(h, asin):
    out = []
    for m in re.finditer(r'id="tmm-grid-swatch-(\w+)"([\s\S]*?)(?=id="tmm-grid-swatch-|id="tmmSwatches_feature_div_end|</ul>)', h):
        corpo = m.group(2)
        nome = testo(re.search(r"<span[^>]*>([\s\S]*?)</span>", corpo).group(1)) if re.search(r"<span", corpo) else m.group(1)
        nome = FORMATI.get(nome.lower(), nome)
        link = re.search(r'href="[^"]*?/dp/([A-Z0-9]{10})', corpo)
        a = link.group(1) if link else asin
        prezzi = re.findall(r"(?:€|EUR|\$|USD)\s?[\d.,]+|[\d.,]+\s?€", testo(corpo))
        prezzi = [p for p in prezzi if not re.match(r"^(€|\$|EUR)?\s?0[.,]00", p.strip())]
        out.append({"formato": nome, "asin": a, **({"prezzo": normalizza_prezzo(prezzi[0])} if prezzi else {})})
    # Un formato solo (quello della pagina) non aggiunge niente
    return out if len(out) > 1 else []


def autori(h):
    b = blocco(h, "bylineInfo", 3000)
    nomi = re.findall(r'<a[^>]*class="a-link-normal"[^>]*>([^<]+)</a>', b)
    nomi = [testo(n) for n in nomi]
    return [n for n in dict.fromkeys(nomi)
            if n and not re.match(r"(Visita|Visit|Scopri|Search|Ricerca|Learn|Book \d|Libro \d|Band \d)", n)]


def recensioni(h):
    out = {}
    m = re.search(r'id="acrPopover"[^>]*title="([\d.,]+)', h)
    if m:
        out["stelle"] = float(m.group(1).replace(",", "."))
    m = re.search(r'id="acrCustomerReviewText"[^>]*>([^<]+)<', h)
    if m:
        n = re.sub(r"\D", "", m.group(1))
        if n:
            out["recensioni"] = int(n)
    return out


def leggi(url, asin, tentativi=3):
    # Amazon a volte risponde con una versione ridotta della pagina, senza la
    # scheda tecnica: in quel caso si riprova dopo una pausa.
    for n in range(tentativi):
        h = scarica(url)
        completa = 'id="productTitle"' in h and "a-text-bold" in blocco(h, "detailBullets_feature_div", 15000)
        if completa or n == tentativi - 1:
            break
        time.sleep(random.uniform(8, 15))
    if "captcha" in h.lower() and "productTitle" not in h:
        raise RuntimeError("captcha")
    if 'id="productTitle"' not in h or len(h) < 100_000:
        raise RuntimeError(f"pagina ridotta ({len(h)} byte), riprovare più tardi")
    titolo = testo(re.search(r'id="productTitle"[^>]*>([\s\S]*?)</span>', h).group(1))
    dati = {"titolo": titolo}
    a = autori(h)
    if a:
        dati["autori"] = a
    f = re.search(r'id="bylineInfo"[\s\S]{0,3000}?(?:Formato|Format):\s*</span>\s*<span>([^<]+)<', h)
    if f:
        dati["formato"] = FORMATI.get(testo(f.group(1)).lower(), testo(f.group(1)))
    p = prezzo_principale(h)
    if p:
        dati["prezzo"] = p
    dati.update(scheda(h))
    dati.update(recensioni(h))
    fo = formati(h, asin)
    if fo:
        dati["formati"] = fo
    d = descrizione(h)
    if d:
        dati["descrizione"] = d
    dati["aggiornato"] = date.today().isoformat()
    return dati


def main():
    with open(DATA, encoding="utf-8") as f:
        voci = json.load(f)
    solo = set(sys.argv[1:])
    fatte = errori = 0
    for voce in voci:
        m = re.search(r"(https://www\.amazon\.\w+)/dp/([A-Z0-9]{10})", voce.get("url", ""))
        if not m or (solo and m.group(2) not in solo):
            continue
        asin = m.group(2)
        try:
            nuovi = leggi(m.group(0), asin)
            # Quello che questa volta manca si tiene dalla lettura precedente
            voce["amazon"] = {**(voce.get("amazon") or {}), **nuovi}
            fatte += 1
            a = voce["amazon"]
            print(f"  ok  {asin}  {a.get('pagine', '-')} pag  {a.get('prezzo', '-')}  "
                  f"{len(a.get('descrizione', []))} blocchi  {voce['title'][:40]}")
        except Exception as ex:
            errori += 1
            print(f"  !!  {asin}  {ex}  {voce['title'][:40]}")
        # salva dopo ogni voce: se si interrompe non si perde niente
        with open(DATA, "w", encoding="utf-8") as f:
            json.dump(voci, f, ensure_ascii=False, indent=2)
            f.write("\n")
        time.sleep(random.uniform(3, 6))
    print(f"{fatte} schede lette, {errori} errori")


if __name__ == "__main__":
    main()
