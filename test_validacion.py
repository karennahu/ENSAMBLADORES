#!/usr/bin/env python3
"""
Script de prueba para verificar la validación de líneas incorrectas
"""

from ensamblador import Ensamblador8086

def test_validacion():
    print("=" * 80)
    print("PRUEBA DE VALIDACIÓN DE ERRORES")
    print("=" * 80)
    
    ensamblador = Ensamblador8086()
    
    print("\n1. Cargando archivo con errores intencionales...")
    if ensamblador.cargar_archivo("ejemplo_errores.asm"):
        print("   ✓ Archivo cargado exitosamente")
    else:
        print("   ✗ Error al cargar el archivo")
        return False
    
    print("\n2. Realizando análisis sintáctico...")
    ensamblador.analizar_sintaxis()
    
    print("\n3. Resultados del análisis:")
    correctas = sum(1 for l in ensamblador.lineas_analizadas if l['resultado'] == 'Correcta')
    incorrectas = sum(1 for l in ensamblador.lineas_analizadas if l['resultado'] == 'Incorrecta')
    
    print(f"   - Líneas correctas: {correctas}")
    print(f"   - Líneas incorrectas: {incorrectas}")
    
    print("\n4. Detalle de líneas INCORRECTAS:")
    print(f"   {'Línea':<6} {'Código':<40} {'Mensaje de Error':<50}")
    print("   " + "-" * 100)
    for analisis in ensamblador.lineas_analizadas:
        if analisis['resultado'] == 'Incorrecta':
            linea_num = analisis['numero']
            linea = analisis['linea'][:38]
            mensaje = analisis['mensaje'][:48]
            print(f"   {linea_num:<6} {linea:<40} {mensaje:<50}")
    
    print("\n5. Todas las líneas del segmento de código:")
    print(f"   {'Línea':<6} {'Resultado':<12} {'Código':<35} {'Mensaje':<40}")
    print("   " + "-" * 100)
    for analisis in ensamblador.lineas_analizadas:
        if any(keyword in analisis['linea'].lower() for keyword in ['mov', 'add', 'push', 'jmp', 'sub', 'xor', 'hlt', 'nop', 'cmc', 'invalid', 'inicio:']):
            linea_num = analisis['numero']
            resultado = analisis['resultado']
            linea = analisis['linea'][:33]
            mensaje = analisis['mensaje'][:38]
            marca = "✗" if resultado == "Incorrecta" else "✓"
            print(f"   {linea_num:<6} {resultado:<12} {linea:<35} {mensaje:<40} {marca}")
    
    print("\n" + "=" * 80)
    if incorrectas > 0:
        print(f"PRUEBA EXITOSA: Se detectaron {incorrectas} líneas incorrectas")
    else:
        print("ADVERTENCIA: No se detectaron errores (debería haber algunos)")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        test_validacion()
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
