#!/usr/bin/env bash
#
# Copia il portale Divinazioni dal suo progetto (~/1PROGETTI/tarot) dentro
# divinazioni/, cosi' e' servito anche su morvinlab.com/mllvnz/divinazioni/.
#
# Il sorgente resta uno solo: si modifica in ~/1PROGETTI/tarot e poi si
# rilancia questo script. Cambia solo PAGE_URL (l'indirizzo usato nei link di
# condivisione), che li' punta a morvin.github.io/tarot.
#
# Uso:   tools/sync-divinazioni.sh

set -euo pipefail

cd "$(dirname "$0")/.."

SRC="$HOME/1PROGETTI/tarot"
DEST=divinazioni
BASE=https://morvinlab.com/mllvnz/divinazioni
FILES=(index.html tarot.html rune.html smorfia.html smorfia-90.html)

mkdir -p "$DEST"
for f in "${FILES[@]}"; do
  [ -f "$SRC/$f" ] || { echo "manca $SRC/$f — sincronizzazione annullata"; exit 1; }
  sed "s#https://morvin.github.io/tarot/#$BASE/#g" "$SRC/$f" > "$DEST/$f"
done

if grep -q "morvin.github.io/tarot" "$DEST"/*.html; then
  echo "attenzione: restano link a morvin.github.io/tarot"; grep -n "morvin.github.io/tarot" "$DEST"/*.html
fi
echo "copiati ${#FILES[@]} file in $DEST/"
