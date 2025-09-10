# Agente Financiero Horizon v3.0

## Descripción

Horizon v3.0 es un agente financiero avanzado integrado con FastAPI que utiliza Google Gemini AI para proporcionar análisis financiero inteligente. El agente está diseñado con una arquitectura de distribución de modelos que optimiza el rendimiento según el tipo de consulta.

## Características Principales

### 🚀 Modelos Especializados

**Gemini 2.5 Flash** - Consultas rápidas:
- Búsquedas web en tiempo real
- Análisis de URLs
- Consultas generales del mercado
- Noticias financieras actualizadas
- Definiciones y conceptos financieros

**Gemini 2.5 Pro** - Análisis profundo:
- Análisis de documentos financieros
- Reportes anuales y estados financieros
- Procesamiento de archivos CSV/PDF
- Análisis de gráficos y métricas
- Evaluación cuantitativa rigurosa

### 🛠️ Capacidades Técnicas

- **Búsqueda Web**: Información financiera en tiempo real
- **Análisis de URLs**: Procesamiento de páginas web financieras
- **Análisis de Documentos**: Soporte para múltiples formatos
- **Gestión de Sesiones**: Contexto persistente entre consultas
- **API RESTful**: Integración completa con FastAPI
- **Carga de Archivos**: Análisis de documentos adjuntos

## Instalación y Configuración

### 1. Dependencias

```bash
pip install -r requirements.txt
```

### 2. Variables de Entorno

Copia `.env.example` a `.env` y configura:

```bash
# Configuración de Google Gemini
GEMINI_API_KEY=tu-api-key-aqui
GOOGLE_API_KEY=tu-api-key-aqui  # Nombre alternativo

# Configuración de FastAPI
PROJECT_NAME="Mi Proyecto - Finanzas con IA"
ENVIRONMENT=development
CLIENT_ORIGIN=http://localhost:5173
```

### 3. Obtener API Key de Google Gemini

1. Ve a [Google AI Studio](https://aistudio.google.com/)
2. Crea una nueva API Key
3. Agrega la key a tu archivo `.env`

## Uso

### Ejecutar el Servidor

```bash
# Desarrollo
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Pruebas del Agente

```bash
# Ejecutar todas las pruebas
python test_agent.py test

# Chat interactivo
python test_agent.py chat
```

## API Endpoints

### Chat Principal

**POST** `/api/v1/ai/chat`

```json
{
  "message": "¿Cuál es el P/E ratio de Apple?",
  "url": "https://finance.yahoo.com/quote/AAPL",
  "session_id": "optional-session-id",
  "use_model": "gemini-2.5-flash"
}
```

**Respuesta:**
```json
{
  "response": "El P/E ratio de Apple es...",
  "model_used": "gemini-2.5-flash",
  "tools_used": ["Google Search", "URL Context"],
  "urls_processed": ["https://finance.yahoo.com/quote/AAPL"],
  "token_usage": {
    "input_tokens": 150,
    "output_tokens": 200,
    "total_tokens": 350
  },
  "session_id": "uuid-session-id"
}
```

### Chat con Archivo

**POST** `/api/v1/ai/chat/upload`

Form data:
- `message`: Mensaje del usuario
- `file`: Archivo para análisis
- `session_id`: ID de sesión (opcional)

### Gestión de Sesiones

**POST** `/api/v1/ai/chat/session/new`
- Crea nueva sesión

**GET** `/api/v1/ai/chat/session/{session_id}`
- Obtiene información de sesión

### Estado del Agente

**GET** `/api/v1/ai/agent/status`
- Estado actual del agente

**GET** `/api/v1/ai/agent/health`
- Health check

### Predicción de Tendencias

**POST** `/api/v1/ai/predict?symbol=AAPL&period=1month`
- Análisis de tendencias

## Ejemplos de Uso

### 1. Consulta Simple

```python
import requests

response = requests.post("http://localhost:8000/api/v1/ai/chat", json={
    "message": "¿Qué es el ROE y cómo se calcula?"
})
```

### 2. Búsqueda de Noticias

```python
response = requests.post("http://localhost:8000/api/v1/ai/chat", json={
    "message": "Últimas noticias sobre Tesla",
    "use_model": "gemini-2.5-flash"
})
```

### 3. Análisis de URL

```python
response = requests.post("http://localhost:8000/api/v1/ai/chat", json={
    "message": "Analiza esta página financiera",
    "url": "https://finance.yahoo.com/quote/TSLA"
})
```

### 4. Análisis de Documento

```python
files = {'file': open('reporte_financiero.pdf', 'rb')}
data = {'message': 'Analiza este reporte financiero'}

response = requests.post(
    "http://localhost:8000/api/v1/ai/chat/upload",
    files=files,
    data=data
)
```

## Arquitectura del Sistema

### Distribución de Modelos

```
Usuario Input → Analizador de Consulta
                        ↓
              ¿Hay archivo local?
                     ↙        ↘
                 Sí: Pro      No: ¿Hay URL?
              (Sin web)           ↙      ↘
                              Sí: Flash  No: Determinar
                            (Con URL)    por keywords
                                            ↓
                                        Flash o Pro
```

### Flujo de Procesamiento

1. **Recepción**: API recibe solicitud
2. **Validación**: Validar parámetros y sesión
3. **Enrutamiento**: Determinar modelo óptimo
4. **Procesamiento**: Ejecutar modelo con herramientas
5. **Respuesta**: Formatear y retornar resultado

## Troubleshooting

### Error: API Key no configurada

```bash
❌ Error: GEMINI_API_KEY o GOOGLE_API_KEY no configurada
```

**Solución**: Configura la API key en `.env`

### Error: Herramientas no disponibles

```bash
⚠️ Herramientas no disponibles: 403 Forbidden
```

**Solución**: Verifica que la API key tenga permisos para búsqueda web

### Error: Modelo no disponible

```bash
❌ Error: Model not found
```

**Solución**: Verifica que tienes acceso a los modelos Gemini 2.5

## Monitoreo y Logs

El agente proporciona logs detallados:

```
✅ Cliente Gemini configurado correctamente
⚡ [Flash]: Procesando consulta
🔍 (con Google Search, URL Context)
🧠 [Pro]: Análisis profundo
📋 (análisis local únicamente)
```

## Próximas Características

- [ ] Análisis de sentimiento de mercado
- [ ] Integración con APIs financieras (Alpha Vantage, IEX)
- [ ] Cache de respuestas frecuentes
- [ ] Análisis de gráficos e imágenes mejorado
- [ ] Notificaciones push para alertas
- [ ] Dashboard de métricas del agente

## Contribuir

1. Fork el repositorio
2. Crea una rama feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -am 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## Soporte

Para soporte y preguntas:
- Abrir un issue en GitHub
- Contactar al equipo de desarrollo

---

**Horizon v3.0** - Análisis financiero inteligente con IA especializada.
