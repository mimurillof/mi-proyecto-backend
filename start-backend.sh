#!/bin/bash
echo "Iniciando Mi Proyecto Backend - FastAPI"
echo "====================================="

echo "Activando entorno virtual..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Instalando dependencias..."
    pip install -r requirements.txt
fi

echo "Iniciando servidor FastAPI..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
