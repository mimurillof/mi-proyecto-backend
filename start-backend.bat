@echo off
echo Iniciando Mi Proyecto Backend - FastAPI
echo =====================================

echo Activando entorno virtual...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Instalando dependencias...
    pip install -r requirements.txt
)

echo Iniciando servidor FastAPI...
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
