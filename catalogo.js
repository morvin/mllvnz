/*
 * Catalogo: mostra tutte le voci di data.json raggruppate per categoria,
 * con filtri per categoria, tipo e lingua. I filtri restano nell'indirizzo
 * (?categoria=...&tipo=...&lingua=...) così una selezione si può condividere.
 */
document.addEventListener('DOMContentLoaded', () => {

    const { $, setBackground, formatDate, setFooterYear, loadData } = Archivio;

    const LANG_NAMES = { it: 'Italiano', en: 'English' };
    const TUTTI = '__tutti__';

    // Chiave del filtro nell'indirizzo -> campo della voce in data.json
    const FILTERS = [
        { param: 'categoria', field: 'category', listId: 'filter-category', all: 'Tutte' },
        { param: 'tipo', field: 'type', listId: 'filter-type', all: 'Tutti' },
        { param: 'lingua', field: 'lang', listId: 'filter-lang', all: 'Tutte' }
    ];

    setBackground();
    setFooterYear();

    const label = (field, value) =>
        field === 'lang' ? (LANG_NAMES[value] || value) : value;

    loadData()
        .then(data => {
            // Le voci senza categoria finiscono in fondo, sotto "Varie".
            const entries = data.map(d => ({
                ...d,
                category: d.category || 'Varie',
                type: d.type || 'Varie',
                lang: d.lang || 'it'
            }));

            // Ordine delle categorie: prima quelle con più voci.
            const orderOf = (field) => {
                const counts = new Map();
                entries.forEach(e => counts.set(e[field], (counts.get(e[field]) || 0) + 1));
                return [...counts.entries()]
                    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'it'));
            };

            const params = new URLSearchParams(window.location.search);
            const selected = {};
            FILTERS.forEach(f => { selected[f.param] = params.get(f.param) || TUTTI; });

            // --- Costruzione dei pulsanti di filtro ---
            FILTERS.forEach(f => {
                const list = $(f.listId);
                const values = orderOf(f.field);
                const items = [[TUTTI, entries.length, f.all]]
                    .concat(values.map(([v, n]) => [v, n, label(f.field, v)]));

                items.forEach(([value, count, text]) => {
                    const li = document.createElement('li');
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'nav-btn filter-btn';
                    btn.textContent = `${text} (${count})`;
                    btn.dataset.value = value;
                    btn.dataset.param = f.param;
                    btn.addEventListener('click', () => {
                        selected[f.param] = selected[f.param] === value ? TUTTI : value;
                        render();
                        updateUrl();
                    });
                    li.appendChild(btn);
                    list.appendChild(li);
                });
            });

            const updateUrl = () => {
                const next = new URLSearchParams();
                FILTERS.forEach(f => {
                    if (selected[f.param] !== TUTTI) next.set(f.param, selected[f.param]);
                });
                const query = next.toString();
                history.replaceState(null, '', query ? `?${query}` : window.location.pathname);
            };

            const matches = (entry) =>
                FILTERS.every(f => selected[f.param] === TUTTI || entry[f.field] === selected[f.param]);

            // --- Disegno della griglia ---
            const catalog = $('catalog');

            const buildCard = (entry) => {
                const card = document.createElement('a');
                card.className = 'card';
                // Rimandiamo alla pagina statica della voce: e' quella con le
                // anteprime social gia' scritte nell'HTML, quindi e' l'indirizzo
                // giusto da condividere.
                card.href = `v/${entry.id}.html`;

                if (entry.image) {
                    const img = document.createElement('img');
                    img.src = entry.image;
                    img.alt = entry.alt || `Copertina di ${entry.title}`;
                    img.loading = 'lazy';
                    img.decoding = 'async';
                    card.appendChild(img);
                } else {
                    const placeholder = document.createElement('span');
                    placeholder.className = 'card-placeholder';
                    placeholder.textContent = 'Link';
                    card.appendChild(placeholder);
                }

                const title = document.createElement('span');
                title.className = 'card-title';
                title.textContent = entry.title;
                card.appendChild(title);

                const date = document.createElement('span');
                date.className = 'card-date';
                date.textContent = formatDate(entry.date);
                card.appendChild(date);

                return card;
            };

            const render = () => {
                catalog.textContent = '';
                const visible = entries.filter(matches);

                document.querySelectorAll('.filter-btn').forEach(btn => {
                    const isActive = selected[btn.dataset.param] === btn.dataset.value;
                    btn.classList.toggle('active', isActive);
                    btn.setAttribute('aria-pressed', String(isActive));
                });

                $('catalog-status').textContent = visible.length === entries.length
                    ? ''
                    : `${visible.length} ${visible.length === 1 ? 'voce trovata' : 'voci trovate'} su ${entries.length}.`;

                if (visible.length === 0) {
                    const empty = document.createElement('p');
                    empty.className = 'catalog-empty';
                    empty.textContent = 'Nessuna voce con questi filtri.';
                    catalog.appendChild(empty);
                    return;
                }

                // Raggruppiamo per categoria, dalla più ricca alla più povera,
                // e all'interno dalla voce più recente alla più vecchia.
                const groups = new Map();
                visible.forEach(e => {
                    if (!groups.has(e.category)) groups.set(e.category, []);
                    groups.get(e.category).push(e);
                });

                [...groups.entries()]
                    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0], 'it'))
                    .forEach(([category, items]) => {
                        const section = document.createElement('section');
                        section.className = 'cat-section';

                        const heading = document.createElement('h3');
                        heading.className = 'cat-heading';
                        heading.textContent = `${category} (${items.length})`;
                        section.appendChild(heading);

                        const grid = document.createElement('div');
                        grid.className = 'grid';
                        items
                            .slice()
                            .sort((a, b) => (b.date || '').localeCompare(a.date || '') || b.id - a.id)
                            .forEach(e => grid.appendChild(buildCard(e)));

                        section.appendChild(grid);
                        catalog.appendChild(section);
                    });
            };

            $('catalog-count').textContent =
                `${entries.length} voci in ${new Set(entries.map(e => e.category)).size} categorie.`;

            render();
            document.body.classList.remove('is-loading');
        })
        .catch(error => {
            console.error('Errore nel caricamento dei dati:', error);
            document.body.classList.remove('is-loading');
            $('catalog-title').textContent = 'Errore nel caricamento del catalogo.';
            $('filters').remove();
        });
});
