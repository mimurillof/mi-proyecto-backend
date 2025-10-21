@echo off
echo ============================================
echo   FIX: Database Pool Exhaustion
echo   Aumentando pool de conexiones PostgreSQL
echo ============================================
echo.

cd /d "%~dp0"

echo [1/5] Verificando cambios en database.py...
git diff database.py
echo.

echo [2/5] Agregando archivos al commit...
git add database.py
git add FIX_DATABASE_POOL_EXHAUSTION.md
echo.

echo [3/5] Creando commit...
git commit -m "fix: Aumentar pool de conexiones PostgreSQL (pool_size=20, max_overflow=10) para resolver MaxClientsInSessionMode"
echo.

echo [4/5] Deploying a Heroku...
echo Este paso puede tardar 2-3 minutos...
git push heroku master
echo.

if errorlevel 1 (
    echo.
    echo ❌ ERROR: El deploy a Heroku falló
    echo Por favor revisa los logs arriba
    pause
    exit /b 1
)

echo [5/5] Reiniciando dynos de Heroku...
heroku restart -a horizon-backend-316b23e32b8b
echo.

echo ============================================
echo   ✅ DEPLOY COMPLETADO EXITOSAMENTE
echo ============================================
echo.
echo Próximos pasos:
echo 1. Espera 30 segundos para que Heroku reinicie
echo 2. Abre: https://mi-proyecto-topaz-omega.vercel.app
echo 3. Haz login y verifica que carga el portfolio
echo.
echo Monitorear logs en tiempo real:
echo   heroku logs --tail -a horizon-backend-316b23e32b8b
echo.
echo Ver configuración del pool:
echo   heroku run python -c "from database import engine; print(f'Pool: {engine.pool.size()}')" -a horizon-backend-316b23e32b8b
echo.

pause
