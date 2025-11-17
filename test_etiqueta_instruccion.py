#!/usr/bin/env python3
"""
Script de prueba para validar etiquetas + instrucciones en la misma línea
"""

from ensamblador import Ensamblador8086

def test_etiqueta_instruccion():
    print("=" * 80)
    print("PRUEBA: ETIQUETAS + INSTRUCCIONES EN LA MISMA LÍNEA")
    print("=" * 80)
    
    ensamblador = Ensamblador8086()
    
    # Casos de prueba
    casos = [
        ("inicio:", "Correcta", "Solo etiqueta"),
        ("inicio: nop", "Correcta", "Etiqueta + instrucción válida sin operandos"),
        ("inicio: inc ax", "Correcta", "Etiqueta + instrucción válida con operandos"),
        ("inicio: mov ax, bx", "Incorrecta", "Etiqueta + instrucción no asignada"),
        ("inicio: xor cx, cx", "Correcta", "Etiqueta + XOR (asignada)"),
        ("etiq: add ax, bx", "Incorrecta", "Etiqueta + ADD (no asignada)"),
        ("ciclo: loope ciclo", "Correcta", "Etiqueta + LOOPE (asignada)"),
        ("fin: hlt", "Incorrecta", "Etiqueta + HLT (no asignada)"),
    ]
    
    print("\nResultados:")
    print(f"{'Línea':<25} {'Esperado':<12} {'Obtenido':<12} {'Estado':<10} {'Mensaje':<40}")
    print("-" * 100)
    
    todos_correctos = True
    
    for linea, esperado, descripcion in casos:
        tokens = ensamblador.tokenizar_linea(linea, 1)
        resultado, mensaje = ensamblador.validar_segmento_codigo(tokens)
        
        estado = "✓ PASS" if resultado == esperado else "✗ FAIL"
        if resultado != esperado:
            todos_correctos = False
        
        print(f"{linea:<25} {esperado:<12} {resultado:<12} {estado:<10} {mensaje[:38]:<40}")
    
    print("\n" + "=" * 80)
    if todos_correctos:
        print("✓ TODOS LOS TESTS PASARON")
    else:
        print("✗ ALGUNOS TESTS FALLARON")
    print("=" * 80)
    
    return todos_correctos

if __name__ == "__main__":
    try:
        test_etiqueta_instruccion()
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
