# 🔴 FIX CRÍTICO: Database Pool Exhaustion

## ❌ Problema

```
asyncpg.exceptions.InternalServerError: MaxClientsInSessionMode: 
max clients reached - in Session mode max clients are limited to pool_size
```

**Síntomas:**
- ✅ Login funciona (no requiere DB)
- ❌ Todos los endpoints protegidos fallan (500 Internal Server Error)
- ❌ TimeoutError al intentar obtener conexiones a PostgreSQL
- ❌ Request Timeout H12 en Heroku (30 segundos)
- ❌ App web no carga nada

**Causa Raíz:**
SQLAlchemy usa por defecto un **pool_size=5** conexiones. Con múltiples peticiones concurrentes desde el frontend:
1. Frontend hace 4-5 peticiones simultáneas al cargar
2. Cada petición necesita una conexión para autenticación (`get_user_by_id`)
3. Pool de 5 conexiones se agota instantáneamente
4. Nuevas peticiones esperan → TimeoutError → HTTP 500

---

## ✅ Solución Implementada

### 1. Aumento del Pool de Conexiones en `database.py`

```python
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    pool_size=20,          # ✅ ANTES: 5 (default) → AHORA: 20
    max_overflow=10,       # ✅ Hasta 30 conexiones totales (20 + 10)
    pool_timeout=30,       # ✅ 30s timeout para obtener conexión
    pool_recycle=3600,     # ✅ Reciclar conexiones idle cada hora
    pool_pre_ping=True     # ✅ Verificar salud antes de usar
)
```

**Justificación:**
- **pool_size=20**: Soporta ~15-20 peticiones concurrentes
- **max_overflow=10**: Picos de tráfico hasta 30 conexiones
- **pool_recycle=3600**: Previene conexiones muertas en Heroku
- **pool_pre_ping=True**: Detecta conexiones rotas antes de usarlas

### 2. Configuración de Heroku Postgres

Verificar el plan de Heroku Postgres:
- **Hobby Dev** (gratis): Max 20 conexiones
- **Hobby Basic** ($9/mes): Max 20 conexiones
- **Standard 0** ($50/mes): Max 120 conexiones

**Con pool_size=20 + max_overflow=10 = 30 conexiones máximo**, estás dentro del límite de los planes Hobby.

---

## 🚀 Deploy del Fix

### Opción 1: Script Automático

```bash
cd c:\Users\mikia\mi-proyecto\mi-proyecto-backend
.\deploy-pool-fix.bat
```

### Opción 2: Manual

```bash
cd c:\Users\mikia\mi-proyecto\mi-proyecto-backend

# 1. Commit del fix
git add database.py
git commit -m "fix: Aumentar pool de conexiones PostgreSQL (20+10) para resolver MaxClientsInSessionMode"

# 2. Push a Heroku
git push heroku master

# 3. Reiniciar dynos
heroku restart -a horizon-backend-316b23e32b8b

# 4. Verificar logs
heroku logs --tail -a horizon-backend-316b23e32b8b
```

---

## 🧪 Verificación Post-Deploy

### 1. Verificar que no hay errores de pool

```bash
# Monitorear logs en tiempo real
heroku logs --tail -a horizon-backend-316b23e32b8b | findstr "MaxClientsInSessionMode"
```

**Resultado esperado:** Sin resultados (el error NO debe aparecer)

### 2. Verificar que el frontend carga

1. Abrir: https://mi-proyecto-topaz-omega.vercel.app
2. Hacer login
3. Verificar que los 4 assets se cargan correctamente
4. Verificar que los gráficos de ^SPX se muestran

### 3. Verificar métricas del pool

```bash
# Ver logs de conexión
heroku logs -a horizon-backend-316b23e32b8b -n 200 | findstr "pool"
```

---

## 📊 Análisis Técnico

### Flujo de Peticiones del Frontend

```
Frontend carga → 4-5 peticiones simultáneas:
├─ GET /api/portfolio-manager/watch
├─ GET /api/portfolio-manager/report
├─ GET /api/portfolio-manager/charts/portfolio
├─ GET /api/portfolio-manager/summary
└─ GET /api/portfolio-manager/market

Cada petición:
1. HTTPBearer extrae token JWT
2. Llama a get_current_user(db=Depends(get_db))
3. FastAPI crea AsyncSession del pool
4. Ejecuta SELECT * FROM users WHERE user_id=...
5. Retorna user
6. FastAPI cierra sesión automáticamente (async with)
```

### Antes del Fix (pool_size=5)

```
Petición 1 → Conexión 1 ✅
Petición 2 → Conexión 2 ✅
Petición 3 → Conexión 3 ✅
Petición 4 → Conexión 4 ✅
Petición 5 → Conexión 5 ✅
Petición 6 → ❌ WAIT... (pool exhausted)
Petición 7 → ❌ WAIT...
Después de 30s → TimeoutError → HTTP 500
```

### Después del Fix (pool_size=20 + max_overflow=10)

```
Peticiones 1-20 → Conexiones 1-20 ✅ (pool permanente)
Peticiones 21-30 → Conexiones 21-30 ✅ (overflow temporal)
Peticiones 31+ → WAIT en cola (muy raro con este pool)
```

---

## 🔧 Troubleshooting

### Si el error persiste después del deploy:

#### 1. Verificar que el código se deployó correctamente

```bash
# Ver último commit en Heroku
heroku releases -a horizon-backend-316b23e32b8b

# Ver contenido de database.py en Heroku
heroku run cat database.py -a horizon-backend-316b23e32b8b
```

Debe contener `pool_size=20`.

#### 2. Verificar plan de Heroku Postgres

```bash
heroku addons -a horizon-backend-316b23e32b8b
```

Si es **Hobby Dev** o **Hobby Basic**, verifica que no tengas otras apps usando la misma base de datos.

#### 3. Reducir pool si es necesario

Si Heroku Postgres solo permite 20 conexiones totales y tienes múltiples dynos:

```python
# En database.py
pool_size=10,      # 10 conexiones por dyno
max_overflow=5,    # 15 total por dyno
```

Con 1 dyno → 15 conexiones max ✅  
Con 2 dynos → 30 conexiones max ⚠️ (necesitarías plan Standard)

#### 4. Verificar que no hay conexiones zombies

```bash
# Reiniciar completamente Heroku
heroku restart -a horizon-backend-316b23e32b8b

# Esperar 1 minuto y probar
```

---

## 📝 Prevención Futura

### 1. Monitoreo de Pool

Agregar logging en `database.py`:

```python
import logging
logger = logging.getLogger(__name__)

async def get_db():
    logger.info(f"Pool size: {engine.pool.size()}, Checked out: {engine.pool.checkedout()}")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 2. Optimización de Queries

Cachear el usuario autenticado para evitar múltiples queries:

```python
# En auth/dependencies.py
from functools import lru_cache

@lru_cache(maxsize=128)
async def _get_user_from_token_cached(token: str, db: AsyncSession) -> User:
    # ... lógica existente
```

### 3. Connection Pooling en Supabase

Si usas Supabase para Storage pero también tienes tu propia DB, considera usar **Supabase Pooler** (PgBouncer) que maneja miles de conexiones.

---

## 🎯 Resultado Esperado

### Antes del Fix ❌
```
Frontend → 5 peticiones → Pool exhausted → TimeoutError → HTTP 500
Usuario ve: Pantalla en blanco con spinner infinito
```

### Después del Fix ✅
```
Frontend → 5 peticiones → Pool OK (20 disponibles) → HTTP 200
Usuario ve: Dashboard completo con 4 assets + gráficos de ^SPX
```

---

**Estado:** ✅ **FIX LISTO PARA DEPLOY**  
**Próximo Paso:** Ejecutar `.\deploy-pool-fix.bat` desde `mi-proyecto-backend`

**Fecha:** 20 de octubre de 2025  
**Tiempo estimado de deploy:** ~2-3 minutos  
**Downtime:** Ninguno (rolling restart en Heroku)
