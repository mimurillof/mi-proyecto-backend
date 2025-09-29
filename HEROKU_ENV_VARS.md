# Variables de Entorno para Heroku - Backend

Configura las siguientes variables de entorno en Heroku para el backend.

## Comando rápido para configurar todas las variables

```bash
heroku config:set \
  ENVIRONMENT=production \
  PROJECT_NAME="Mi Proyecto API" \
  API_V1_STR="/api" \
  DATABASE_URL="postgresql+asyncpg://..." \
  SECRET_KEY="tu_secret_key_muy_seguro_y_largo" \
  ALGORITHM="HS256" \
  ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  CLIENT_ORIGIN="https://tu-frontend.vercel.app" \
  CHAT_AGENT_SERVICE_URL_PROD="https://chat-agent-horizon-cc5e16d4b37e.herokuapp.com" \
  SUPABASE_URL="https://tu-proyecto.supabase.co" \
  SUPABASE_ANON_KEY="tu_anon_key" \
  SUPABASE_SERVICE_ROLE="tu_service_role_key" \
  GEMINI_API_KEY="tu_gemini_api_key" \
  -a horizon-backend-316b23e32b8b
```

## Variables requeridas

### Configuración básica
- `ENVIRONMENT=production` - **IMPORTANTE**: Esto hace que use las URLs de producción
- `PROJECT_NAME="Mi Proyecto API"`
- `API_V1_STR="/api"`

### Base de datos
- `DATABASE_URL` - URL de conexión PostgreSQL (Heroku Postgres la crea automáticamente)

### Autenticación JWT
- `SECRET_KEY` - Clave secreta para JWT (genera una segura)
- `ALGORITHM="HS256"`
- `ACCESS_TOKEN_EXPIRE_MINUTES=30`

### CORS y Frontend
- `CLIENT_ORIGIN` - URL de tu frontend en producción

### Chat Agent Service (Comunicación entre servicios)
- `CHAT_AGENT_SERVICE_URL_PROD="https://chat-agent-horizon-cc5e16d4b37e.herokuapp.com"`

### Supabase
- `SUPABASE_URL` - URL de tu proyecto Supabase
- `SUPABASE_ANON_KEY` - Clave anónima de Supabase
- `SUPABASE_SERVICE_ROLE` - Service role key de Supabase
- `SUPABASE_BUCKET_NAME="portfolio-files"` (opcional, por defecto)
- `ENABLE_SUPABASE_UPLOAD=True` (opcional, por defecto)

### AI / APIs externas
- `GEMINI_API_KEY` - API key de Google AI
- `GOOGLE_API_KEY` - (alternativo a GEMINI_API_KEY)
- `SERPER_API_KEY` - (opcional) API key para búsquedas

## Variables opcionales

```bash
heroku config:set \
  CHAT_AGENT_TIMEOUT=30 \
  CHAT_AGENT_RETRIES=3 \
  PDF_SERVICE_URL="https://tu-pdf-service.com" \
  INTERNAL_API_KEY="tu_internal_api_key" \
  -a horizon-backend-316b23e32b8b
```

## Verificar configuración

```bash
# Ver todas las variables configuradas
heroku config -a horizon-backend-316b23e32b8b

# Ver una variable específica
heroku config:get ENVIRONMENT -a horizon-backend-316b23e32b8b
```

## Generar SECRET_KEY seguro

```python
# En Python
import secrets
print(secrets.token_urlsafe(32))
```

O en la terminal:
```bash
openssl rand -base64 32
```

## Notas importantes

1. **ENVIRONMENT=production** es CRÍTICO - sin esto, el backend intentará conectarse a localhost:8001 en lugar del servicio de Heroku
2. La variable `DATABASE_URL` es creada automáticamente por Heroku Postgres
3. Nunca compartas tus SECRET_KEY, API keys, o service role keys públicamente
4. Los CORS_ORIGINS se configuran automáticamente en el código para incluir tanto desarrollo como producción
