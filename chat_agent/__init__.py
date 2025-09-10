# -*- coding: utf-8 -*-
"""
Chat Agent Package
Agente financiero Horizon v3.0 integrado con FastAPI
"""

try:
    from .agent_service import HorizonAgent
    
    __all__ = ["HorizonAgent"]
    
except ImportError as e:
    print(f"⚠️ Error importando agente: {e}")
    HorizonAgent = None
    __all__ = []
