document.addEventListener('DOMContentLoaded', () => {
    // 1. Recuperiamo i dati dal file JSON
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            if (!data || data.length === 0) throw new Error("Database vuoto");
            
            const total = data.length;
            
            // 2. Determiniamo quale ID mostrare (dall'URL ?p=X o l'ultimo disponibile)
            const urlParams = new URLSearchParams(window.location.search);
            const pParam = urlParams.get('p');
            
            // Se non c'è parametro p, mostriamo l'ultimo. Se c'è, lo cerchiamo.
            let currentIndex = pParam 
                ? data.findIndex(d => d.id === parseInt(pParam)) 
                : total - 1;

            // Fallback: se l'ID non esiste (es. ?p=999), vai all'ultimo
            if (currentIndex === -1) currentIndex = total - 1;
            
            const item = data[currentIndex];

            // Log di debug: ti permette di vedere nel terminale del browser cosa sta succedendo
            console.log(`Caricamento contenuto ID: ${item.id} (Posizione: ${currentIndex + 1} di ${total})`);
            
            // 3. Popoliamo la pagina con i dati
            document.title = `Archivio - ${item.title}`;
            const metaDesc = document.getElementById('meta-desc');
            if (metaDesc) metaDesc.content = item.description;

            document.getElementById('post-title').textContent = item.title;
            document.getElementById('post-date').textContent = item.date ? new Date(item.date).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }) : '';
            document.getElementById('content-caption').textContent = item.caption;
            document.getElementById('post-desc').textContent = item.description;

            // Cambiamo colore di sfondo in modo dinamico e accessibile
            const palette = [
                '#ffffff', // Bianco
                '#f0f7ff', // Azzurro chiarissimo
                '#f2fff2', // Verde chiarissimo
                '#fffaf0', // Arancio chiarissimo
                '#fdf2ff', // Viola chiarissimo
                '#f5f5f5'  // Grigio chiarissimo
            ];
            
            // Scegliamo un colore casuale dalla palette ad ogni caricamento della pagina
            const colorIndex = Math.floor(Math.random() * palette.length);
            document.body.style.backgroundColor = palette[colorIndex];
            
            // Rendiamo visibile la navigazione solo dopo il caricamento
            document.getElementById('nav-top').style.visibility = 'visible';

            const imgElement = document.getElementById('main-image');
            const linkElement = document.getElementById('main-link');

            if (item.url) {
                imgElement.style.display = 'none';
                linkElement.style.display = 'block';
                linkElement.href = item.url;
                linkElement.textContent = item.url;
            } else {
                imgElement.style.display = 'block';
                linkElement.style.display = 'none';
                imgElement.src = item.image;
                imgElement.alt = item.alt;
                imgElement.title = item.alt;
            }

            // 4. Gestiamo la navigazione basandoci sulla posizione nell'array
            const firstId = data[0].id;
            const lastId = data[total - 1].id;
            const prevId = currentIndex > 0 ? data[currentIndex - 1].id : null;
            const nextId = currentIndex < total - 1 ? data[currentIndex + 1].id : null;

            console.log(`Navigazione calcolata -> Precedente: ${prevId}, Successivo: ${nextId}`);

            // Funzione per aggiornare i link e gestire lo stato disabilitato (WCAG)
            const updateLinks = (className, newId, isDisabled) => {
                document.querySelectorAll(`.${className}`).forEach(el => {
                    if (isDisabled || newId === null) {
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

            updateLinks('nav-first', firstId, currentIndex === 0);
            updateLinks('nav-prev', prevId, currentIndex === 0);
            updateLinks('nav-next', nextId, currentIndex === total - 1);
            updateLinks('nav-last', lastId, currentIndex === total - 1);

            // Pulsante Casuale
            const btnRandom = document.getElementById('btn-random');
            if (btnRandom) {
                btnRandom.addEventListener('click', () => {
                    let randomId;
                    do {
                        randomId = data[Math.floor(Math.random() * total)].id;
                    } while (randomId === item.id && total > 1);
                    window.location.search = `?p=${randomId}`;
                });
            }
            
            // Bonus: Navigazione con le frecce della tastiera (Accessibilità+)
            document.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowLeft' && prevId !== null) window.location.search = `?p=${prevId}`;
                if (e.key === 'ArrowRight' && nextId !== null) window.location.search = `?p=${nextId}`;
            });
        })
        .catch(error => {
            console.error("Errore nel caricamento dei dati:", error);
            document.getElementById('post-title').textContent = "Errore nel caricamento del contenuto.";
        });
});
