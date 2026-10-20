@echo off
REM Kripto Risk Terminali: her 15m mumda yeniler, pano: http://localhost:5055 (telefondan da acilir)
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m btc_tahmin canli --ac %*
pause
