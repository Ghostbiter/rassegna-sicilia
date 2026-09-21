#!/bin/zsh
# Aggiorna la rassegna dal Mac e pubblica online.
# Avviato ogni ora da ~/Library/LaunchAgents/com.rassegnasicilia.aggiorna.plist
set -u
CARTELLA="/Users/marcellopardo/Downloads/musica/sicilia_news"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$CARTELLA" || exit 1

echo "===== $(date '+%d/%m %H:%M') ====="

# se non c'è rete, non ha senso continuare
ping -c1 -t5 github.com >/dev/null 2>&1 || { echo "niente rete, salto"; exit 0; }

# allineo la copia locale (i JSON generati possono divergere: tengo quelli remoti)
git fetch -q origin main
git rebase -q origin/main 2>/dev/null || {
  git checkout --theirs docs/data/*.json 2>/dev/null
  git add docs/data 2>/dev/null
  GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || git rebase --abort
}

/usr/bin/python3 bot.py || { echo "bot fallito"; exit 1; }

git add docs/data
if git diff --cached --quiet; then
  echo "nessuna notizia nuova"
else
  git commit -qm "Rassegna $(date '+%F %H:%M') (dal Mac)"
  git push -q origin main && echo "pubblicato online" || echo "push non riuscito"
fi
