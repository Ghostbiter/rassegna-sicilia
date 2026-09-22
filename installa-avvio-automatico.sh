#!/bin/zsh
# Installa (o reinstalla) l'aggiornamento automatico orario sul Mac.
# Da lanciare dal Terminale: ./installa-avvio-automatico.sh
#
# Perche' serve: macOS non esegue script che stanno su un disco esterno,
# quindi la copia che lavora viene messa sul disco interno, in
# ~/Library/Application Support/rassegna-sicilia/.
set -u
SORGENTE="$(cd "$(dirname "$0")" && pwd)/aggiorna-locale.sh"
DEST_DIR="$HOME/Library/Application Support/rassegna-sicilia"
DEST="$DEST_DIR/aggiorna.sh"
PLIST="$HOME/Library/LaunchAgents/com.rassegnasicilia.aggiorna.plist"

mkdir -p "$DEST_DIR"
cp "$SORGENTE" "$DEST"
chmod +x "$DEST"
xattr -c "$DEST" 2>/dev/null

cat > "$PLIST" <<PLISTFINE
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.rassegnasicilia.aggiorna</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$DEST</string>
  </array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/rassegna-sicilia.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/rassegna-sicilia.log</string>
</dict>
</plist>
PLISTFINE

launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "avvio automatico installato: ogni ora"
echo "copia attiva: $DEST"
echo "per provarlo subito:  launchctl start com.rassegnasicilia.aggiorna"
echo "per vedere il diario: tail -f ~/Library/Logs/rassegna-sicilia.log"
