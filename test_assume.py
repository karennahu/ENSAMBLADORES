#!/usr/bin/env python3
"""
Script de prueba para verificar que ASSUME se tokeniza correctamente
"""

from ensamblador import Ensamblador8086, TipoToken

def test_assume():
    print("=" * 80)
    print("PRUEBA: TOKENIZACIÓN DE ASSUME")
    print("=" * 80)
    
    ensamblador = Ensamblador8086()
    
    # Casos de prueba
    casos = [
        "assume cs:.code, ds:.data, ss:.stack",
        "assume cs:.code",
        "inicio:",
        "inicio: nop",
    ]
    
    for linea in casos:
        print(f"\nLínea: {linea}")
        tokens = ensamblador.tokenizar_linea(linea, 1)
        print(f"Tokens:")
        for i, token in enumerate(tokens):
            print(f"  {i+1}. '{token.valor}' -> {token.tipo.value}")
        
        # Verificar que no haya tokens NO_IDENTIFICADO
        no_identificados = [t for t in tokens if t.tipo == TipoToken.NO_IDENTIFICADO]
        if no_identificados:
            print(f"  ✗ ERROR: Tokens no identificados: {[t.valor for t in no_identificados]}")
        else:
            print(f"  ✓ Todos los tokens identificados correctamente")
    
    print("\n" + "=" * 80)
    print("VERIFICACIÓN ESPECÍFICA DE ASSUME")
    print("=" * 80)
    
    linea_assume = "assume cs:.code, ds:.data, ss:.stack"
    tokens = ensamblador.tokenizar_linea(linea_assume, 1)
    
    print(f"\nTokens de '{linea_assume}':")
    for i, token in enumerate(tokens):
        print(f"  {i+1}. '{token.valor}' -> {token.tipo.value}")
    
    # Verificaciones esperadas
    assert tokens[0].valor.upper() == 'ASSUME', f"Primer token debería ser ASSUME, no {tokens[0].valor}"
    assert tokens[0].tipo == TipoToken.PSEUDOINSTRUCCION, f"ASSUME debería ser pseudoinstrucción, no {tokens[0].tipo.value}"
    
    # Buscar registros
    registros_encontrados = [t for t in tokens if t.tipo == TipoToken.REGISTRO]
    print(f"\nRegistros encontrados: {[t.valor for t in registros_encontrados]}")
    
    # Buscar elementos compuestos (.code, .data, .stack)
    elementos_encontrados = [t for t in tokens if '.code' in t.valor.lower() or '.data' in t.valor.lower() or '.stack' in t.valor.lower()]
    print(f"Elementos con segmentos encontrados: {[t.valor for t in elementos_encontrados]}")
    
    no_identificados = [t for t in tokens if t.tipo == TipoToken.NO_IDENTIFICADO]
    if no_identificados:
        print(f"\n✗ FALLO: Hay {len(no_identificados)} tokens no identificados:")
        for t in no_identificados:
            print(f"  - '{t.valor}'")
    else:
        print(f"\n✓ ÉXITO: Todos los tokens de ASSUME identificados correctamente")

if __name__ == "__main__":
    try:
        test_assume()
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
