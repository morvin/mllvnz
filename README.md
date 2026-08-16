# Il Mio Archivio

Sito statico pubblicato su GitHub Pages: <https://morvin.github.io/mllvnz/>

Un contenuto per pagina, sfogliabile con i pulsanti `Primo / Indietro / Casuale / Avanti / Ultimo`
(funzionano anche le frecce ← → della tastiera). La pagina si apre sulla prima voce;
`?p=ID` apre una voce precisa.

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
  "description": "Il testo che accompagna il libro."
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
| `index.html` | Struttura della pagina (una sola, i contenuti sono dinamici) |
| `style.css` | Grafica |
| `script.js` | Carica `data.json`, riempie la pagina e gestisce la navigazione |
| `data.json` | I contenuti dell'archivio |
| `image/` | Le immagini |

## Nota sulle anteprime social

Il titolo, la descrizione e l'immagine per le anteprime (Facebook, WhatsApp…)
vengono impostati via JavaScript. I "robot" che generano le anteprime spesso non
eseguono JavaScript: vedranno quindi sempre il titolo generico del sito, non quello
della singola voce. Per anteprime corrette voce per voce servirebbe generare una
pagina HTML separata per ogni contenuto.
