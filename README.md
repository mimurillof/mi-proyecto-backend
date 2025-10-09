# Mi Proyecto - Backend FastAPI

Este es el backend de la aplicación de finanzas con IA, desarrollado con FastAPI y PostgreSQL.

## 🚀 Características

- **FastAPI**: Framework moderno y rápido para APIs
- **SQLAlchemy 2.0**: ORM asíncrono para PostgreSQL
- **Pydantic**: Validación automática de datos
- **JWT Authentication**: Autenticación segura con tokens
- **Async/Await**: Arquitectura completamente asíncrona
- **CORS**: Configurado para el frontend React

## 📋 Prerequisitos

- Python 3.11+
- PostgreSQL 12+
- pip (gestor de paquetes de Python)

## 🛠️ Instalación

1. **Crear entorno virtual:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**
```bash
# Copiar el archivo de ejemplo
copy .env.example .env
# Editar .env con tus configuraciones
```

4. **Configurar base de datos:**
```bash
# Crear la base de datos PostgreSQL
createdb mi_proyecto_db

# Inicializar las tablas
python init_db.py
```

## 🚦 Ejecución

### Desarrollo
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Usando el script de inicio
```bash
python run_server.py
```

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - Registrar nuevo usuario
- `POST /api/auth/login` - Iniciar sesión
- `GET /api/auth/me` - Obtener usuario actual

### Users
- `GET /api/users/{user_id}/profile` - Obtener perfil de usuario
- `PUT /api/users/{user_id}/profile` - Actualizar perfil
- `GET /api/users/{user_id}/notifications` - Obtener configuración de notificaciones
- `PUT /api/users/{user_id}/notifications` - Actualizar notificaciones

### Health Check
- `GET /` - Estado del servidor
- `GET /api/health` - Health check detallado

## 🧪 Testing

Para probar la API:

1. **Swagger UI**: http://localhost:8000/docs
2. **ReDoc**: http://localhost:8000/redoc
3. **Health Check**: http://localhost:8000/api/health

## 🔄 Migración Completada

✅ **Migración desde Node.js completada exitosamente**

Esta implementación reemplaza completamente el backend anterior de Node.js/Express con:

- ✅ Validación automática con Pydantic
- ✅ Documentación automática con Swagger
- ✅ Arquitectura asíncrona completa
- ✅ Mejor manejo de errores
- ✅ Seguridad JWT mejorada
- ✅ ORM moderno con SQLAlchemy 2.0

El servidor está ejecutándose en: http://localhost:8000
