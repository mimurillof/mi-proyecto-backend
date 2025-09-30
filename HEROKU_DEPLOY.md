# Guía de Despliegue en Heroku - Mi Proyecto Backend

## Requisitos previos
- Cuenta de Heroku
- Heroku CLI instalado
- Git configurado

## Pasos para desplegar

### 1. Iniciar sesión en Heroku
```bash
heroku login
```

### 2. Crear la aplicación en Heroku
```bash
heroku create mi-proyecto-backend
```

O si quieres un nombre específico:
```bash
heroku create tu-nombre-backend
```

### 3. Configurar las variables de entorno
Necesitas configurar las siguientes variables de entorno en Heroku:

```bash
# Configuración de la base de datos
heroku config:set DATABASE_URL=postgresql://usuario:password@host:5432/dbname

# Configuración de Supabase
heroku config:set SUPABASE_URL=tu_supabase_url
heroku config:set SUPABASE_KEY=tu_supabase_key
heroku config:set SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key

# Configuración del proyecto
heroku config:set PROJECT_NAME="Mi Proyecto Backend"
heroku config:set API_V1_STR="/api"
heroku config:set ENVIRONMENT=production

# ⚠️ IMPORTANTE: CORS - URL del Frontend
# Esta variable es CRÍTICA para que el frontend pueda hacer peticiones al backend
heroku config:set CLIENT_ORIGIN=https://tu-proyecto.vercel.app

# Configuración de autenticación
heroku config:set SECRET_KEY=tu_secret_key_muy_seguro
heroku config:set ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys (si las usas)
heroku config:set GEMINI_API_KEY=tu_gemini_api_key
heroku config:set OPENAI_API_KEY=tu_openai_api_key
```

**NOTA IMPORTANTE SOBRE CORS:**
El backend está configurado para aceptar peticiones desde la URL especificada en `CLIENT_ORIGIN`. Si despliegas el frontend en Vercel y obtienes errores de CORS, asegúrate de configurar esta variable con la URL exacta de tu despliegue de Vercel.

### 4. Agregar PostgreSQL (si lo necesitas)
```bash
heroku addons:create heroku-postgresql:mini
```

### 5. Desplegar la aplicación
```bash
# Si estás en el directorio del proyecto
git push heroku main

# Si estás en un subdirectorio
git subtree push --prefix=mi-proyecto-backend heroku main
```

### 6. Ejecutar migraciones de base de datos (si es necesario)
```bash
heroku run python init_db.py
```

### 7. Ver los logs
```bash
heroku logs --tail
```

### 8. Abrir la aplicación
```bash
heroku open
```

## Configuración del Procfile
El archivo `Procfile` ya está configurado con:
```
web: gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

Esto usa:
- **Gunicorn** como servidor WSGI para producción
- **4 workers** para manejar múltiples peticiones
- **UvicornWorker** para soportar aplicaciones FastAPI/ASGI
- **$PORT** variable de entorno proporcionada por Heroku

## Verificar el despliegue
Visita: `https://tu-app.herokuapp.com/`

Endpoint de health check: `https://tu-app.herokuapp.com/api/health`

## Troubleshooting

### Ver logs en tiempo real
```bash
heroku logs --tail
```

### Reiniciar la aplicación
```bash
heroku restart
```

### Ver las variables de entorno configuradas
```bash
heroku config
```

### Escalar dynos (si necesitas más recursos)
```bash
heroku ps:scale web=1
```

### Errores de CORS desde el frontend
**Síntoma**: El frontend en Vercel muestra errores como:
```
Access to fetch has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Solución**:
```bash
# 1. Configurar la URL exacta del frontend de Vercel
heroku config:set CLIENT_ORIGIN=https://tu-proyecto.vercel.app -a horizon-backend

# 2. Verificar que se configuró correctamente
heroku config:get CLIENT_ORIGIN -a horizon-backend

# 3. Redesplegar el backend (si hiciste cambios en el código)
git push heroku main

# 4. Verificar los logs
heroku logs --tail -a horizon-backend
```

**Importante**: 
- La URL debe ser EXACTA (sin `/` al final)
- Debe coincidir con el dominio desde donde se hacen las peticiones
- El backend incluye automáticamente `CLIENT_ORIGIN` en la lista de orígenes permitidos

### Timeout al generar reportes (H12)
**Síntoma**: Al generar reportes desde el frontend, aparece "Failed to fetch" después de 30 segundos.

**Causa**: Heroku tiene un límite fijo de 30 segundos para requests HTTP. Generar reportes con Gemini toma más tiempo.

**Soluciones**:

1. **Solución Rápida** - Usar modelo más rápido:
   - Cambiar `model_preference` a `"gemini-2.5-flash"` (3x más rápido)
   - Genera reportes en ~15-20 segundos

2. **Solución Permanente** - Implementar procesamiento asíncrono:
   - Ver documentación completa en `REPORTE_TIMEOUT_SOLUTION.md`
   - Requiere endpoints de polling
   - Mejor experiencia de usuario

**Documentación**: Ver `REPORTE_TIMEOUT_SOLUTION.md` en la raíz del proyecto

## Notas importantes
- El puerto lo asigna Heroku automáticamente a través de la variable `$PORT`
- Asegúrate de que todas las variables de entorno estén configuradas antes de desplegar
- **`CLIENT_ORIGIN` es crítico para que el frontend pueda comunicarse con el backend**
- **Heroku tiene un timeout de 30 segundos** - procesos largos deben ser asíncronos
- Los archivos en `.gitignore` no se desplegarán
- El directorio `venv/` no debe incluirse en el repositorio
