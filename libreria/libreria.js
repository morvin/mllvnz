/* La Libreria: carosello da sfogliare con atmosfere che cambiano col libro.
   Le particelle sono le stesse della scena per le dirette (STREAM_LAB/public/libreria.js).
   Indirizzo diretto a un libro: libreria/#<id> apre la sua scheda. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var root = document.documentElement;
  var tutti = [], libri = [], corrente = 0, carte = [], filtro = null, show = null;
  var ferme = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ================= Atmosfere =================
  var cv = $('atmo'), cx = cv.getContext('2d'), W = 0, H = 0;
  var particelle = [], tema = 'bokeh', extra = null, colori = ['#2b2540', '#4b3b6e', '#a77bd0'];
  function misura() { W = cv.width = innerWidth; H = cv.height = innerHeight; }
  addEventListener('resize', function () { misura(); posiziona(); }); misura();
  var rnd = function (a, b) { return a + Math.random() * (b - a); };
  var scegli = function (a) { return a[Math.floor(Math.random() * a.length)]; };
  var BASE = { oro: 90, stelle: 160, neve: 140, foglie: 55, petali: 60, bolle: 70, note: 34, cuori: 30, coriandoli: 90, bokeh: 26, polvere: 120, aerei: 4, lettere: 24 };
  var quanti = function (t) { return Math.round(BASE[t] * Math.min(1, W * H / (1920 * 1080)) + 4); };
  function temaDi(b) {
    var t = b.titolo.toLowerCase();
    if (/inverno|natale|neve|winter/.test(t)) return 'neve';
    if (/autunno|autumn|fall/.test(t)) return 'foglie';
    if (/primavera|spring|giardin|fiori/.test(t)) return 'petali';
    if (/ocean|mare|estate|summer|birra|vino|beer/.test(t)) return 'bolle';
    if (/astronom|spazio|stell|cosmo/.test(t)) return 'stelle';
    return ({ 'Miti e classici': 'oro', 'Scienza': 'stelle', 'Luoghi e viaggi': 'aerei', 'Storia e nostalgia': 'polvere', 'Cinema': 'polvere',
      'Cucina e vino': 'bolle', 'Musica': 'note', 'Coppia': 'cuori', 'Feste': 'coriandoli', 'Sport': 'coriandoli', 'Natura e stagioni': 'foglie' })[b.categoria] || 'bokeh';
  }
  function nuova(tipo, dentro) {
    var p = { tipo: tipo, x: rnd(0, W), y: dentro ? rnd(0, H) : 0, vx: 0, vy: 0, s: 1, r: rnd(0, 6.28), vr: rnd(-.02, .02), a: 0, amax: 1, f: rnd(0, 6.28) };
    switch (tipo) {
      case 'oro': p.s = rnd(1.5, 4); p.vy = rnd(-.5, -.15); p.vx = rnd(-.15, .15); p.amax = rnd(.4, .95); if (!dentro) p.y = H + 10; break;
      case 'stelle': p.s = rnd(.6, 2.2); p.vx = -rnd(.02, .12); p.amax = rnd(.3, 1); break;
      case 'neve': p.s = rnd(1.5, 4.5); p.vy = rnd(.4, 1.3); p.amax = rnd(.5, .95); if (!dentro) p.y = -10; break;
      case 'foglie': case 'petali': p.s = rnd(8, 18); p.vy = rnd(.5, 1.2); p.vx = rnd(-.4, .6); p.amax = rnd(.6, .95);
        p.col = tipo === 'foglie' ? scegli(['#d9682b', '#b8441b', '#e3a33b', '#9c3d17', '#c98a2a']) : scegli(['#ffc2d6', '#ffe3ec', '#ffffff', '#f7a8c4']);
        if (!dentro) p.y = -30; break;
      case 'bolle': p.s = rnd(4, 16); p.vy = rnd(-1, -.35); p.amax = rnd(.25, .6); if (!dentro) p.y = H + 30; break;
      case 'note': p.s = rnd(24, 46); p.vy = rnd(-.7, -.3); p.vx = rnd(-.2, .2); p.ch = scegli(['♪', '♫', '♩', '♬']); p.amax = rnd(.25, .5); if (!dentro) p.y = H + 50; break;
      case 'cuori': p.s = rnd(12, 28); p.vy = rnd(-.8, -.3); p.amax = rnd(.3, .6); p.col = scegli(['#ff5c8a', '#ff8fb1', '#ffc2d6']); if (!dentro) p.y = H + 40; break;
      case 'coriandoli': p.s = rnd(6, 13); p.vy = rnd(1, 2.4); p.vx = rnd(-.6, .6); p.vr = rnd(-.15, .15); p.amax = .9;
        p.col = scegli(['#ffb020', '#36bffa', '#12b76a', '#ff5c8a', '#8b5cf6', '#ffffff']); if (!dentro) p.y = -20; break;
      case 'bokeh': p.s = rnd(50, 170); p.vx = rnd(-.25, .25); p.vy = rnd(-.2, .2); p.amax = rnd(.08, .2); p.col = scegli(colori); break;
      case 'polvere': p.s = rnd(.6, 2); p.vx = rnd(-.3, .3); p.vy = rnd(-.3, .3); p.amax = rnd(.2, .7); break;
      case 'aerei': p.s = rnd(26, 40); p.vx = rnd(1.1, 2); p.vy = rnd(-.3, .2); p.x = dentro ? rnd(0, W) : -60; p.y = rnd(100, H - 200); p.scia = []; p.amax = .7; break;
      case 'lettere': p.s = rnd(28, 64); p.vy = rnd(.25, .65); p.ch = String.fromCharCode(65 + Math.floor(Math.random() * 26)); p.amax = rnd(.05, .14); if (!dentro) p.y = -60; break;
    }
    return p;
  }
  function cuore(x, y, s) {
    cx.beginPath(); cx.moveTo(x, y + s * .3);
    cx.bezierCurveTo(x, y - s * .2, x - s, y - s * .2, x - s, y + s * .3); cx.bezierCurveTo(x - s, y + s * .8, x, y + s, x, y + s * 1.3);
    cx.bezierCurveTo(x, y + s, x + s, y + s * .8, x + s, y + s * .3); cx.bezierCurveTo(x + s, y - s * .2, x, y - s * .2, x, y + s * .3); cx.fill();
  }
  function disegna(p, t) {
    cx.globalAlpha = p.a;
    switch (p.tipo) {
      case 'oro': case 'polvere': {
        var tw = p.tipo === 'oro' ? .6 + .4 * Math.sin(t * .003 + p.f) : 1;
        var g = cx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.s * 4);
        g.addColorStop(0, p.tipo === 'oro' ? 'rgba(255,214,130,' + tw + ')' : 'rgba(255,240,220,.9)'); g.addColorStop(1, 'rgba(255,200,120,0)');
        cx.fillStyle = g; cx.beginPath(); cx.arc(p.x, p.y, p.s * 4, 0, 6.29); cx.fill(); break;
      }
      case 'stelle': cx.globalAlpha = p.a * (.55 + .45 * Math.sin(t * .002 + p.f)); cx.fillStyle = '#fff'; cx.beginPath(); cx.arc(p.x, p.y, p.s, 0, 6.29); cx.fill(); break;
      case 'neve': cx.fillStyle = '#fff'; cx.beginPath(); cx.arc(p.x, p.y, p.s, 0, 6.29); cx.fill(); break;
      case 'foglie': case 'petali':
        cx.save(); cx.translate(p.x, p.y); cx.rotate(p.r); cx.scale(1, .45 + .35 * Math.sin(t * .002 + p.f));
        cx.fillStyle = p.col; cx.beginPath(); cx.ellipse(0, 0, p.s, p.s * (p.tipo === 'foglie' ? .5 : .7), 0, 0, 6.29); cx.fill(); cx.restore(); break;
      case 'bolle':
        cx.strokeStyle = 'rgba(255,255,255,.8)'; cx.lineWidth = 1.5; cx.beginPath(); cx.arc(p.x, p.y, p.s, 0, 6.29); cx.stroke(); break;
      case 'note': case 'lettere':
        cx.save(); cx.translate(p.x, p.y); cx.rotate(p.tipo === 'note' ? Math.sin(t * .001 + p.f) * .3 : 0);
        cx.fillStyle = '#fff'; cx.font = '800 ' + p.s + 'px Fraunces, serif'; cx.textAlign = 'center'; cx.fillText(p.ch, 0, 0); cx.restore(); break;
      case 'cuori': cx.fillStyle = p.col; cuore(p.x, p.y, p.s * .5); break;
      case 'coriandoli': cx.save(); cx.translate(p.x, p.y); cx.rotate(p.r); cx.fillStyle = p.col; cx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2 * Math.abs(Math.cos(t * .004 + p.f)) + 1); cx.restore(); break;
      case 'bokeh': {
        var gb = cx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.s); gb.addColorStop(0, p.col); gb.addColorStop(1, 'rgba(0,0,0,0)');
        cx.fillStyle = gb; cx.beginPath(); cx.arc(p.x, p.y, p.s, 0, 6.29); cx.fill(); break;
      }
      case 'aerei':
        cx.strokeStyle = 'rgba(255,255,255,.5)'; cx.setLineDash([6, 10]); cx.lineWidth = 2; cx.beginPath();
        p.scia.forEach(function (q, i) { if (i) cx.lineTo(q[0], q[1]); else cx.moveTo(q[0], q[1]); }); cx.stroke(); cx.setLineDash([]);
        cx.save(); cx.translate(p.x, p.y); cx.rotate(Math.atan2(p.vy, p.vx)); cx.fillStyle = '#fff'; cx.font = p.s + 'px sans-serif'; cx.textAlign = 'center'; cx.textBaseline = 'middle';
        cx.fillText('✈', 0, 0); cx.restore(); break;
    }
  }
  function muovi(p, t) {
    if (p.tipo === 'neve' || p.tipo === 'foglie' || p.tipo === 'petali') p.x += Math.sin(t * .001 + p.f) * .6;
    p.x += p.vx; p.y += p.vy; p.r += p.vr;
    if (p.tipo === 'aerei') { p.scia.push([p.x, p.y]); if (p.scia.length > 120) p.scia.shift(); }
    p.a = p.muore ? Math.max(0, p.a - .015) : Math.min(p.amax, p.a + .01);
    if (p.x < -250 || p.x > W + 250 || p.y < -250 || p.y > H + 250) { if (p.tipo === 'stelle') p.x = W + 5; else p.morta = true; }
    if (p.muore && p.a <= 0) p.morta = true;
  }
  function cambiaTema(nuovo, secondario) {
    particelle.forEach(function (p) { if (p.tipo !== nuovo && p.tipo !== secondario) p.muore = true; });
    tema = nuovo; extra = secondario;
    var ci = particelle.filter(function (p) { return p.tipo === nuovo && !p.muore; }).length;
    for (var i = ci; i < quanti(nuovo); i++) particelle.push(nuova(nuovo, true));
  }
  function anima(t) {
    cx.clearRect(0, 0, W, H);
    cx.globalCompositeOperation = (tema === 'bokeh' || tema === 'oro') ? 'lighter' : 'source-over';
    [tema, extra].forEach(function (tp) {
      if (!tp) return;
      var vive = particelle.filter(function (p) { return p.tipo === tp && !p.muore; }).length;
      if (vive < (tp === extra ? quanti(tp) * .7 : quanti(tp)) && Math.random() < .3) particelle.push(nuova(tp, tp === 'stelle' || tp === 'bokeh' || tp === 'polvere'));
    });
    particelle.forEach(function (p) { muovi(p, t); disegna(p, t); });
    particelle = particelle.filter(function (p) { return !p.morta; });
    cx.globalAlpha = 1; cx.globalCompositeOperation = 'source-over';
    requestAnimationFrame(anima);
  }

  // ================= Colori e sfondo =================
  var strati = document.querySelectorAll('#sfondo .strato'), sv = 0, tAtmo;
  function atmosfera(b) {
    clearTimeout(tAtmo);
    // Si aspetta che il carosello si fermi, per non cambiare scena a ogni passaggio
    tAtmo = setTimeout(function () {
      colori = b.colori && b.colori.length ? b.colori.slice() : colori;
      root.style.setProperty('--c1', colori[0]); root.style.setProperty('--c2', colori[1] || colori[0]);
      root.style.setProperty('--c3', 'color-mix(in srgb, ' + (colori[2] || colori[0]) + ' 55%, #fff)');
      sv = 1 - sv;
      strati[sv].style.backgroundImage = 'url("' + (b.aplus[0] || b.copertina) + '")';
      strati[sv].classList.add('on'); strati[1 - sv].classList.remove('on');
      if (!ferme) cambiaTema(temaDi(b), /parole|word|crucipuzzle|ricerca|search/i.test(b.titolo) ? 'lettere' : null);
    }, 450);
  }

  // ================= Carosello =================
  function costruisci() {
    var anello = $('anello');
    anello.innerHTML = ''; carte = [];
    libri.forEach(function (b, i) {
      var d = document.createElement('div'); d.className = 'libro'; d.setAttribute('role', 'option');
      var img = new Image(); img.src = b.copertina; img.alt = b.titolo; img.decoding = 'async'; img.loading = Math.abs(i - corrente) < 8 ? 'eager' : 'lazy';
      d.appendChild(img); anello.appendChild(d); carte.push(d);
      d.addEventListener('click', function () {
        if (spostato) return;
        if (i === corrente) apri(b); else vai(i);
      });
    });
  }
  // Altezza delle copertine: il contenitore è alto 1,25 volte una copertina (vedi --h nel CSS)
  function altezza() { return $('anello').clientHeight / 1.25 || 400; }
  function posiziona() {
    var n = libri.length; if (!n) return;
    var h = altezza();
    var lati = innerWidth < 760 ? 3 : 5;
    carte.forEach(function (d, i) {
      var o = ((i - corrente) % n + n) % n; if (o > n / 2) o -= n;
      o += trascinato;
      var a = Math.abs(o), s = Math.sign(o);
      d.classList.toggle('centro', i === corrente && !trascinato);
      d.classList.toggle('nascosto', a > lati + 1);
      d.setAttribute('aria-selected', i === corrente);
      d.style.zIndex = 100 - Math.round(a);
      d.style.transition = a > lati + 1 ? 'none' : '';
      if (a < .01) d.style.transform = 'translateX(-50%) translateZ(' + (h * .3) + 'px)';
      else {
        var x = s * (h * .72 * Math.min(1, a) + Math.max(0, a - 1) * h * .36);
        d.style.transform = 'translateX(calc(-50% + ' + x + 'px)) translateZ(' + (-a * h * .28) + 'px) rotateY(' + (-s * Math.min(1, a) * 50) + 'deg)';
      }
      d.style.opacity = a <= lati ? 1 - a * (.6 / lati) : 0;
      d.style.filter = 'brightness(' + (1 - Math.min(a, lati) * .1) + ')';
    });
    var b = libri[corrente];
    $('dCat').textContent = b.categoria;
    $('dTitolo').textContent = b.titolo;
  }
  function vai(i) {
    if (!libri.length) return;
    corrente = (i % libri.length + libri.length) % libri.length;
    posiziona(); atmosfera(libri[corrente]);
  }

  // Trascinamento col dito o col mouse: la ruota segue, al rilascio si ferma sul libro più vicino
  var inizioX = null, trascinato = 0, spostato = false;
  var anelloEl = $('anello');
  anelloEl.addEventListener('pointerdown', function (e) { inizioX = e.clientX; spostato = false; });
  addEventListener('pointermove', function (e) {
    if (inizioX === null) return;
    var dx = e.clientX - inizioX, h = altezza();
    if (Math.abs(dx) > 8) { spostato = true; anelloEl.classList.add('trascina'); }
    if (spostato) { trascinato = dx / (h * .45); posiziona(); }
  });
  addEventListener('pointerup', function () {
    if (inizioX === null) return;
    inizioX = null; anelloEl.classList.remove('trascina');
    if (spostato) { var passi = Math.round(trascinato); trascinato = 0; vai(corrente - passi); setTimeout(function () { spostato = false; }, 50); }
  });
  var tRuota = 0;
  anelloEl.addEventListener('wheel', function (e) {
    var d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (Math.abs(d) < 8) return;
    e.preventDefault();
    if (Date.now() - tRuota < 220) return;
    tRuota = Date.now(); vai(corrente + (d > 0 ? 1 : -1));
  }, { passive: false });

  // ================= Filtri per categoria =================
  function filtri() {
    var conta = {};
    tutti.forEach(function (b) { conta[b.categoria] = (conta[b.categoria] || 0) + 1; });
    var voci = [[null, 'Tutti', tutti.length]].concat(Object.keys(conta).sort(function (a, b) { return conta[b] - conta[a]; }).map(function (c) { return [c, c, conta[c]]; }));
    $('filtri').innerHTML = voci.map(function (v) {
      return '<button type="button" data-cat="' + (v[0] || '') + '" aria-pressed="' + (v[0] === filtro) + '">' + v[1] + ' <small>' + v[2] + '</small></button>';
    }).join('');
    $('filtri').querySelectorAll('button').forEach(function (bt) {
      bt.addEventListener('click', function () {
        filtro = bt.dataset.cat || null;
        var attuale = libri[corrente];
        libri = filtro ? tutti.filter(function (b) { return b.categoria === filtro; }) : tutti.slice();
        corrente = Math.max(0, libri.indexOf(attuale));
        $('filtri').querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === bt); });
        costruisci(); posiziona(); atmosfera(libri[corrente]);
      });
    });
  }

  // ================= Scheda =================
  var aperto = null, gi = 0;
  function apri(b) {
    aperto = b; gi = 0;
    fermaShow();
    $('sCop').src = b.copertina; $('sCop').alt = 'Copertina di ' + b.titolo;
    $('sCat').textContent = b.categoria; $('sTitolo').textContent = b.titolo; $('sFrase').textContent = b.frase || '';
    var tipo = { 'Parole intrecciate': '🧩 Parole intrecciate', 'Diari e taccuini': '📓 Diario e taccuino', 'Libro': '📖 Libro', 'Sudoku': '🔢 Sudoku' }[b.tipo] || b.tipo;
    $('sDati').innerHTML = [tipo, b.pagine ? '📄 ' + b.pagine + ' pagine' : '', b.formato ? '📘 ' + b.formato : ''].filter(Boolean).map(function (x) { return '<span>' + x + '</span>'; }).join('');
    $('sAmazon').href = b.url; $('sAmazon').hidden = !b.url;
    $('sVoce').href = '../v/' + b.id + '.html';
    $('galleria').hidden = !b.aplus.length;
    $('gPunti').innerHTML = b.aplus.map(function (_, i) { return '<i data-i="' + i + '"></i>'; }).join('');
    $('gPunti').querySelectorAll('i').forEach(function (p) { p.addEventListener('click', function () { immagine(+p.dataset.i); }); });
    immagine(0);
    $('scheda').hidden = false;
    document.body.style.overflow = 'hidden';
    history.replaceState(null, '', '#' + b.id);
    $('scheda').querySelector('.chiudi').focus();
  }
  function immagine(i) {
    if (!aperto || !aperto.aplus.length) return;
    gi = (i + aperto.aplus.length) % aperto.aplus.length;
    var img = $('gImg');
    img.classList.add('cambia');
    setTimeout(function () { img.src = aperto.aplus[gi]; img.alt = 'Immagine ' + (gi + 1) + ' dall\'interno di ' + aperto.titolo; img.classList.remove('cambia'); }, 180);
    $('gPunti').querySelectorAll('i').forEach(function (p, k) { p.classList.toggle('on', k === gi); });
  }
  function chiudi() {
    $('scheda').hidden = true; aperto = null; document.body.style.overflow = '';
    history.replaceState(null, '', location.pathname);
    $('btnApri').focus();
  }
  document.querySelectorAll('[data-chiudi]').forEach(function (el) { el.addEventListener('click', chiudi); });
  document.querySelector('.g-prec').addEventListener('click', function () { immagine(gi - 1); });
  document.querySelector('.g-succ').addEventListener('click', function () { immagine(gi + 1); });
  $('btnApri').addEventListener('click', function () { apri(libri[corrente]); });
  $('sCopia').addEventListener('click', function () {
    var link = location.origin + location.pathname + '#' + aperto.id;
    var bt = $('sCopia');
    (navigator.clipboard ? navigator.clipboard.writeText(link) : Promise.reject()).then(function () { bt.textContent = '✅ Copiato'; }, function () { prompt('Copia il link:', link); })
      .then(function () { setTimeout(function () { bt.textContent = '🔗 Copia il link'; }, 1800); });
  });

  // ================= Presentazione e caso =================
  function fermaShow() { clearInterval(show); show = null; $('btnShow').setAttribute('aria-pressed', 'false'); $('btnShow').textContent = '▶ Presentazione'; }
  $('btnShow').addEventListener('click', function () {
    if (show) return fermaShow();
    show = setInterval(function () { vai(corrente + 1); }, 6000);
    $('btnShow').setAttribute('aria-pressed', 'true'); $('btnShow').textContent = '⏸ Ferma';
    vai(corrente + 1);
  });
  $('btnCaso').addEventListener('click', function () {
    var altro = corrente;
    while (libri.length > 1 && altro === corrente) altro = Math.floor(Math.random() * libri.length);
    vai(altro);
  });

  addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT') return;
    if (aperto) {
      if (e.key === 'Escape') chiudi();
      else if (e.key === 'ArrowRight') immagine(gi + 1);
      else if (e.key === 'ArrowLeft') immagine(gi - 1);
      return;
    }
    if (e.key === 'ArrowRight') { fermaShow(); vai(corrente + 1); }
    else if (e.key === 'ArrowLeft') { fermaShow(); vai(corrente - 1); }
    else if (e.key === 'Enter' && e.target === document.body) apri(libri[corrente]);
  });

  // ================= Avvio =================
  fetch('libri.json').then(function (r) { return r.json(); }).then(function (d) {
    tutti = d; libri = d.slice();
    $('conta').textContent = d.length + ' libri';
    var dalLink = libri.findIndex(function (b) { return '#' + b.id === location.hash; });
    corrente = dalLink >= 0 ? dalLink : Math.floor(Math.random() * libri.length);
    filtri(); costruisci(); posiziona(); atmosfera(libri[corrente]);
    if (!ferme) requestAnimationFrame(anima);
    if (dalLink >= 0) setTimeout(function () { apri(libri[corrente]); }, 600);
  });
})();
