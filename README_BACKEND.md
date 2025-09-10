# Mi Proyecto Backend - FastAPI

## Descripción
Backend API desarrollado con FastAPI para el sistema de gestión de portafolios de inversión.

## Instalación y Ejecución

### Configuración Local
1. Crear entorno virtual:
```bash
python -m venv venv
venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno en .env

4. Ejecutar servidor:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker-compose up --build
```

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
