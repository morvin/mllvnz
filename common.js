/*
 * Funzioni usate sia dall'archivio (script.js) sia dal catalogo (catalogo.js).
 */
const Archivio = (() => {

    // Palette di sfondi chiari: uno a caso ad ogni caricamento.
    const PALETTE = [
        '#ffffff', // Bianco
        '#f0f7ff', // Azzurro chiarissimo
        '#f2fff2', // Verde chiarissimo
        '#fffaf0', // Arancio chiarissimo
        '#fdf2ff', // Viola chiarissimo
        '#f5f5f5'  // Grigio chiarissimo
    ];

    const $ = (id) => document.getElementById(id);

    const setBackground = () => {
        const color = PALETTE[Math.floor(Math.random() * PALETTE.length)];
        document.body.style.backgroundColor = color;
        const themeColor = document.querySelector('meta[name="theme-color"]');
        if (themeColor) themeColor.content = color;
    };

    // "2026-01-05" va letto come data locale: new Date("2026-01-05") la
    // interpreta come UTC e in certi fusi mostrerebbe il giorno prima.
    const formatDate = (value) => {
        if (!value) return '';
        const parts = String(value).split('-').map(Number);
        const date = parts.length === 3 && parts.every(n => !isNaN(n))
            ? new Date(parts[0], parts[1] - 1, parts[2])
            : new Date(value);
        if (isNaN(date.getTime())) return '';
        return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' });
    };

    const setFooterYear = () => {
        const el = $('footer-year');
        if (el) el.textContent = new Date().getFullYear();
    };

    // Scarica data.json tenendo solo le voci utilizzabili.
    const loadData = () => fetch('data.json', { cache: 'no-cache' })
        .then(response => {
            if (!response.ok) throw new Error(`data.json: HTTP ${response.status}`);
            return response.json();
        })
        .then(raw => {
            if (!Array.isArray(raw)) throw new Error('data.json non contiene un elenco');
            const data = raw.filter(d => d && Number.isInteger(d.id) && (d.image || d.url));
            if (data.length === 0) throw new Error('Database vuoto');
            return data;
        });

    return { PALETTE, $, setBackground, formatDate, setFooterYear, loadData };
})();
