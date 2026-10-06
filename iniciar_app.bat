@echo off
title Libreria en Linea - Cliente de Escritorio
echo ============================================================
echo   Iniciando Cliente de Escritorio Python (Tkinter)...
echo ============================================================
cd /d "%~dp0apps\Python_app"
start "" "venv\Scripts\python.exe" main.py
echo Listo! La ventana debe aparecer en tu pantalla.
timeout /t 3 >nul
