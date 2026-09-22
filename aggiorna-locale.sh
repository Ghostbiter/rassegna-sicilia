#!/bin/zsh
# Aggiorna la rassegna dal Mac e pubblica online. Ogni ora, avviato da
# ~/Library/LaunchAgents/com.rassegnasicilia.aggiorna.plist
#
# IMPORTANTE: lavora su una copia propria, sul disco interno, perché macOS
# vieta ai lavori automatici di leggere i dischi esterni. La copia si tiene
# allineata da sola con GitHub, quindi resta identica a questa cartella.
# Dopo aver modificato questo file, reinstalla con ./installa-avvio-automatico.sh
set -u
REPO="$HOME/Library/Application Support/rassegna-sicilia/repo"
ORIGINE="https://github.com/Ghostbiter/rassegna-sicilia.git"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

echo "===== $(date '+%d/%m %H:%M') ====="

# senza rete non si fa nulla: ci penserà GitHub
ping -c1 -t5 github.com >/dev/null 2>&1 || { echo "niente rete, salto"; exit 0; }

# prima volta: mi creo la copia di lavoro
if [ ! -d "$REPO/.git" ]; then
  echo "creo la copia di lavoro sul disco interno..."
  mkdir -p "$(dirname "$REPO")"
  git clone -q "$ORIGINE" "$REPO" || { echo "clone fallito"; exit 1; }
fi
cd "$REPO" || exit 1

# mi allineo a quello che c'è online (compreso quello che ha fatto GitHub)
if ! git pull --rebase --autostash -q origin main 2>/dev/null; then
  echo "conflitto sui dati: tengo la versione online"
  git checkout --theirs docs/data/*.json 2>/dev/null
  git add docs/data 2>/dev/null
  GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1
fi

/usr/bin/python3 bot.py || { echo "bot fallito"; exit 1; }

git add docs/data
if git diff --cached --quiet; then
  echo "nessuna notizia nuova"
else
  git commit -qm "Rassegna $(date '+%F %H:%M') (dal Mac)"
  git push -q origin main && echo "pubblicato online" || echo "push non riuscito"
fi
