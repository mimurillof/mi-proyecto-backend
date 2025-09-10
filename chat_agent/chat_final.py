# -*- coding: utf-8 -*-
"""
Horizon v3.0 - Versión Final Corregida
Autor: Gemini, para Miguel Ángel Murillo Frías
Fecha: 2025-07-04

Agente financiero con distribución correcta de funcionalidades:
- Gemini 2.5 Flash: Búsquedas web, URL Context, consultas rápidas
- Gemini 2.5 Pro: Análisis profundo de documentos locales únicamente
"""
import os
import sys
from typing import Optional
import mimetypes
from dotenv import load_dotenv

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()

try:
    from google import genai
    from google.genai import types
    
    # El cliente obtiene la API key automáticamente de la variable de entorno GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY o GOOGLE_API_KEY no configurada en .env")
    
    # Configurar la variable de entorno si no está configurada
    if not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = api_key
    
    client = genai.Client()
    print("✅ Configuración completada")
    
except Exception as e:
    print(f"❌ Error de configuración: {e}")
    sys.exit(1)

# --- CONFIGURACIÓN DE MODELOS ---
MODEL_FLASH = 'gemini-2.5-flash'
MODEL_PRO = 'gemini-2.5-pro'

# Prompts del sistema
FLASH_SYSTEM_PROMPT = """
Eres un asistente financiero rápido y eficiente especializado en:
- Consultas generales del mercado y definiciones financieras
- Búsquedas web de información actualizada 
- Análisis de contenido de URLs
- Resúmenes concisos y respuestas directas
- Noticias financieras en tiempo real

Utiliza las herramientas de búsqueda web y análisis de URLs cuando necesites información actualizada.
Sé directo, preciso y proporciona fuentes cuando sea apropiado.
"""

PRO_SYSTEM_PROMPT = """
Eres un analista financiero cuantitativo senior, escéptico y riguroso como 
los protagonistas de 'The Big Short'. Tu especialidad es el análisis profundo de:
- Documentos financieros y reportes anuales
- Estados financieros y métricas
- Gráficos, tablas y datos numéricos
- Archivos CSV, PDF, imágenes de documentos

No confías en opiniones populares; confías en los datos duros. Identifica patrones, 
riesgos, tendencias y métricas clave. Proporciona conclusiones fundamentadas y 
señala inconsistencias o riesgos ocultos en los documentos que analices.

IMPORTANTE: Solo trabajas con documentos locales. No tienes acceso a búsquedas web.
"""

print(f"✅ Modelos configurados: {MODEL_FLASH}, {MODEL_PRO}")

# --- FUNCIONES DE UTILIDAD ---
def validar_archivo(file_path: str) -> bool:
    """Valida si un archivo existe."""
    return os.path.exists(file_path) and os.path.isfile(file_path)

def procesar_texto(file_path: str) -> Optional[str]:
    """Procesa archivo de texto."""
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error procesando texto: {e}")
        return None

def usar_modelo_flash(prompt: str, url: Optional[str] = None):
    """
    Usa Gemini 2.5 Flash para consultas rápidas, búsquedas web y URL Context.
    """
    print(f"⚡ [Flash]: Consulta rápida con herramientas web")
    
    # Preparar prompt
    prompt_completo = FLASH_SYSTEM_PROMPT + "\n\nConsulta del usuario: " + prompt
    
    # Agregar URL si se proporciona
    if url:
        prompt_completo += f" {url}"
        print(f"🔗 URL incluida: {url}")
    
    try:
        # Configurar herramientas para Flash (solo estas están disponibles)
        tools = []
        tools.append(types.Tool(google_search=types.GoogleSearch()))
        
        if url:
            # URL Context solo si hay URL
            tools.append(types.Tool(url_context=types.UrlContext()))
        
        config = types.GenerateContentConfig(
            tools=tools,
            response_modalities=["TEXT"]
        )
        
        response = client.models.generate_content(
            model=MODEL_FLASH,
            contents=prompt_completo,
            config=config
        )
        
        herramientas = ["Google Search"]
        if url:
            herramientas.append("URL Context")
        print(f"🔍 (con {', '.join(herramientas)})")
        
        return response
        
    except Exception as tool_error:
        print(f"⚠️ Herramientas no disponibles ({tool_error})")
        print("🔧 Ejecutando Flash sin herramientas...")
        
        # Fallback sin herramientas
        response = client.models.generate_content(
            model=MODEL_FLASH,
            contents=prompt_completo
        )
        return response

def usar_modelo_pro(prompt: str, file_path: str):
    """
    Usa Gemini 2.5 Pro para análisis profundo de documentos locales únicamente.
    """
    print(f"🧠 [Pro]: Análisis profundo de documento")
    
    # Preparar prompt con el documento
    prompt_completo = PRO_SYSTEM_PROMPT + "\n\nConsulta del usuario: " + prompt
    
    # Procesar archivo
    if validar_archivo(file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type and "image/" in mime_type:
            prompt_completo += f"\n\nSe adjunta imagen para análisis: {file_path}"
            print(f"🖼️ Imagen incluida: {file_path}")
        else:
            texto = procesar_texto(file_path)
            if texto:
                prompt_completo += f"\n\nContenido del archivo {file_path}:\n{texto}"
                print(f"📄 Documento cargado: {file_path}")
            else:
                raise ValueError(f"No se pudo cargar el archivo: {file_path}")
    else:
        raise ValueError(f"Archivo no encontrado: {file_path}")
    
    # Ejecutar Pro SIN herramientas (no tiene acceso a búsquedas web)
    response = client.models.generate_content(
        model=MODEL_PRO,
        contents=prompt_completo
    )
    
    print("📋 (análisis local únicamente)")
    return response

# --- FUNCIÓN PRINCIPAL ---
def run_financial_agent(prompt: str, file_path: Optional[str] = None, url: Optional[str] = None):
    """
    Función principal del agente financiero con distribución correcta de modelos.
    """
    print(f"\n🤖 Analizando consulta...")
    
    # Lógica de enrutamiento basada en capacidades de cada modelo
    if file_path and validar_archivo(file_path):
        # Si hay archivo, usar Pro para análisis profundo (sin herramientas web)
        try:
            response = usar_modelo_pro(prompt, file_path)
            model_usado = MODEL_PRO
        except Exception as e:
            print(f"❌ Error con modelo Pro: {e}")
            print("🔄 Intentando con Flash...")
            response = usar_modelo_flash(prompt, url)
            model_usado = MODEL_FLASH
    
    elif url:
        # Si hay URL pero no archivo, usar Flash con URL Context
        response = usar_modelo_flash(prompt, url)
        model_usado = MODEL_FLASH
        
    else:
        # Consulta general: determinar por palabras clave
        pro_keywords = ['analiza', 'reporte', 'informe', 'métricas', 'profundo', 
                       'análisis', 'evaluar', 'documento']
        
        if any(keyword in prompt.lower() for keyword in pro_keywords) and not url:
            # Análisis profundo pero sin archivo ni URL -> usar Flash con búsqueda web
            print("💡 Sugerencia: Para análisis profundo proporciona un archivo local")
            response = usar_modelo_flash(prompt, url)
            model_usado = MODEL_FLASH
        else:
            # Consulta general -> Flash con búsqueda web
            response = usar_modelo_flash(prompt, url)
            model_usado = MODEL_FLASH
    
    # Mostrar respuesta
    try:
        print(f"\n--- 📊 Respuesta de {model_usado} ---")
        print(response.text)
        
        # Mostrar metadatos si están disponibles
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            print(f"\n📈 Tokens: entrada={usage.prompt_token_count}, salida={usage.candidates_token_count}")
            
        # Mostrar URLs procesadas si hay URL Context
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'url_context_metadata') and candidate.url_context_metadata:
                print(f"\n🔗 URLs procesadas:")
                for url_meta in candidate.url_context_metadata.url_metadata:
                    status = "✅" if "SUCCESS" in str(url_meta.url_retrieval_status) else "❌"
                    print(f"   {status} {url_meta.retrieved_url}")
                    
    except Exception as e:
        print(f"\n❌ Error mostrando respuesta: {e}")

# --- BUCLE DE CHAT ---
def mostrar_bienvenida():
    """Muestra mensaje de bienvenida."""
    print("\n" + "="*70)
    print("🚀 Horizon v3.0")
    print("="*70)
    print("🧠 Análisis financiero con IA especializada")
    print()
    print("⚡ Gemini 2.5 Flash:")
    print("   • Consultas rápidas del mercado")
    print("   • Búsquedas web en tiempo real") 
    print("   • Análisis de URLs")
    print()
    print("🧠 Gemini 2.5 Pro:")
    print("   • Análisis profundo de documentos")
    print("   • Reportes financieros locales")
    print("   • Métricas y gráficos")
    print()
    print("💬 Escribe 'salir' para terminar")
    print("="*70)

def chat_loop():
    """Bucle principal de chat."""
    mostrar_bienvenida()
    
    while True:
        try:
            print("\n" + "-"*50)
            prompt = input("💬 Tu consulta: ").strip()
            
            if prompt.lower() in ['salir', 'exit', 'quit']:
                print("\n👋 ¡Gracias por usar Horizon!")
                break
            
            if not prompt:
                print("⚠️ Ingresa una consulta válida")
                continue
            
            file_path = input("📁 Archivo local (opcional): ").strip() or None
            url = input("🔗 URL (opcional): ").strip() or None
            
            run_financial_agent(prompt, file_path, url)
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")

# --- FUNCIÓN DE PRUEBAS ---
def test_agent():
    """Ejecuta pruebas del agente."""
    print("\n🧪 === Pruebas del Agente v3.0 ===")
    
    tests = [
        {
            "name": "Consulta simple con Flash",
            "prompt": "¿Qué es el P/E ratio?",
            "file_path": None,
            "url": None
        },
        {
            "name": "Búsqueda web con Flash",
            "prompt": "¿Cuáles son las últimas noticias de Tesla?",
            "file_path": None,
            "url": None
        },
        {
            "name": "Análisis de URL con Flash",
            "prompt": "Resume la información financiera de esta página",
            "file_path": None,
            "url": "https://finance.yahoo.com"
        }
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"\n🔬 Prueba {i}: {test['name']}")
        try:
            run_financial_agent(test["prompt"], test["file_path"], test["url"])
            print(f"✅ Prueba {i} completada")
        except Exception as e:
            print(f"❌ Prueba {i} falló: {e}")
        
        if i < len(tests):
            input("\nPresiona Enter para continuar...")
    
    print("\n🎉 Todas las pruebas completadas")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_agent()
    else:
        chat_loop()
