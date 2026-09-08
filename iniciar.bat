@echo off
title Capa Cero - Estudio de Preproduccion
color 0B

echo =======================================================
echo   CAPA CERO - ESTUDIO DE PREPRODUCCION YOUTUBE
echo   Optimizacion: AMD 9950X3D + NVIDIA RTX 4090
echo =======================================================
echo.

cd /d "%~dp0"

REM 1. Verificar si existe el entorno virtual aislado
if not exist ".venv" (
    echo [1/3] Creando entorno virtual aislado .venv...
    python -m venv .venv
    echo [2/3] Instalando dependencias necesarias...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

REM 2. Redirigir variables de entorno a IAsModels para evitar basura en el disco C:
set "HF_HOME=%~dp0IAsModels\LLMs"
set "TORCH_HOME=%~dp0IAsModels\Complementos"

echo [3/3] Iniciando servidor local en http://127.0.0.1:8000 ...
echo.
echo Presiona Ctrl+C para cerrar el estudio en cualquier momento.
echo.

REM Abrir automaticamente el navegador en localhost seguro
start http://127.0.0.1:8000

REM Arrancar FastAPI / Uvicorn con entorno virtual directo
.venv\Scripts\python.exe main.py

pause

