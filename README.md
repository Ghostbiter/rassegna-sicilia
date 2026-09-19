# Rassegna Sicilia
Rassegna stampa quotidiana delle notizie siciliane, divise per provincia e argomento.
- `bot.py` raccoglie le notizie (feed RSS delle testate + Google News) e salva `docs/data/AAAA-MM-GG.json`
- `docs/index.html` è il sito (GitHub Pages)
- `.github/workflows/aggiorna.yml` lancia il bot ogni 2 ore
