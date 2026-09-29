# Rassegna Sicilia
Rassegna stampa quotidiana delle notizie siciliane, divise per provincia e argomento.
- `bot.py` raccoglie le notizie (feed RSS delle testate + Google News) e salva `docs/data/AAAA-MM-GG.json`
- `mondo.py` prepara una volta al giorno (al mattino) lo scenario internazionale: aree, temi, storie più riprese e parole in ascesa/in calo dalla stampa italiana ed estera, in `docs/data/mondo/`
- `docs/index.html` è il sito (GitHub Pages), con la sezione 🌍 Internazionale nel menù in alto
- `.github/workflows/aggiorna.yml` lancia il bot ogni ora
