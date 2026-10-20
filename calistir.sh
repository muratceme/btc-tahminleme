#!/usr/bin/env bash
# Kripto Risk Terminali: her 15m mumda yeniler, panoyu http://localhost:5055 adresinde yayınlar
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
python3 -m btc_tahmin canli --ac "$@"
