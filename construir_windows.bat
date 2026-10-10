@echo off
REM Crea RendiPlus.exe (funciona sin tener Python instalado).
REM Se arma como carpeta y no como un solo archivo: asi abre mucho mas rapido.
cd /d "%~dp0"
echo Instalando lo necesario...
py -m pip install -r requirements.txt pyinstaller
echo.
echo Creando RendiPlus.exe (puede tardar un par de minutos)...
py -m PyInstaller --noconfirm --onedir --windowed --name RendiPlus ^
  --icon recursos\icono.ico --add-data "recursos;recursos" ^
  --collect-data customtkinter --hidden-import pystray._win32 app.py
echo.
echo Listo: abre dist\RendiPlus\RendiPlus.exe (copia la carpeta dist\RendiPlus completa)
pause
