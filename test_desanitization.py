"""
Test de desanitización de nombres de archivo.
"""
import sys
sys.path.append("c:\\Users\\mikia\\mi-proyecto\\mi-proyecto-backend")

from services.portfolio_manager_service import desanitize_filename_for_storage

def test_desanitization():
    """Prueba la desanitización de nombres de archivo."""
    
    test_cases = [
        ("_CARET_SPX_chart.html", "^SPX_chart.html"),
        ("_CARET_GSPC_chart.png", "^GSPC_chart.png"),
        ("BTC-USD_chart.html", "BTC-USD_chart.html"),  # Sin cambios
        ("AAPL_chart.html", "AAPL_chart.html"),        # Sin cambios
        ("test_CARET_file_LT_name_GT_.html", "test^file<name>.html"),
    ]
    
    print("=" * 80)
    print("TEST DE DESANITIZACIÓN DE NOMBRES DE ARCHIVO (BACKEND)")
    print("=" * 80)
    print()
    
    all_passed = True
    
    for sanitized, expected in test_cases:
        result = desanitize_filename_for_storage(sanitized)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✓" if passed else "✗"
        print(f"{status} {sanitized:40s} → {result:30s}", end="")
        
        if not passed:
            print(f" (esperado: {expected})")
        else:
            print()
    
    print()
    print("=" * 80)
    print("TEST DE EXTRACCIÓN DE SÍMBOLO")
    print("=" * 80)
    print()
    
    # Simular el proceso del backend
    test_files = [
        "_CARET_SPX_chart.html",
        "BTC-USD_chart.html",
        "NVDA_chart.html",
        "_CARET_GSPC_chart.html",
    ]
    
    for file_name in test_files:
        desanitized = desanitize_filename_for_storage(file_name)
        symbol = desanitized.replace("_chart.html", "").replace(".html", "")
        print(f"  Archivo:  {file_name:35s} → Símbolo: {symbol}")
    
    print()
    print("=" * 80)
    
    if all_passed:
        print("✓ TODAS LAS PRUEBAS PASARON")
        return 0
    else:
        print("✗ ALGUNAS PRUEBAS FALLARON")
        return 1

if __name__ == "__main__":
    sys.exit(test_desanitization())
