/*
 * Il Mio Archivio - logica di navigazione.
 * I contenuti stanno tutti in data.json: per aggiungere una voce
 * basta aggiungere un oggetto a quel file (vedi README.md).
 */
document.addEventListener('DOMContentLoaded', () => {

    const { $, setBackground, formatDate, setFooterYear, loadData } = Archivio;

    const showError = (message) => {
        document.body.classList.remove('is-loading');
        $('post-title').textContent = message;
        // Senza dati non c'è niente da mostrare né da navigare.
        document.querySelectorAll('.post-nav, .content-media, .content-text')
            .forEach(el => el.remove());
    };

    const goTo = (id) => {
        window.location.search = `?p=${id}`;
    };

    const absoluteUrl = (path) => {
        try {
            return new URL(path, window.location.href).href;
        } catch (e) {
            return '';
        }
    };

    setBackground();
    setFooterYear();

    const LINGUE = { it: 'Italiano', en: 'Inglese', de: 'Tedesco' };
    const esc = (v) => String(v).replace(/[&<>"']/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

    // Descrizione completa, scheda tecnica, altri formati e QR code del libro.
    // Il markup è lo stesso che tools/build-pages.py scrive nelle pagine in v/.
    const renderAmazon = (item) => {
        const box = $('amazon-info');
        if (!box) return;
        const url = item.url || '';
        if (!url.includes('amazon.')) { box.hidden = true; return; }
        const a = item.amazon || {};
        const pezzi = [];

        const blocchi = (a.descrizione || []).map(b =>
            b.h ? `<h4>${esc(b.h)}</h4>` :
            b.p ? `<p>${esc(b.p)}</p>` :
            b.ul ? `<ul>${b.ul.map(v => `<li>${esc(v)}</li>`).join('')}</ul>` : '').join('');
        if (blocchi) pezzi.push(`<h3>Descrizione</h3><div class="amazon-desc">${blocchi}</div>`);

        const righe = [];
        const riga = (nome, valore) => { if (valore) righe.push(`<dt>${esc(nome)}</dt><dd>${valore}</dd>`); };
        riga('Autore', esc((a.autori || []).join(', ')));
        riga('Editore', esc(item.publisher || ''));
        riga('Formato', esc(a.formato || ''));
        riga('Lingua', esc(LINGUE[item.lang] || ''));
        riga('Pagine', esc(a.pagine || ''));
        riga('Dimensioni', esc(a.dimensioni || ''));
        riga('Peso', esc(a.peso || ''));
        riga('File', esc(a.file || ''));
        riga('ISBN-13', esc(a.isbn13 || ''));
        riga('ISBN-10', esc(a.isbn10 || ''));
        if (a.serie) riga('Collana', esc(`${a.serie.nome}, libro ${a.serie.numero} di ${a.serie.di}`));
        if (a.prezzo) {
            const quando = formatDate(a.aggiornato);
            riga('Prezzo', esc(a.prezzo) + (quando ? ` <span class="nota">al ${esc(quando)}</span>` : ''));
        }
        if (a.stelle) {
            const n = a.recensioni;
            const stelle = a.stelle.toFixed(1).replace('.', ',');
            riga('Valutazione', esc(`${stelle} su 5` + (n ? ` (${n} ${n === 1 ? 'recensione' : 'recensioni'})` : '')));
        }
        if (a.classifica) riga('Classifica', a.classifica.map(esc).join('<br>'));
        if (righe.length) pezzi.push(`<h3>Scheda del libro</h3><dl class="scheda">${righe.join('')}</dl>`);

        const base = url.split('/dp/')[0];
        const altri = (a.formati || []).filter(f => f.asin && !url.includes(f.asin));
        if (altri.length) {
            pezzi.push('<h3>Altri formati</h3><ul class="formati">' + altri.map(f =>
                `<li><a href="${esc(base)}/dp/${esc(f.asin)}" target="_blank" rel="noopener">${esc(f.formato)}</a>` +
                (f.prezzo ? ` <span class="nota">${esc(f.prezzo)}</span>` : '') + '</li>').join('') + '</ul>');
        }

        pezzi.push(`<div class="qr">
            <img src="qr/${item.id}.svg" alt="QR code della scheda Amazon" width="132" height="132">
            <p>Inquadra il codice con il telefono per aprire il libro su Amazon,
            oppure <a href="${esc(url)}" target="_blank" rel="noopener">apri la scheda</a>.</p>
        </div>`);
        box.innerHTML = pezzi.join('');
        box.hidden = false;
    };

    loadData()
        .then(data => {
            const total = data.length;

            // Quale voce mostrare: quella indicata da ?p=ID, altrimenti la prima.
            const pParam = new URLSearchParams(window.location.search).get('p');
            let currentIndex = pParam !== null
                ? data.findIndex(d => d.id === parseInt(pParam, 10))
                : 0;
            if (currentIndex === -1) currentIndex = 0; // id inesistente -> home

            const item = data[currentIndex];

            // 1. Testi della pagina
            const title = item.title || 'Senza titolo';
            const description = item.description || '';

            document.title = `Archivio - ${title}`;
            $('post-title').textContent = title;
            $('post-date').textContent = formatDate(item.date);
            $('content-caption').textContent = item.caption || 'Dettagli';
            $('post-desc').textContent = description;

            // 2. Metadati. L'indirizzo ufficiale della voce e' la pagina statica
            // in v/: e' quella con le anteprime social scritte nell'HTML.
            const staticUrl = absoluteUrl(`v/${item.id}.html`);
            const meta = {
                'meta-desc': description,
                'og-title': title,
                'og-desc': description,
                'og-url': staticUrl
            };
            Object.entries(meta).forEach(([id, value]) => {
                const el = $(id);
                if (el) el.content = value;
            });
            const canonical = $('canonical');
            if (canonical) canonical.href = staticUrl;

            const ogImage = $('og-image');
            const twCard = $('tw-card');
            if (item.image) {
                if (ogImage) ogImage.content = absoluteUrl(item.image);
                if (twCard) twCard.content = 'summary_large_image';
            } else if (ogImage) {
                ogImage.remove();
            }

            // 3. Contenuto: immagine (eventualmente cliccabile) oppure link in evidenza
            const imgElement = $('main-image');
            const imgLink = $('image-link');
            const linkElement = $('main-link');

            if (item.image) {
                linkElement.style.display = 'none';
                imgElement.alt = item.alt || title;
                imgElement.src = item.image;
                imgElement.hidden = false;
                imgElement.addEventListener('error', () => {
                    imgElement.hidden = true;
                    $('post-desc').textContent =
                        `Immagine non disponibile (${item.image}). ${description}`.trim();
                }, { once: true });

                // Se la voce ha anche un link, la copertina ci porta sopra.
                if (item.url) {
                    imgLink.href = item.url;
                    imgLink.setAttribute('aria-label', `${title}: apri il link`);
                } else {
                    imgLink.removeAttribute('href');
                }
            } else {
                imgElement.hidden = true;
                imgLink.removeAttribute('href');
                linkElement.style.display = 'block';
                linkElement.href = item.url;
                linkElement.textContent = item.url;
            }

            // 3b. Scheda Amazon (stessa sezione delle pagine statiche in v/)
            renderAmazon(item);

            // 4. Navigazione, calcolata sulla posizione nell'elenco
            const prevId = currentIndex > 0 ? data[currentIndex - 1].id : null;
            const nextId = currentIndex < total - 1 ? data[currentIndex + 1].id : null;

            const updateLinks = (className, newId) => {
                document.querySelectorAll(`.${className}`).forEach(el => {
                    if (newId === null) {
                        el.removeAttribute('href');
                        el.classList.add('disabled');
                        el.setAttribute('aria-disabled', 'true');
                    } else {
                        el.href = `?p=${newId}`;
                        el.classList.remove('disabled');
                        el.removeAttribute('aria-disabled');
                    }
                });
            };

            updateLinks('nav-first', currentIndex === 0 ? null : data[0].id);
            updateLinks('nav-prev', prevId);
            updateLinks('nav-next', nextId);
            updateLinks('nav-last', currentIndex === total - 1 ? null : data[total - 1].id);

            // I contenuti sono pronti: mostriamo la navigazione.
            document.body.classList.remove('is-loading');

            // 5. Pulsante Casuale (presente in entrambe le barre)
            document.querySelectorAll('.nav-random').forEach(btn => {
                btn.addEventListener('click', () => {
                    if (total === 1) return;
                    let randomIndex;
                    do {
                        randomIndex = Math.floor(Math.random() * total);
                    } while (randomIndex === currentIndex);
                    goTo(data[randomIndex].id);
                });
            });

            // 6. Frecce della tastiera, senza disturbare campi di testo e scorciatoie
            document.addEventListener('keydown', (e) => {
                if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
                const tag = (e.target.tagName || '').toLowerCase();
                if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
                if (e.key === 'ArrowLeft' && prevId !== null) goTo(prevId);
                if (e.key === 'ArrowRight' && nextId !== null) goTo(nextId);
            });

            // 7. Precarichiamo le immagini vicine: sfogliare diventa istantaneo.
            [currentIndex - 1, currentIndex + 1].forEach(i => {
                const neighbour = data[i];
                if (neighbour && neighbour.image) new Image().src = neighbour.image;
            });
        })
        .catch(error => {
            console.error('Errore nel caricamento dei dati:', error);
            showError('Errore nel caricamento del contenuto.');
        });
});
