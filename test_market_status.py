"""Script para probar el estado del mercado."""
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    MARKET_TZ = ZoneInfo("America/New_York")
except ImportError:
    import pytz
    MARKET_TZ = pytz.timezone("America/New_York")

def is_market_open():
    """Verifica si el mercado está abierto."""
    current = datetime.now(MARKET_TZ)
    print(f"Hora actual en ET: {current}")
    print(f"Día de la semana: {current.weekday()} (0=Lunes, 6=Domingo)")
    
    if current.weekday() >= 5:
        print("❌ Mercado CERRADO - Es fin de semana")
        return False
    
    open_time = current.replace(hour=9, minute=30, second=0, microsecond=0)
    close_time = current.replace(hour=16, minute=0, second=0, microsecond=0)
    
    print(f"Hora de apertura: {open_time}")
    print(f"Hora de cierre: {close_time}")
    
    is_open = open_time <= current <= close_time
    
    if is_open:
        print("✅ Mercado ABIERTO")
    else:
        print("❌ Mercado CERRADO")
    
    return is_open

if __name__ == "__main__":
    market_status = is_market_open()
    print(f"\nResultado: {market_status}")
