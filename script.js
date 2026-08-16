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

            // 2. Metadati (descrizione, canonical, anteprima social)
            const pageUrl = absoluteUrl(`?p=${item.id}`);
            const meta = {
                'meta-desc': description,
                'og-title': title,
                'og-desc': description,
                'og-url': pageUrl
            };
            Object.entries(meta).forEach(([id, value]) => {
                const el = $(id);
                if (el) el.content = value;
            });
            const canonical = $('canonical');
            if (canonical) canonical.href = pageUrl;

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
