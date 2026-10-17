@echo off
REM Kripto Risk Terminali: her 15m mum kapanisinda raporu yeniler ve panoyu acar
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m btc_tahmin izle --dakika 15 --ac %*
pause
