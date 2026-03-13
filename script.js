document.addEventListener('DOMContentLoaded', () => {
    // 1. Recuperiamo i dati dal file JSON
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
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
            
            // 3. Popoliamo la pagina con i dati
            document.title = `Archivio - ${item.title}`;
            document.getElementById('post-title').textContent = item.title;
            document.getElementById('content-caption').textContent = item.caption;
            document.getElementById('post-desc').textContent = item.description;
            
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
            const prevId = currentIndex > 0 ? data[currentIndex - 1].id : firstId;
            const nextId = currentIndex < total - 1 ? data[currentIndex + 1].id : lastId;

            // Funzione per aggiornare tutti i link della navigazione (top e bottom)
            const updateLinks = (className, newId) => {
                document.querySelectorAll(`.${className}`).forEach(el => {
                    el.href = `?p=${newId}`;
                });
            };

            updateLinks('nav-first', firstId);
            updateLinks('nav-prev', prevId);
            updateLinks('nav-next', nextId);
            updateLinks('nav-last', lastId);

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
                if (e.key === 'ArrowLeft') window.location.search = `?p=${prevId}`;
                if (e.key === 'ArrowRight') window.location.search = `?p=${nextId}`;
            });
        });
});
