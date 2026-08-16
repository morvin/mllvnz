# Il Mio Archivio

Sito statico pubblicato su GitHub Pages: <https://morvin.github.io/mllvnz/>

Due pagine:

- **Archivio** (`index.html`): un contenuto per pagina, sfogliabile con i pulsanti
  `Primo / Indietro / Casuale / Avanti / Ultimo` (funzionano anche le frecce ← →
  della tastiera). Si apre sulla voce più vecchia; `?p=ID` apre una voce precisa.
- **Catalogo** (`catalogo.html`): tutte le voci insieme, raggruppate per categoria,
  con filtri per categoria, tipo e lingua. I filtri finiscono nell'indirizzo
  (`catalogo.html?categoria=Miti e classici&lingua=it`), quindi una selezione si
  può salvare tra i preferiti o mandare a qualcuno.

## Come aggiungere una voce

Tutti i contenuti stanno in [`data.json`](data.json): un elenco di oggetti, mostrati
nell'ordine in cui compaiono nel file. Per aggiungere una voce basta accodare un oggetto.

**Voce con immagine** (metti prima il file dentro `image/`):

```json
{
  "id": 10,
  "title": "Titolo della voce",
  "date": "2026-03-01",
  "image": "image/10.png",
  "alt": "Cosa si vede nell'immagine, per chi non può vederla",
  "caption": "Titoletto del riquadro di testo",
  "description": "Il testo che accompagna il contenuto."
}
```

**Voce con immagine cliccabile** (è il caso dei libri: si vede la copertina e
cliccandoci si apre la scheda su Amazon):

```json
{
  "id": 12,
  "title": "Titolo del libro",
  "date": "2026-04-17",
  "image": "image/copertina.jpg",
  "url": "https://www.amazon.it/dp/ASIN",
  "alt": "Cosa si vede in copertina",
  "caption": "Apri la scheda su Amazon",
  "description": "Il testo che accompagna il libro.",
  "publisher": "La Quercia Edizioni",
  "lang": "it",
  "type": "Parole intrecciate",
  "category": "Miti e classici"
}
```

Le copertine si scaricano dall'ASIN con:
`https://m.media-amazon.com/images/P/ASIN.01._SCLZZZZZZZ_.jpg`
(conviene salvarle dentro `image/`, così il sito non dipende da Amazon).

**Voce con solo link:**

```json
{
  "id": 11,
  "title": "Titolo della voce",
  "date": "2026-03-05",
  "url": "https://esempio.it/pagina",
  "caption": "Titoletto del riquadro di testo",
  "description": "Il testo che accompagna il link."
}
```

Regole pratiche:

- `id` deve essere un numero intero **mai usato prima**: è l'indirizzo della voce
  (`?p=10`), quindi non va cambiato dopo che l'hai condivisa in giro.
- Ogni voce deve avere `image` **o** `url` (o entrambi). Le voci senza nessuno
  dei due vengono ignorate, così un errore di battitura non rompe tutto il sito.
- Con `image` + `url` si vede la copertina, cliccabile. Con il solo `url` si vede
  l'indirizzo nel riquadro tratteggiato.
- `date` va scritta come `AAAA-MM-GG` e viene mostrata in italiano ("1 marzo 2026").
- `alt` descrive l'immagine a chi usa uno screen reader: se manca viene usato il titolo.

I campi che riguardano solo il catalogo (`category`, `type`, `lang`, `publisher`)
si possono anche omettere: la voce finisce sotto "Varie" e resta comunque
sfogliabile nell'archivio. I valori usati finora:

- `category`: Miti e classici, Natura e stagioni, Luoghi e viaggi, Storia e nostalgia,
  Cucina e vino, Benessere, Scienza, Animali, Coppia, Musica, Feste, Varie
- `type`: Parole intrecciate, Diari e taccuini, Sudoku, Libro, Link
- `lang`: `it` oppure `en`

I filtri del catalogo si costruiscono da soli leggendo `data.json`: se inventi una
categoria nuova, il pulsante compare da solo, senza toccare il codice.

## Le pagine da condividere si rigenerano da sole

Quando su GitHub cambiano `data.json`, le immagini in `image/` o lo script,
la GitHub Action [`pagine.yml`](.github/workflows/pagine.yml) rilancia il
generatore e salva le pagine aggiornate nel repository. Non c'è niente da fare
a mano: dopo un paio di minuti il sito è allineato.

Per farlo comunque in locale (o per vedere il risultato prima di pubblicare):

```bash
python3 tools/build-pages.py
```

Serve Pillow (`pip3 install Pillow`). Le pagine in `v/` si riscrivono ogni
volta; le card in `og/` solo quando la copertina è davvero cambiata, così le
esecuzioni ripetute non sporcano il repository. Il controllo si basa su
`og/manifest.json`: cancellandolo, si rifanno tutte.

## Quale indirizzo condividere

Per mandare in giro un contenuto (Facebook, WhatsApp, messaggi) usa la pagina
statica della voce:

    https://morvin.github.io/mllvnz/v/7.html

È l'unica che fa comparire titolo, descrizione e copertina nell'anteprima:
i programmi che generano le anteprime non eseguono JavaScript, quindi devono
trovare tutto già scritto nell'HTML. `index.html?p=7` mostra lo stesso
contenuto ma nell'anteprima resta il titolo generico del sito.

Le copertine per le anteprime stanno in `og/<id>.jpg`: la copertina su una card
1200x630, la misura che Facebook mostra grande invece di ridurre a francobollo.

Se cambi l'indirizzo del sito, aggiorna `BASE_URL` in `tools/build-pages.py`
e rigenera: i tag delle anteprime hanno bisogno di indirizzi assoluti.

## Modifiche in locale

Serve un piccolo server web, perché il sito legge `data.json` via `fetch`
(aprendo `index.html` con doppio clic il browser lo blocca):

```bash
python3 -m http.server 8765
```

Poi apri <http://localhost:8765>.

## File

| File | A cosa serve |
| --- | --- |
| `index.html` | L'archivio: una voce per volta |
| `catalogo.html` | Il catalogo: tutte le voci per categoria, con i filtri |
| `style.css` | Grafica di entrambe le pagine |
| `common.js` | Funzioni comuni: sfondo casuale, date, caricamento di `data.json` |
| `script.js` | Logica dell'archivio (navigazione, metadati della voce) |
| `catalogo.js` | Logica del catalogo (filtri e griglia) |
| `data.json` | I contenuti |
| `image/` | Le copertine e le immagini |
| `v/` | Una pagina statica per voce, generata: è quella da condividere |
| `og/` | Le immagini 1200x630 per le anteprime social, generate |
| `tools/build-pages.py` | Genera `v/` e `og/` leggendo `data.json` |

## Se Facebook mostra ancora l'anteprima vecchia

Facebook tiene in memoria le anteprime già viste. Se hai cambiato titolo,
descrizione o copertina di una voce già condivisa, incolla l'indirizzo della
pagina nello Sharing Debugger di Facebook e premi "Scrape Again":
<https://developers.facebook.com/tools/debug/>
