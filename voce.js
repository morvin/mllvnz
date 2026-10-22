/*
 * Comodità delle pagine delle voci: la pagina funziona anche senza.
 * I dati arrivano da window.VOCE, scritto da tools/build-pages.py.
 */
(function () {
    var V = window.VOCE;
    if (!V) return;

    var msg = document.querySelector('.share-msg');
    var avvisa = function (testo) {
        if (!msg) return;
        msg.textContent = testo;
        clearTimeout(avvisa.t);
        avvisa.t = setTimeout(function () { msg.textContent = ''; }, 6000);
    };

    var copia = function (testo, conferma) {
        var fatto = function () { avvisa(conferma); };
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(testo).then(fatto, function () { avvisa(testo); });
        } else {
            avvisa(testo);
        }
    };

    // Casuale: ogni clic sceglie una voce diversa da quella aperta.
    document.querySelectorAll('[data-azione="casuale"]').forEach(function (a) {
        a.addEventListener('click', function (ev) {
            var altre = V.voci.filter(function (i) { return i !== V.id; });
            if (!altre.length) return;
            ev.preventDefault();
            location.href = V.base + altre[Math.floor(Math.random() * altre.length)] + '.html';
        });
    });

    // Frecce della tastiera, senza disturbare campi di testo e scorciatoie.
    document.addEventListener('keydown', function (ev) {
        if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
        var tag = (ev.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || ev.target.isContentEditable) return;
        if (ev.key === 'ArrowLeft' && V.prec) location.href = V.prec;
        if (ev.key === 'ArrowRight' && V.succ) location.href = V.succ;
    });

    // Menu di condivisione del telefono, quando c'è.
    var sistema = document.querySelector('[data-azione="sistema"]');
    if (sistema && navigator.share) {
        sistema.hidden = false;
        sistema.addEventListener('click', function () {
            navigator.share({ title: V.titolo, url: V.url }).catch(function () {});
        });
    }

    // Instagram non accetta link dal web: sul telefono gli passiamo la
    // copertina come immagine, altrimenti copiamo il link per lo sticker.
    var insta = document.querySelector('[data-azione="instagram"]');
    if (insta) {
        insta.addEventListener('click', function () {
            var ripiego = function () {
                copia(V.url, 'Link copiato. Su Instagram aprilo in una storia con lo sticker "Link".');
            };
            if (!V.immagine || !navigator.canShare) return ripiego();
            fetch(V.immagine)
                .then(function (r) { return r.blob(); })
                .then(function (blob) {
                    var file = new File([blob], 'copertina.jpg', { type: blob.type || 'image/jpeg' });
                    if (!navigator.canShare({ files: [file] })) return ripiego();
                    copia(V.url, 'Link copiato: incollalo nella storia con lo sticker "Link".');
                    return navigator.share({ files: [file], title: V.titolo, text: V.titolo + ' ' + V.url });
                })
                .catch(function (err) { if (!err || err.name !== 'AbortError') ripiego(); });
        });
    }

    var copiaLink = document.querySelector('[data-azione="copia"]');
    if (copiaLink) {
        copiaLink.addEventListener('click', function () { copia(V.url, 'Link copiato'); });
    }
})();
