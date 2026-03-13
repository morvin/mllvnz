document.addEventListener('DOMContentLoaded', () => {
    const btnRandom = document.getElementById('btn-random');

    if (btnRandom) {
        btnRandom.addEventListener('click', () => {
            const totalPages = 5; 
            const randomPageNumber = Math.floor(Math.random() * totalPages) + 1;
            const randomUrl = `pagina${randomPageNumber}.html`;

            alert(`In una versione reale, il pulsante 'Casuale' ti porterebbe a: ${randomUrl}`);
        });
    }
});
