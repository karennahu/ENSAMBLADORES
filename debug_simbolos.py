#!/usr/bin/env python3
"""
Script de depuración para la tabla de símbolos
"""

from ensamblador import Ensamblador8086, TipoToken

ensamblador = Ensamblador8086()
ensamblador.cargar_archivo("ejemplo.asm")

print("=" * 80)
print("DEPURACIÓN DE TABLA DE SÍMBOLOS")
print("=" * 80)

segmento_actual = None
i = 0

while i < len(ensamblador.lineas_codigo):
    linea = ensamblador.lineas_codigo[i].strip()
    linea_limpia = ensamblador.limpiar_comentarios(linea).strip()
    
    if not linea_limpia:
        i += 1
        continue
    
    tokens_linea = ensamblador.tokenizar_linea(linea_limpia, i + 1)
    if not tokens_linea:
        i += 1
        continue
    
    # Actualizar segmento
    if len(tokens_linea) >= 2:
        primer_token = tokens_linea[0].valor.upper()
        if '.STACK SEGMENT' in linea_limpia.upper():
            segmento_actual = 'STACK'
            print(f"\n→ Línea {i+1}: Entrando a segmento STACK")
        elif '.DATA SEGMENT' in linea_limpia.upper():
            segmento_actual = 'DATA'
            print(f"\n→ Línea {i+1}: Entrando a segmento DATA")
        elif '.CODE SEGMENT' in linea_limpia.upper():
            segmento_actual = 'CODE'
            print(f"\n→ Línea {i+1}: Entrando a segmento CODE")
        elif primer_token == 'ENDS':
            print(f"→ Línea {i+1}: Saliendo de segmento {segmento_actual}")
            segmento_actual = None
    
    # Verificar si es candidato para tabla de símbolos
    if segmento_actual == 'DATA':
        print(f"  Línea {i+1} (DATA): {linea_limpia[:60]}")
        print(f"    Tokens: {[t.valor for t in tokens_linea]}")
        print(f"    Tipos: {[t.tipo.value for t in tokens_linea]}")
        
        if len(tokens_linea) >= 3:
            print(f"    Tiene >=3 tokens: ✓")
            print(f"    Primer token es SIMBOLO: {'✓' if tokens_linea[0].tipo == TipoToken.SIMBOLO else '✗'}")
            
            if tokens_linea[0].tipo == TipoToken.SIMBOLO:
                print(f"    → AGREGANDO A TABLA: {tokens_linea[0].valor}")
                ensamblador.agregar_simbolo(tokens_linea)
        else:
            print(f"    Tiene <3 tokens: ✗")
    
    i += 1

print("\n" + "=" * 80)
print("TABLA DE SÍMBOLOS FINAL:")
print("=" * 80)

if ensamblador.tabla_simbolos:
    print(f"{'Símbolo':<20} {'Tipo':<10} {'Valor':<20} {'Tamaño':<10}")
    print("-" * 60)
    for simbolo in ensamblador.tabla_simbolos.values():
        print(f"{simbolo.nombre:<20} {simbolo.tipo:<10} {simbolo.valor:<20} {simbolo.tamanio:<10}")
else:
    print("(Tabla vacía)")
