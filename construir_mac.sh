#!/bin/bash
# Crea RendiPlus.app para Mac. Ejecútalo con:  bash construir_mac.sh
cd "$(dirname "$0")"
echo "Instalando lo necesario..."
python3 -m pip install -r requirements.txt pyinstaller pillow
echo
echo "Creando RendiPlus.app (puede tardar un par de minutos)..."
python3 -m PyInstaller --noconfirm --windowed --name RendiPlus \
  --icon recursos/icono.png --add-data "recursos:recursos" \
  --collect-data customtkinter app.py
echo
echo "Listo: tu programa quedó en dist/RendiPlus.app"
