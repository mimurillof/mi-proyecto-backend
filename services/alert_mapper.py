"""
Mapeador de alertas para transformar tipos de alerta en propiedades de UI
Traduce los tipos de alerta de svga_system.py y alertas_avanzadas.py
a tarjetas de UI con colores, íconos y títulos apropiados.
"""

# Mapeador completo de alertas
ALERT_MAPPER = {
    
    # ==========================================================================
    # VERDE: OPORTUNIDADES (Éxito)
    # Basado en alertas_avanzadas.py y svga_system.py
    # ==========================================================================
    
    "PATRON_ALCISTA": {
        "title": "Oportunidad Potencial",
        "color_theme": "success",
        "icon": "💡"
    },
    "DIVERGENCIA_ALCISTA": {
        "title": "Oportunidad: Divergencia Alcista",
        "color_theme": "success",
        "icon": "📈"
    },
    "DIVERGENCIA_ALCISTA_RSI": {
        "title": "Oportunidad: Divergencia RSI",
        "color_theme": "success",
        "icon": "📈"
    },
    "RUPTURA_ALCISTA_CONFIRMADA": {
        "title": "Oportunidad: Ruptura Confirmada",
        "color_theme": "success",
        "icon": "📈"
    },
    "MACD_CRUCE_ALCISTA": {
        "title": "Oportunidad: Cruce MACD",
        "color_theme": "success",
        "icon": "📊"
    },
    "RSI_SOBREVENTA": {
        "title": "Oportunidad: Sobreventa Extrema",
        "color_theme": "success",
        "icon": "⬇️"
    },
    "SOBREVENTA": {
        "title": "Oportunidad: Sobreventa",
        "color_theme": "success",
        "icon": "⬇️"
    },
    "DIVERGENCIA_DETECTADA": {
        "title": "Oportunidad: Divergencia",
        "color_theme": "success",
        "icon": "📈"
    },
    
    # ==========================================================================
    # ROJO: ANOMALÍAS Y RIESGOS (Error)
    # Basado en alertas_avanzadas.py y svga_system.py
    # ==========================================================================
    
    "VOLATILIDAD_AUMENTADA": {
        "title": "Anomalía Detectada",
        "color_theme": "error",
        "icon": "⚠️"
    },
    "CORRELACION_ROTA": {
        "title": "Anomalía: Correlación Rota",
        "color_theme": "error",
        "icon": "⚠️"
    },
    "CAMBIO_PRECIO_ABRUPTO": {
        "title": "Anomalía: Precio Abrupto",
        "color_theme": "error",
        "icon": "⚠️"
    },
    "PATRON_BAJISTA": {
        "title": "Anomalía: Patrón Bajista",
        "color_theme": "error",
        "icon": "📉"
    },
    "DIVERGENCIA_BAJISTA": {
        "title": "Anomalía: Divergencia Bajista",
        "color_theme": "error",
        "icon": "📉"
    },
    "RUPTURA_BAJISTA_CONFIRMADA": {
        "title": "Anomalía: Ruptura Bajista",
        "color_theme": "error",
        "icon": "📉"
    },
    
    # ==========================================================================
    # AMARILLO: ALERTAS INFORMATIVAS (Advertencia)
    # Basado en alertas_avanzadas.py y svga_system.py
    # ==========================================================================
    
    "VOLUMEN_BAJO": {
        "title": "Alerta",
        "color_theme": "warning",
        "icon": "ℹ️"
    },
    "VOLUMEN_BAJO_INUSUAL": {
        "title": "Alerta",
        "color_theme": "warning",
        "icon": "ℹ️"
    },
    "VOLUMEN_ALTO": {
        "title": "Alerta: Volumen Alto",
        "color_theme": "warning",
        "icon": "📊"
    },
    "RSI_SOBRECOMPRA": {
        "title": "Alerta: Sobrecompra Extrema",
        "color_theme": "warning",
        "icon": "⬆️"
    },
    "SOBRECOMPRA": {
        "title": "Alerta: Sobrecompra",
        "color_theme": "warning",
        "icon": "⬆️"
    },
    "MERCADO_LATERAL": {
        "title": "Aviso: Mercado Lateral",
        "color_theme": "warning",
        "icon": "⏸️"
    },
    "ALERTA_CONTRA_TENDENCIA": {
        "title": "Alerta: Contra Tendencia",
        "color_theme": "warning",
        "icon": "⚠️"
    },
    "MACD_CRUCE_BAJISTA": {
        "title": "Alerta: Cruce MACD",
        "color_theme": "warning",
        "icon": "📊"
    },
    
    # ==========================================================================
    # DEFAULT (Informativo)
    # ==========================================================================
    
    "SIN_SEÑALES": {
        "title": "Informativo",
        "color_theme": "info",
        "icon": "✅"
    },
    "DEFAULT": {
        "title": "Alerta Informativa",
        "color_theme": "info",
        "icon": "ℹ️"
    }
}


def get_alert_config(alert_type: str) -> dict:
    """
    Obtiene la configuración de UI para un tipo de alerta.
    
    Args:
        alert_type: Tipo de alerta (ej: "SOBRECOMPRA", "PATRON_ALCISTA")
        
    Returns:
        Dict con title, color_theme e icon para la alerta
    """
    return ALERT_MAPPER.get(alert_type, ALERT_MAPPER["DEFAULT"])


def process_alert_to_card(alert_type: str, description: str, ticker: str, priority: str = "LOW") -> dict:
    """
    Transforma una alerta en una tarjeta lista para el frontend.
    
    Args:
        alert_type: Tipo de alerta
        description: Descripción de la alerta
        ticker: Símbolo del activo
        priority: Prioridad de la alerta (HIGH, MEDIUM, LOW)
        
    Returns:
        Dict con la estructura de la tarjeta para el frontend
    """
    config = get_alert_config(alert_type)
    
    # Determinar prioridad basada en el color_theme si no se proporciona
    if priority == "LOW" and config["color_theme"] == "error":
        priority = "HIGH"
    elif priority == "LOW" and config["color_theme"] == "success":
        priority = "MEDIUM"
    
    return {
        "id": f"{ticker}-{alert_type}",
        "title": config["title"],
        "description": f"**{ticker}:** {description}",
        "color_theme": config["color_theme"],
        "icon": config["icon"],
        "priority": priority
    }

