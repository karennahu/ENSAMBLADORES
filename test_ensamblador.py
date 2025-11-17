#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento del ensamblador sin GUI
"""

from ensamblador import Ensamblador8086, TipoToken

def test_ensamblador():
    print("=" * 80)
    print("PRUEBA DEL ENSAMBLADOR 8086")
    print("=" * 80)
    
    ensamblador = Ensamblador8086()
    
    print("\n1. Cargando archivo ejemplo.asm...")
    if ensamblador.cargar_archivo("ejemplo.asm"):
        print("   ✓ Archivo cargado exitosamente")
        print(f"   - Líneas de código: {len(ensamblador.lineas_codigo)}")
        print(f"   - Tokens encontrados: {len(ensamblador.tokens)}")
    else:
        print("   ✗ Error al cargar el archivo")
        return False
    
    print("\n2. Verificando tokenización...")
    elementos_compuestos_encontrados = []
    instrucciones_encontradas = []
    registros_encontrados = []
    
    for token in ensamblador.tokens[:50]:
        if token.tipo == TipoToken.ELEMENTO_COMPUESTO:
            elementos_compuestos_encontrados.append(token.valor)
        elif token.tipo == TipoToken.INSTRUCCION:
            instrucciones_encontradas.append(token.valor)
        elif token.tipo == TipoToken.REGISTRO:
            registros_encontrados.append(token.valor)
    
    print(f"   - Elementos compuestos: {len(elementos_compuestos_encontrados)}")
    if elementos_compuestos_encontrados:
        print(f"     Ejemplos: {elementos_compuestos_encontrados[:5]}")
    
    print(f"   - Instrucciones: {len(instrucciones_encontradas)}")
    if instrucciones_encontradas:
        print(f"     Ejemplos: {instrucciones_encontradas[:5]}")
    
    print(f"   - Registros: {len(registros_encontrados)}")
    if registros_encontrados:
        print(f"     Ejemplos: {registros_encontrados[:5]}")
    
    print("\n3. Mostrando primeros 20 tokens:")
    print(f"   {'Núm.':<6} {'Token':<25} {'Tipo':<30}")
    print("   " + "-" * 70)
    for i, token in enumerate(ensamblador.tokens[:20], 1):
        print(f"   {i:<6} {token.valor:<25} {token.tipo.value:<30}")
    
    print("\n4. Realizando análisis sintáctico...")
    ensamblador.analizar_sintaxis()
    print(f"   ✓ Análisis completado")
    print(f"   - Líneas analizadas: {len(ensamblador.lineas_analizadas)}")
    print(f"   - Símbolos en tabla: {len(ensamblador.tabla_simbolos)}")
    
    print("\n5. Resultados del análisis sintáctico:")
    correctas = sum(1 for l in ensamblador.lineas_analizadas if l['resultado'] == 'Correcta')
    incorrectas = len(ensamblador.lineas_analizadas) - correctas
    print(f"   - Líneas correctas: {correctas}")
    print(f"   - Líneas incorrectas: {incorrectas}")
    
    print("\n6. Tabla de símbolos:")
    if ensamblador.tabla_simbolos:
        print(f"   {'Símbolo':<20} {'Tipo':<10} {'Valor':<20} {'Tamaño':<10}")
        print("   " + "-" * 60)
        for simbolo in list(ensamblador.tabla_simbolos.values())[:10]:
            print(f"   {simbolo.nombre:<20} {simbolo.tipo:<10} {simbolo.valor:<20} {simbolo.tamanio:<10}")
    else:
        print("   (Sin símbolos encontrados)")
    
    print("\n7. Primeras líneas del análisis:")
    for analisis in ensamblador.lineas_analizadas[:10]:
        print(f"   Línea {analisis['numero']:3d}: {analisis['resultado']:<12} - {analisis['mensaje']}")
    
    print("\n" + "=" * 80)
    print("PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    try:
        test_ensamblador()
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
