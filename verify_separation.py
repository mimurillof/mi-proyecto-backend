#!/usr/bin/env python3
"""
Script de verificación final - Chat Agent Service separado
"""

import requests
import json

# URLs de los servicios
BACKEND_URL = "http://localhost:8000"
AGENT_URL = "http://localhost:8001"

def test_backend_health():
    """Verifica que el backend principal esté corriendo"""
    try:
        response = requests.get(f"{BACKEND_URL}/")
        print(f"✅ Backend Principal: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Backend Principal: {str(e)}")
        return False

def test_agent_health():
    """Verifica que el servicio de agente esté corriendo"""
    try:
        response = requests.get(f"{AGENT_URL}/health")
        print(f"✅ Servicio de Agente: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Servicio de Agente: {str(e)}")
        return False

def test_backend_ai_health():
    """Verifica el health check del AI router"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/ai/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Backend AI Health: {result}")
            return True
        else:
            print(f"❌ Backend AI Health: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend AI Health: {str(e)}")
        return False

def test_chat_functionality():
    """Prueba la funcionalidad de chat completa"""
    try:
        payload = {
            "message": "Hola, ¿puedes explicarme brevemente qué son las acciones?"
        }
        response = requests.post(f"{BACKEND_URL}/api/ai/chat", json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat Funcional: {result.get('response', 'Sin respuesta')[:100]}...")
            return True
        else:
            print(f"❌ Chat: Status {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Chat: {str(e)}")
        return False

def main():
    print("🔍 Verificación final - Servicios separados\n")
    
    # Verificar servicios básicos
    backend_ok = test_backend_health()
    agent_ok = test_agent_health()
    ai_health_ok = test_backend_ai_health()
    
    if not backend_ok or not agent_ok:
        print("\n❌ Servicios básicos no disponibles")
        return False
    
    print("\n🧪 Probando funcionalidad completa...\n")
    
    # Probar chat completo
    chat_ok = test_chat_functionality()
    
    print("\n📊 Resumen Final:")
    print(f"- Backend Principal: {'✅' if backend_ok else '❌'}")
    print(f"- Servicio de Agente: {'✅' if agent_ok else '❌'}")
    print(f"- Backend AI Health: {'✅' if ai_health_ok else '❌'}")
    print(f"- Chat Funcional: {'✅' if chat_ok else '❌'}")
    
    if backend_ok and agent_ok and ai_health_ok and chat_ok:
        print("\n🎉 ¡SEPARACIÓN COMPLETADA EXITOSAMENTE!")
        print("✅ Es seguro eliminar la carpeta 'chat_agent'")
        print("✅ El sistema funciona completamente con servicios separados")
        return True
    else:
        print("\n⚠️ Hay problemas que necesitan revisión")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)