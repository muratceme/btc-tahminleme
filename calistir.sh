#!/usr/bin/env bash
# Kripto Risk Terminali: her 15m mum kapanışında raporu yeniler ve panoyu açar
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
python3 -m btc_tahmin izle --dakika 15 --ac "$@"
