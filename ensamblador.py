#EQUIPO2 - Ensamblador 8086 con Codificación de Instrucciones
# Versión mejorada con análisis sintáctico basado en documentación oficial

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class TipoToken(Enum):
    PSEUDOINSTRUCCION = "Pseudoinstrucción"
    INSTRUCCION = "Instrucción"
    REGISTRO = "Registro"
    SIMBOLO = "Símbolo"
    CONSTANTE_DECIMAL = "Constante Numérica Decimal"
    CONSTANTE_HEXADECIMAL = "Constante Numérica Hexadecimal"
    CONSTANTE_BINARIA = "Constante Numérica Binaria"
    CONSTANTE_CARACTER = "Constante Caracter"
    NO_IDENTIFICADO = "Elemento no identificado"

@dataclass
class Token:
    valor: str
    tipo: TipoToken
    linea: int
    posicion: int

@dataclass
class Simbolo:
    nombre: str
    tipo: str
    valor: str
    tamanio: str
    direccion: str = ""


class Ensamblador8086:
    def __init__(self):
        # INSTRUCCIONES VÁLIDAS PERMITIDAS (solo las especificadas)
        # Sin operandos: CMC, CMPSB, NOP, POPA, AAD, AAM
        # Con 1 operando: MUL, INC, IDIV, INT
        # Con 2 operandos: AND, LEA, OR, XOR
        # Saltos: JNAE, JNE, JNLE, LOOPE, JA, JC
        self.instrucciones = {
            # Instrucciones sin operandos
            'CMC', 'CMPSB', 'NOP', 'POPA', 'AAD', 'AAM',
            # Instrucciones con 1 operando
            'MUL', 'INC', 'IDIV', 'INT',
            # Instrucciones con 2 operandos
            'AND', 'LEA', 'OR', 'XOR',
            # Saltos condicionales permitidos
            'JNAE', 'JNE', 'JNLE', 'LOOPE', 'JA', 'JC'
        }

        self.pseudoinstrucciones = {
            'SEGMENT', 'ENDS', 'END', 'DB', 'DW', 'DD', 'DQ', 'DT',
            'EQU', 'DUP', 'BYTE', 'PTR', 'WORD', 'DWORD', 'MACRO', 'ENDM', 
            'PROC', 'ENDP', 'ASSUME', 'ORG', 'OFFSET', 'MODEL', 'STACK',
            'SMALL', 'MEDIUM', 'LARGE', 'COMPACT', 'HUGE', 'FLAT'
        }

        # Registros 8086 (8-bit, 16-bit y segmento)
        self.registros_8bit = {'AL', 'AH', 'BL', 'BH', 'CL', 'CH', 'DL', 'DH'}
        self.registros_16bit = {'AX', 'BX', 'CX', 'DX', 'SI', 'DI', 'BP', 'SP'}
        self.registros_segmento = {'CS', 'DS', 'ES', 'SS'}
        self.registros = self.registros_8bit | self.registros_16bit | self.registros_segmento | {'IP', 'FLAGS'}

        # Codificación de registros según el PDF
        self.reg_codigo = {
            'AL': '000', 'CL': '001', 'DL': '010', 'BL': '011',
            'AH': '100', 'CH': '101', 'DH': '110', 'BH': '111',
            'AX': '000', 'CX': '001', 'DX': '010', 'BX': '011',
            'SP': '100', 'BP': '101', 'SI': '110', 'DI': '111'
        }
        
        self.regs2_codigo = {'ES': '00', 'CS': '01', 'SS': '10', 'DS': '11'}

        # Instrucciones que NO requieren operandos
        self.instrucciones_sin_operandos = {
            'CMC', 'CMPSB', 'NOP', 'POPA', 'AAD', 'AAM'
        }
        
        # Instrucciones que requieren 1 operando
        self.instrucciones_1_operando = {
            'MUL', 'INC', 'IDIV', 'INT',
            # Saltos permitidos
            'JNAE', 'JNE', 'JNLE', 'LOOPE', 'JA', 'JC'
        }
        
        # Instrucciones que requieren 2 operandos
        self.instrucciones_2_operandos = {
            'AND', 'LEA', 'OR', 'XOR'
        }

        self.tokens: List[Token] = []
        self.tabla_simbolos = {}
        self.lineas_codigo: List[str] = []
        self.lineas_analizadas: List[dict] = []
        self.lineas_codificadas: List[dict] = []

    def limpiar_comentarios(self, linea: str) -> str:
        pos = linea.find(';')
        return linea[:pos] if pos != -1 else linea

    def tiene_string_invalido(self, linea: str) -> bool:
        """Verifica si hay strings sin cerrar o paréntesis/corchetes desbalanceados"""
        if linea.count('[') != linea.count(']'):
            return True
        if linea.count('(') != linea.count(')'):
            return True
        return False
    
    def detectar_string_sin_cerrar(self, linea: str) -> Optional[str]:
        """Detecta si hay un string que empieza pero no termina"""
        # Buscar comillas dobles sin cerrar
        en_string_doble = False
        inicio_string = -1
        for i, c in enumerate(linea):
            if c == '"' and (i == 0 or linea[i-1] != '\\'):
                if not en_string_doble:
                    en_string_doble = True
                    inicio_string = i
                else:
                    en_string_doble = False
        if en_string_doble:
            return linea[inicio_string:]
        
        # Buscar comillas simples sin cerrar
        en_string_simple = False
        for i, c in enumerate(linea):
            if c == "'" and (i == 0 or linea[i-1] != '\\'):
                if not en_string_simple:
                    en_string_simple = True
                    inicio_string = i
                else:
                    en_string_simple = False
        if en_string_simple:
            return linea[inicio_string:]
        
        return None

    def tokenizar_linea(self, linea: str, num_linea: int) -> List[Token]:
        """
        Tokeniza una línea de código ensamblador.
        Separadores: espacio, coma, dos puntos (excepto en etiquetas)
        Elementos compuestos que NO se separan:
        - .code segment, .data segment, .stack segment
        - byte ptr, word ptr
        - número dup(valor)
        - [xxx] (direccionamiento)
        - "xxx" y 'xxx' (strings)
        """
        linea_sin_com = self.limpiar_comentarios(linea).strip()
        if not linea_sin_com:
            return []
        
        # Detectar string sin cerrar
        string_sin_cerrar = self.detectar_string_sin_cerrar(linea_sin_com)
        if string_sin_cerrar:
            # Tokenizar lo que está antes del string sin cerrar
            pos_string = linea_sin_com.find(string_sin_cerrar)
            parte_antes = linea_sin_com[:pos_string].strip()
            tokens = []
            if parte_antes:
                tokens = self._tokenizar_parte(parte_antes, num_linea)
            # Agregar el string sin cerrar como elemento no identificado
            tokens.append(Token(string_sin_cerrar.strip(), TipoToken.NO_IDENTIFICADO, num_linea, len(tokens)))
            return tokens
        
        # Verificar paréntesis/corchetes desbalanceados
        if self.tiene_string_invalido(linea_sin_com):
            return [Token(linea_sin_com, TipoToken.NO_IDENTIFICADO, num_linea, 0)]
        
        return self._tokenizar_parte(linea_sin_com, num_linea)
    
    def _tokenizar_parte(self, linea: str, num_linea: int) -> List[Token]:
        """Tokeniza una parte de línea (sin strings sin cerrar)"""
        texto_mod = linea
        elementos = []
        contador = 0
        
        # === PASO 1: Extraer y proteger elementos compuestos ===
        
        # Patrones de elementos compuestos (en orden de prioridad)
        patrones_compuestos = [
            # Segmentos
            (r'\.code\s+segment', 'COMP_SEG'),
            (r'\.data\s+segment', 'COMP_SEG'),
            (r'\.stack\s+segment', 'COMP_SEG'),
            # PTR
            (r'byte\s+ptr', 'COMP_PTR'),
            (r'word\s+ptr', 'COMP_PTR'),
            (r'dword\s+ptr', 'COMP_PTR'),
            # DUP con paréntesis - SOLO el dup(valor), NO el número antes
            # El número se tokeniza por separado
            (r'dup\s*\([^)]*\)', 'COMP_DUP'),
            # Direccionamiento con corchetes
            (r'\[[^\]]*\]', 'COMP_BRACKET'),
            # Strings con comillas dobles
            (r'"[^"]*"', 'COMP_STRING'),
            # Strings con comillas simples  
            (r"'[^']*'", 'COMP_CHAR'),
        ]
        
        for patron, prefijo in patrones_compuestos:
            for match in list(re.finditer(patron, texto_mod, re.IGNORECASE))[::-1]:
                elem = match.group(0)
                marcador = f'{prefijo}_{contador}'
                elementos.append((marcador, elem))
                texto_mod = texto_mod[:match.start()] + f' {marcador} ' + texto_mod[match.end():]
                contador += 1
        
        # === PASO 2: Extraer etiquetas (terminan con :) ===
        etiquetas = []
        # Buscar etiquetas al inicio de la línea o después de espacio
        patron_etiq = r'(?:^|(?<=\s))([A-Za-z_][A-Za-z0-9_]*):(?=\s|$|,)'
        for match in re.finditer(patron_etiq, texto_mod):
            marcador = f'ETIQ_{len(etiquetas)}'
            etiqueta_completa = match.group(1) + ':'
            etiquetas.append((marcador, etiqueta_completa))
            texto_mod = texto_mod[:match.start()] + f' {marcador} ' + texto_mod[match.end():]
        
        # === PASO 3: Separar por espacio, coma ===
        # Primero reemplazamos comas por espacios para separar
        texto_sep = texto_mod.replace(',', ' ')
        
        # Separar por espacios
        partes = texto_sep.split()
        
        # === PASO 4: Restaurar elementos compuestos y etiquetas ===
        tokens_str = []
        for parte in partes:
            parte = parte.strip()
            if not parte:
                continue
            
            # Restaurar etiquetas
            restaurado = False
            for marcador, original in etiquetas:
                if marcador == parte:
                    tokens_str.append(original)
                    restaurado = True
                    break
            
            if restaurado:
                continue
            
            # Restaurar elementos compuestos
            for marcador, original in elementos:
                if marcador == parte:
                    tokens_str.append(original)
                    restaurado = True
                    break
            
            if not restaurado:
                tokens_str.append(parte)
        
        # === PASO 5: Crear tokens con sus tipos ===
        tokens = []
        for pos, token_str in enumerate(tokens_str):
            tipo = self.identificar_tipo_token(token_str)
            tokens.append(Token(token_str, tipo, num_linea, pos))
        
        return tokens

    def identificar_tipo_token(self, token: str) -> TipoToken:
        t = token.strip()
        tu = t.upper()
        
        if not t:
            return TipoToken.NO_IDENTIFICADO

        # ===== ELEMENTOS COMPUESTOS VÁLIDOS =====
        if re.match(r'^\.(?:CODE|DATA|STACK)\s+SEGMENT$', t, re.IGNORECASE):
            return TipoToken.PSEUDOINSTRUCCION
        if re.match(r'^(?:BYTE|WORD|DWORD)\s+PTR$', t, re.IGNORECASE):
            return TipoToken.PSEUDOINSTRUCCION
        
        # DUP(valor) - es pseudoinstrucción (el número se tokeniza por separado)
        if re.match(r'^DUP\s*\([^)]*\)$', t, re.IGNORECASE):
            return TipoToken.PSEUDOINSTRUCCION
        
        # Direccionamiento con corchetes - es un modo de direccionamiento válido
        if re.match(r'^\[[^\]]+\]$', t):
            return TipoToken.SIMBOLO  # Tratarlo como símbolo de direccionamiento

        # ===== CONSTANTES DE CARACTER (strings) =====
        if re.match(r'^"[^"]*"$', t) or re.match(r"^'[^']*'$", t):
            return TipoToken.CONSTANTE_CARACTER
        
        if (t.startswith('"') and not t.endswith('"')) or \
           (t.startswith("'") and not t.endswith("'")):
            return TipoToken.NO_IDENTIFICADO

        # ===== INSTRUCCIONES =====
        if tu in self.instrucciones:
            return TipoToken.INSTRUCCION

        # ===== PSEUDOINSTRUCCIONES =====
        if tu in self.pseudoinstrucciones:
            return TipoToken.PSEUDOINSTRUCCION

        # ===== REGISTROS =====
        if tu in self.registros:
            return TipoToken.REGISTRO

        # ===== CONSTANTES NUMÉRICAS =====
        
        # CONSTANTE BINARIA: solo 0s y 1s, termina con B
        if re.match(r'^[01]+[Bb]$', t):
            return TipoToken.CONSTANTE_BINARIA
        
        # CONSTANTE HEXADECIMAL: DEBE empezar con 0 y terminar con H
        # Ejemplos válidos: 0h, 0Fh, 032h, 0ABCDh
        # Ejemplos inválidos: 45H (no empieza con 0), Fh (empieza con letra)
        if re.match(r'^0[0-9A-Fa-f]*[Hh]$', t):
            return TipoToken.CONSTANTE_HEXADECIMAL
        
        # Hexadecimal inválido (no empieza con 0 pero termina con H)
        if re.match(r'^[1-9][0-9A-Fa-f]*[Hh]$', t):
            return TipoToken.NO_IDENTIFICADO
        
        # Hexadecimal inválido (empieza con letra)
        if re.match(r'^[A-Fa-f][0-9A-Fa-f]*[Hh]$', t):
            return TipoToken.NO_IDENTIFICADO
        
        # CONSTANTE DECIMAL (puede tener sufijo D)
        if re.match(r'^\d+[Dd]?$', t):
            return TipoToken.CONSTANTE_DECIMAL
        
        # Número con sufijo inválido
        if re.match(r'^\d+[A-Za-z]+$', t) and not re.match(r'^0[0-9A-Fa-f]*[Hh]$', t) and not re.match(r'^[01]+[Bb]$', t):
            return TipoToken.NO_IDENTIFICADO

        # ===== ETIQUETAS (terminan con :) =====
        if t.endswith(':'):
            nombre = t[:-1]
            if len(nombre) > 31:
                return TipoToken.NO_IDENTIFICADO
            # Debe empezar con letra o guion bajo
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', nombre):
                return TipoToken.SIMBOLO
            return TipoToken.NO_IDENTIFICADO

        # ===== SÍMBOLOS =====
        # @data, @code, etc.
        if re.match(r'^@[A-Za-z_][A-Za-z0-9_]*$', t):
            return TipoToken.SIMBOLO
            
        if re.match(r'^\.[A-Za-z_][A-Za-z0-9_]*$', t):
            if len(t) <= 32:
                return TipoToken.SIMBOLO
            return TipoToken.NO_IDENTIFICADO
        
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t):
            if len(t) <= 31:
                return TipoToken.SIMBOLO
            return TipoToken.NO_IDENTIFICADO

        # ===== OPERADORES VÁLIDOS =====
        # Coma, dos puntos, operadores aritméticos, signo de interrogación
        if t in [',', ':', '+', '-', '*', '/']:
            return TipoToken.SIMBOLO  # Son símbolos operadores válidos
        
        # Signo de interrogación (variable sin inicializar)
        if t == '?':
            return TipoToken.SIMBOLO
        
        # Paréntesis y corchetes sueltos son inválidos
        if t in ['[', ']', '(', ')']:
            return TipoToken.NO_IDENTIFICADO

        return TipoToken.NO_IDENTIFICADO

    def es_operando_valido(self, token: Token) -> bool:
        """Verifica si un token es un operando válido para una instrucción"""
        if token.tipo in [TipoToken.REGISTRO, TipoToken.SIMBOLO, 
                          TipoToken.CONSTANTE_DECIMAL, TipoToken.CONSTANTE_HEXADECIMAL,
                          TipoToken.CONSTANTE_BINARIA, TipoToken.CONSTANTE_CARACTER]:
            return True
        # BYTE PTR, WORD PTR seguido de dirección
        if token.tipo == TipoToken.PSEUDOINSTRUCCION:
            tu = token.valor.upper()
            if 'PTR' in tu or 'OFFSET' in tu:
                return True
        return False

    def es_direccionamiento_valido(self, operando: str) -> bool:
        """Valida modos de direccionamiento según el PDF"""
        op = operando.strip()
        
        # Registro directo
        if op.upper() in self.registros:
            return True
        
        # Inmediato (constante)
        if re.match(r'^\d+[DHBdhb]?$', op) or re.match(r'^0[0-9A-Fa-f]+[Hh]$', op):
            return True
        
        # Directo (variable)
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', op):
            return True
        
        # Indirecto con registro [BX], [SI], [DI], [BP]
        if re.match(r'^\[(BX|SI|DI|BP)\]$', op, re.IGNORECASE):
            return True
        
        # Base + desplazamiento [BX+4], [BP-2]
        if re.match(r'^\[(BX|BP|SI|DI)\s*[\+\-]\s*\d+\]$', op, re.IGNORECASE):
            return True
        
        # Base + índice [BX+SI], [BP+DI]
        if re.match(r'^\[(BX|BP)\s*\+\s*(SI|DI)\]$', op, re.IGNORECASE):
            return True
        
        # Base + índice + desplazamiento [BX+SI+4]
        if re.match(r'^\[(BX|BP)\s*\+\s*(SI|DI)\s*[\+\-]\s*\d+\]$', op, re.IGNORECASE):
            return True
        
        # Variable con offset
        if re.match(r'^OFFSET\s+[A-Za-z_][A-Za-z0-9_]*$', op, re.IGNORECASE):
            return True
        
        # BYTE/WORD PTR [direccion]
        if re.match(r'^(BYTE|WORD|DWORD)\s+PTR\s+\[.+\]$', op, re.IGNORECASE):
            return True
        
        # String literal
        if re.match(r'^["\'].*["\']$', op):
            return True
        
        return False

    def validar_instruccion(self, instr_texto: str) -> Tuple[bool, str]:
        instr = instr_texto.strip().upper()
        if not instr:
            return False, "Instrucción vacía"
        if instr not in self.instrucciones:
            return False, f"Instrucción no reconocida: {instr}"
        return True, "OK"

    def cargar_archivo(self, ruta: str) -> bool:
        try:
            path = Path(ruta)
            if not path.exists():
                return False
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.lineas_codigo = [ln.rstrip('\n') for ln in f]
            self.tokens = []
            for num, linea in enumerate(self.lineas_codigo, 1):
                self.tokens.extend(self.tokenizar_linea(linea, num))
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def analizar_sintaxis(self):
        self.lineas_analizadas = []
        self.tabla_simbolos = {}
        segmento = None

        for i, linea_raw in enumerate(self.lineas_codigo):
            linea = linea_raw.strip()
            if not linea or linea.startswith(';'):
                continue
            
            linea_limpia = self.limpiar_comentarios(linea).strip()
            if not linea_limpia:
                continue

            tokens_linea = self.tokenizar_linea(linea_limpia, i + 1)
            if not tokens_linea:
                continue

            primer = tokens_linea[0].valor.upper()

            if '.STACK SEGMENT' in linea_limpia.upper():
                segmento = 'STACK'
            elif '.DATA SEGMENT' in linea_limpia.upper():
                segmento = 'DATA'
            elif '.CODE SEGMENT' in linea_limpia.upper():
                segmento = 'CODE'
            elif primer == 'ENDS':
                segmento = None

            # Primero validar la línea
            resultado, mensaje = self.validar_linea(tokens_linea, segmento)

            # Solo agregar etiquetas a la tabla si la línea es correcta
            if tokens_linea[0].tipo == TipoToken.SIMBOLO and tokens_linea[0].valor.endswith(':'):
                if resultado == "Correcta":
                    nombre = tokens_linea[0].valor.replace(':', '')
                    self.tabla_simbolos[nombre] = Simbolo(nombre, 'Etiqueta', '', '')

            # Solo agregar variables/constantes a la tabla si la línea es correcta
            if segmento == 'DATA' and len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
                if resultado == "Correcta":
                    self.agregar_simbolo(tokens_linea)

            self.lineas_analizadas.append({
                'numero': i + 1,
                'linea': linea_limpia,
                'resultado': resultado,
                'mensaje': mensaje
            })

    def validar_linea(self, tokens: List[Token], segmento: Optional[str]) -> Tuple[str, str]:
        if not tokens:
            return "Incorrecta", "Línea vacía"

        linea_texto = ' '.join([t.valor for t in tokens])
        linea_upper = linea_texto.upper()

        # Validar inicio de segmentos - DEBE SER EXACTAMENTE .stack/.data/.code segment
        # Primero verificar si es una declaración de segmento
        if re.search(r'\.\w+\s+SEGMENT', linea_upper):
            # Verificar que sea EXACTAMENTE uno de los válidos
            if re.match(r'^\.STACK\s+SEGMENT$', linea_upper):
                return "Correcta", "Inicio de segmento de pila"
            elif re.match(r'^\.DATA\s+SEGMENT$', linea_upper):
                return "Correcta", "Inicio de segmento de datos"
            elif re.match(r'^\.CODE\s+SEGMENT$', linea_upper):
                return "Correcta", "Inicio de segmento de código"
            else:
                # Declaración de segmento incorrecta (ej: .stacks segment, .datas segment)
                return "Incorrecta", f"Declaración de segmento inválida: '{linea_texto}'. Use: .stack segment, .data segment o .code segment"
        
        if tokens[0].valor.upper() == 'ENDS':
            return "Correcta", "Fin de segmento"
        if tokens[0].valor.upper() == 'END':
            return "Correcta", "Fin de programa"

        # Directivas de modelo (.model small, etc.)
        if tokens[0].valor.upper() == '.MODEL' or tokens[0].valor.lower() == '.model':
            return "Correcta", "Directiva de modelo"
        if tokens[0].valor.upper() == '.STACK' and len(tokens) == 2:
            # .STACK 256 (forma alternativa sin SEGMENT)
            return "Correcta", "Directiva de pila"

        if segmento == 'STACK':
            return self.validar_segmento_pila(tokens)
        elif segmento == 'DATA':
            return self.validar_segmento_datos(tokens)
        elif segmento == 'CODE':
            return self.validar_segmento_codigo(tokens)

        return "Incorrecta", "Línea fuera de segmento"

    def validar_segmento_pila(self, tokens: List[Token]) -> Tuple[str, str]:
        """
        Valida declaraciones en el segmento de pila.
        Solo se permite declarar espacio para la pila usando DW con DUP.
        """
        if len(tokens) < 2:
            return "Incorrecta", "Definición de pila incompleta"
        
        directiva = tokens[0].valor.upper()
        
        # Solo se permite DW en el segmento de pila
        if directiva != 'DW':
            # Verificar si es una instrucción (no permitida en .stack)
            if directiva in self.instrucciones:
                return "Incorrecta", f"Instrucción '{directiva}' no permitida en segmento de pila"
            # Verificar si es una declaración de datos (debería estar en .data)
            if directiva in ['DB', 'DD', 'DQ', 'DT', 'EQU']:
                return "Incorrecta", f"'{directiva}' no permitido en segmento de pila. Use solo DW para reservar espacio"
            return "Incorrecta", f"'{directiva}' no válido en segmento de pila. Solo se permite DW cantidad DUP(?)"
        
        # DW cantidad DUP(?) o DW cantidad
        valor_str = ' '.join([t.valor for t in tokens[1:]])
        
        # Validar formato: número DUP(valor) - preferido
        if re.match(r'^\d+\s+DUP\s*\([^)]+\)$', valor_str, re.IGNORECASE):
            return "Correcta", "Reserva de espacio en pila con DUP"
        
        # Validar formato: solo número (menos común pero válido)
        if re.match(r'^\d+$', valor_str):
            return "Correcta", "Reserva de espacio en pila"
        
        # DUP sin número antes
        if re.match(r'^DUP\s*\([^)]+\)$', valor_str, re.IGNORECASE):
            return "Incorrecta", "DUP requiere cantidad antes: DW cantidad DUP(?)"
        
        return "Incorrecta", f"Formato inválido en pila: {valor_str}. Use: DW cantidad DUP(?)"

    def validar_segmento_datos(self, tokens: List[Token]) -> Tuple[str, str]:
        """
        Valida declaraciones en el segmento de datos según el PDF:
        Solo se permiten: variables, constantes, cadenas, arreglos/buffers, tablas
        - nombre DB/DW/DD valor
        - nombre DB 'string', 0
        - nombre DB cantidad DUP(valor)
        - nombre EQU valor
        """
        if len(tokens) < 2:
            return "Incorrecta", "Definición de datos incompleta"
        
        # Verificar si es una instrucción (no permitida en .data)
        primer_token = tokens[0].valor.upper()
        if primer_token in self.instrucciones:
            return "Incorrecta", f"Instrucción '{primer_token}' no permitida en segmento de datos"
        
        # Verificar si es una etiqueta de código (no permitida en .data)
        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            return "Incorrecta", "Etiquetas de código no permitidas en segmento de datos"
        
        # Verificar si el primer token es un número (error: el nombre debe empezar con letra)
        if tokens[0].tipo in [TipoToken.CONSTANTE_DECIMAL, TipoToken.CONSTANTE_HEXADECIMAL, TipoToken.CONSTANTE_BINARIA]:
            return "Incorrecta", f"Nombre de variable no puede empezar con número: '{tokens[0].valor}'"
        
        # Verificar si algún token es no identificado
        for tok in tokens:
            if tok.tipo == TipoToken.NO_IDENTIFICADO:
                return "Incorrecta", f"Elemento no identificado: '{tok.valor}'"
        
        if len(tokens) < 3:
            return "Incorrecta", "Definición de datos incompleta (requiere: nombre directiva valor)"
        
        # El primer token debe ser un símbolo válido (nombre de variable)
        if tokens[0].tipo != TipoToken.SIMBOLO:
            return "Incorrecta", f"Nombre de variable inválido: '{tokens[0].valor}'"
        
        nombre = tokens[0].valor
        # Verificar que el nombre empiece con letra o guion bajo
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', nombre):
            return "Incorrecta", f"Nombre de variable inválido: '{nombre}' (debe empezar con letra o _)"
        
        if len(nombre) > 31:
            return "Incorrecta", f"Nombre de variable muy largo (máx 31 caracteres)"
        
        # El segundo token debe ser una directiva de datos
        directiva = tokens[1].valor.upper()
        directivas_validas = ['DB', 'DW', 'DD', 'DQ', 'DT', 'EQU']
        if directiva not in directivas_validas:
            # Verificar si es una instrucción
            if directiva in self.instrucciones:
                return "Incorrecta", f"Instrucción '{directiva}' no permitida en segmento de datos"
            return "Incorrecta", f"Directiva inválida: '{tokens[1].valor}'. Use: {', '.join(directivas_validas)}"
        
        # Validar el valor/expresión
        valor_tokens = tokens[2:]
        
        # Reconstruir valor_str - si son múltiples valores numéricos, unirlos con coma
        if len(valor_tokens) > 1 and all(t.tipo in [TipoToken.CONSTANTE_DECIMAL, TipoToken.CONSTANTE_HEXADECIMAL, 
                                                      TipoToken.CONSTANTE_BINARIA] or t.valor == '?' 
                                          for t in valor_tokens):
            valor_str = ', '.join([t.valor for t in valor_tokens])
        else:
            valor_str = ' '.join([t.valor for t in valor_tokens])
        
        # === Validar EQU ===
        if directiva == 'EQU':
            # EQU puede tener constantes numéricas o expresiones
            if re.match(r'^\d+[DHBdhb]?$', valor_str):  # Decimal, hex, binario
                return "Correcta", f"Constante {nombre} definida"
            if re.match(r'^0[0-9A-Fa-f]+[Hh]$', valor_str):
                return "Correcta", f"Constante hexadecimal {nombre} definida"
            if re.match(r"^'[^']*'$", valor_str) or re.match(r'^"[^"]*"$', valor_str):
                return "Correcta", f"Constante de caracter {nombre} definida"
            return "Incorrecta", f"Valor inválido para EQU: {valor_str}"
        
        # === Validar DUP ===
        if 'DUP' in valor_str.upper():
            # Formato correcto: número DUP(valor)
            if re.match(r'^\d+\s+DUP\s*\([^)]+\)$', valor_str, re.IGNORECASE):
                return "Correcta", f"Array/Buffer {nombre} definido con DUP"
            # Errores comunes
            if not re.search(r'\d+\s+DUP', valor_str, re.IGNORECASE):
                return "Incorrecta", "DUP requiere un número antes: cantidad DUP(valor)"
            if '(' not in valor_str or ')' not in valor_str:
                return "Incorrecta", "DUP requiere paréntesis: cantidad DUP(valor)"
            return "Incorrecta", f"Sintaxis DUP inválida: {valor_str}"
        
        # === Validar strings ===
        if re.search(r'["\']', valor_str):
            # Verificar strings cerrados
            if (valor_str.count('"') % 2 != 0) or (valor_str.count("'") % 2 != 0):
                return "Incorrecta", "Cadena de texto sin cerrar (faltan comillas)"
            # String válido (puede terminar con , 0 para null-terminated)
            if re.match(r'^["\'][^"\']*["\'](\s*,\s*0)?$', valor_str):
                return "Correcta", f"Cadena {nombre} definida"
            # Lista de caracteres o strings
            if re.match(r'^["\'][^"\']*["\'](\s*,\s*["\'][^"\']*["\'])*(\s*,\s*0)?$', valor_str):
                return "Correcta", f"Cadena {nombre} definida"
            return "Correcta", f"Cadena {nombre} definida"
        
        # === Validar valor numérico ===
        if valor_str.strip() == '?':
            return "Correcta", f"Variable {nombre} sin inicializar"
        
        # Constante decimal
        if re.match(r'^\d+[Dd]?$', valor_str):
            return "Correcta", f"Variable {nombre} inicializada"
        
        # Constante hexadecimal - DEBE empezar con 0
        if re.match(r'^0[0-9A-Fa-f]*[Hh]$', valor_str):
            return "Correcta", f"Variable {nombre} inicializada (hex)"
        
        # Hexadecimal inválido (no empieza con 0)
        if re.match(r'^[1-9][0-9A-Fa-f]*[Hh]$', valor_str):
            return "Incorrecta", f"Hexadecimal inválido: '{valor_str}' (debe empezar con 0)"
        
        # Constante binaria
        if re.match(r'^[01]+[Bb]$', valor_str):
            return "Correcta", f"Variable {nombre} inicializada (bin)"
        
        # Caracter individual
        if re.match(r"^'[^']'$", valor_str):
            return "Correcta", f"Variable {nombre} inicializada (char)"
        
        # Lista de valores separados por coma (tabla de datos)
        if ',' in valor_str:
            # Verificar que los elementos sean válidos (números, ?, o strings)
            partes = [p.strip() for p in valor_str.split(',')]
            for parte in partes:
                if not parte:
                    continue
                # Verificar si es válido: número, ?, string entre comillas
                if parte == '?':
                    continue
                if re.match(r'^\d+[Dd]?$', parte):
                    continue
                # Hexadecimal debe empezar con 0
                if re.match(r'^0[0-9A-Fa-f]*[Hh]$', parte):
                    continue
                if re.match(r'^["\'][^"\']*["\']$', parte):
                    continue
                # Binario
                if re.match(r'^[01]+[Bb]$', parte):
                    continue
                # Si llegamos aquí, hay un elemento inválido
                return "Incorrecta", f"Elemento inválido en lista: '{parte}'"
            return "Correcta", f"Tabla {nombre} definida"
        
        # === Detectar texto sin comillas (error común) ===
        if len(valor_tokens) > 1:
            todas_palabras = all(
                t.tipo == TipoToken.SIMBOLO or t.tipo == TipoToken.NO_IDENTIFICADO 
                for t in valor_tokens
            )
            if todas_palabras:
                return "Incorrecta", f"Texto sin comillas. Use: {nombre} {directiva} \"{valor_str}\""
        
        if len(valor_tokens) == 1 and valor_tokens[0].tipo == TipoToken.SIMBOLO:
            val = valor_tokens[0].valor
            if not val.upper() in self.registros and not val.upper() in self.pseudoinstrucciones:
                if len(val) > 1 and val.isalpha():
                    return "Incorrecta", f"¿Texto sin comillas? Use: {nombre} {directiva} \"{val}\""
        
        return "Incorrecta", f"Valor inválido para {directiva}: '{valor_str}'"

    def validar_segmento_codigo(self, tokens: List[Token]) -> Tuple[str, str]:
        """
        Valida instrucciones en el segmento de código según los PDFs:
        - Instrucciones sin operandos: NOP, RET, etc.
        - Instrucciones con 1 operando: PUSH, POP, INC, JMP, etc.
        - Instrucciones con 2 operandos: MOV, ADD, CMP, etc.
        """
        if not tokens:
            return "Correcta", "Línea vacía"

        tokens_val = tokens
        msg_etiq = ""

        # Verificar si hay etiqueta al inicio
        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            msg_etiq = f"Etiqueta '{tokens[0].valor[:-1]}' definida"
            if len(tokens) == 1:
                return "Correcta", msg_etiq
            tokens_val = tokens[1:]

        if not tokens_val:
            return "Correcta", msg_etiq if msg_etiq else "Línea vacía"

        primer_token = tokens_val[0]
        instr = primer_token.valor.upper()

        # === Verificar que NO sea una declaración de datos (no permitido en .code) ===
        directivas_datos = ['DB', 'DW', 'DD', 'DQ', 'DT', 'EQU']
        if len(tokens_val) >= 2:
            segundo_token = tokens_val[1].valor.upper()
            if segundo_token in directivas_datos:
                return "Incorrecta", f"Declaración de datos no permitida en segmento de código. Use segmento .data"
        
        # Si el primer token es una directiva de datos
        if instr in directivas_datos:
            return "Incorrecta", f"'{instr}' no permitido en segmento de código. Use segmento .data"

        # === Pseudoinstrucciones permitidas en código ===
        # ASSUME, PROC, ENDP, ORG son válidos en .code
        if instr in ['ASSUME', 'PROC', 'ENDP', 'ORG']:
            msg = f"Pseudoinstrucción {instr} válida"
            return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg

        # === Validar que sea una instrucción ===
        if instr not in self.instrucciones:
            # Verificar si parece una declaración de datos mal ubicada
            if primer_token.tipo == TipoToken.SIMBOLO:
                if len(tokens_val) >= 2 and tokens_val[1].valor.upper() in directivas_datos:
                    return "Incorrecta", "Declaración de datos no permitida en segmento de código"
            return "Incorrecta", f"'{primer_token.valor}' no es una instrucción válida"

        # Obtener operandos (excluyendo comas)
        operandos = [t for t in tokens_val[1:] if t.valor != ',']
        num_operandos = len(operandos)

        # === Verificar que los símbolos usados estén declarados ===
        # (excepto registros, constantes numéricas y etiquetas de código)
        for op in operandos:
            op_val = op.valor
            op_upper = op_val.upper()
            
            # Ignorar registros
            if op_upper in self.registros:
                continue
            
            # Ignorar constantes numéricas
            if op.tipo in [TipoToken.CONSTANTE_DECIMAL, TipoToken.CONSTANTE_HEXADECIMAL, 
                          TipoToken.CONSTANTE_BINARIA, TipoToken.CONSTANTE_CARACTER]:
                continue
            
            # Ignorar @data y similares
            if op_val.startswith('@'):
                continue
            
            # Ignorar direccionamiento con corchetes (se valida el contenido interno)
            if op_val.startswith('[') and op_val.endswith(']'):
                # Extraer el contenido del corchete y verificar
                contenido = op_val[1:-1].strip()
                # Si contiene solo registros, es válido
                partes = re.split(r'[\+\-\*]', contenido)
                for parte in partes:
                    parte = parte.strip().upper()
                    if parte and parte not in self.registros:
                        # Podría ser un desplazamiento numérico
                        if not re.match(r'^\d+[HhDdBb]?$', parte) and not re.match(r'^[0-9][0-9A-Fa-f]*[Hh]$', parte):
                            # Es un símbolo, verificar si está declarado
                            if parte.lower() not in [s.lower() for s in self.tabla_simbolos.keys()]:
                                return "Incorrecta", f"Símbolo '{parte}' no declarado en segmento de datos"
                continue
            
            # Si es un símbolo (posible variable o etiqueta)
            if op.tipo == TipoToken.SIMBOLO:
                # Verificar si está en la tabla de símbolos
                simbolo_encontrado = False
                for nombre_simbolo in self.tabla_simbolos.keys():
                    if nombre_simbolo.lower() == op_val.lower():
                        simbolo_encontrado = True
                        break
                
                if not simbolo_encontrado:
                    # Podría ser una etiqueta que aún no se ha declarado (salto hacia adelante)
                    # Para saltos, permitimos etiquetas no declaradas aún
                    if instr in ['JNAE', 'JNE', 'JNLE', 'LOOPE', 'JA', 'JC']:
                        continue  # Los saltos pueden referenciar etiquetas adelante
                    
                    return "Incorrecta", f"Símbolo '{op_val}' no declarado en segmento de datos"

        # === Instrucciones sin operandos ===
        if instr in self.instrucciones_sin_operandos:
            if num_operandos > 0:
                return "Incorrecta", f"{instr} no requiere operandos"
            msg = f"Instrucción {instr} válida"
            return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg

        # === Instrucciones con 1 operando ===
        if instr in self.instrucciones_1_operando:
            if num_operandos < 1:
                return "Incorrecta", f"{instr} requiere 1 operando"
            if num_operandos > 1:
                # Permitir BYTE PTR [x] como un solo operando
                operando_completo = ' '.join([t.valor for t in operandos])
                if not re.match(r'^(BYTE|WORD)\s+PTR\s+', operando_completo, re.IGNORECASE):
                    pass  # Ser más permisivo
            msg = f"Instrucción {instr} válida"
            return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg

        # === Instrucciones con 2 operandos ===
        if instr in self.instrucciones_2_operandos:
            if num_operandos < 2:
                return "Incorrecta", f"{instr} requiere 2 operandos"
            
            # Validaciones específicas por instrucción
            op1 = operandos[0].valor.upper()
            op2 = operandos[1].valor.upper() if len(operandos) > 1 else ""
            
            # LEA solo acepta registro como destino
            if instr == 'LEA':
                if op1 not in self.registros_16bit:
                    return "Incorrecta", "LEA requiere registro de 16 bits como destino"
            
            msg = f"Instrucción {instr} válida"
            return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg

        # === Instrucción válida por defecto ===
        msg = f"Instrucción {instr} válida"
        return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg

    def agregar_simbolo(self, tokens_linea: List[Token]):
        nombre = tokens_linea[0].valor.rstrip(":")

        if tokens_linea[0].valor.endswith(":"):
            tipo = "Etiqueta"
            tamanio = ""
            valor = ""
        else:
            directiva = tokens_linea[1].valor.upper()
            tipo = "Constante" if directiva == "EQU" else "Variable"
            tamanio = directiva if directiva in ("DB", "DW", "DD", "DQ", "DT") else ""
            raw_valor = " ".join(tok.valor for tok in tokens_linea[2:])

            if re.match(r'^0[0-9A-F]+H$', raw_valor.upper()):
                valor = raw_valor.upper()
            elif re.match(r'^[01]+[Bb]$', raw_valor):
                valor = raw_valor.upper()
            else:
                valor = raw_valor

        self.tabla_simbolos[nombre] = Simbolo(nombre, tipo, valor, tamanio)

    # =========================================================================
    # CODIFICACIÓN DE INSTRUCCIONES Y CONTADOR DE PROGRAMA
    # =========================================================================
    
    def calcular_tamano_dato(self, tokens: List[Token]) -> int:
        if len(tokens) < 3:
            return 0
        directiva = tokens[1].valor.upper()
        valor_str = ' '.join([t.valor for t in tokens[2:]])
        
        tam_base = {'DB': 1, 'DW': 2, 'DD': 4, 'DQ': 8, 'DT': 10}.get(directiva, 0)
        
        # Verificar DUP
        dup_match = re.match(r'^(\d+)\s+DUP\s*\([^)]+\)$', valor_str, re.IGNORECASE)
        if dup_match:
            return tam_base * int(dup_match.group(1))
        
        if 'DUP' in valor_str.upper():
            return 0
        
        string_match = re.search(r'["\']([^"\']*)["\']', valor_str)
        if string_match:
            return len(string_match.group(1))
        
        if ',' in valor_str:
            return tam_base * len(valor_str.split(','))
        
        return tam_base

    def calcular_tamano_instruccion(self, tokens: List[Token]) -> int:
        if not tokens:
            return 0
        
        idx = 0
        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            idx = 1
        if idx >= len(tokens):
            return 0
        
        instr = tokens[idx].valor.upper()
        operandos = tokens[idx + 1:] if idx + 1 < len(tokens) else []
        
        # Instrucciones de 1 byte
        if instr in self.instrucciones_sin_operandos:
            if instr in {'AAD', 'AAM'}:
                return 2
            return 1
        
        if instr == 'INT':
            return 2
        
        # Saltos condicionales
        saltos_cortos = {'JA', 'JAE', 'JB', 'JBE', 'JC', 'JE', 'JG', 'JGE', 'JL', 'JLE',
                        'JNA', 'JNAE', 'JNB', 'JNBE', 'JNC', 'JNE', 'JNG', 'JNGE',
                        'JNL', 'JNLE', 'JNO', 'JNP', 'JNS', 'JNZ', 'JO', 'JP', 'JS', 'JZ',
                        'LOOP', 'LOOPE', 'LOOPZ', 'LOOPNE', 'LOOPNZ'}
        if instr in saltos_cortos:
            return 2
        
        if instr in {'JMP', 'CALL'}:
            return 3
        
        if instr in {'INC', 'DEC'} and operandos:
            op = operandos[0].valor.upper()
            if op in self.registros_16bit:
                return 1
            return 2
        
        if instr in {'MUL', 'IMUL', 'DIV', 'IDIV'}:
            return 2
        
        if instr in {'AND', 'OR', 'XOR'}:
            tiene_mem = any('[' in t.valor for t in operandos)
            return 4 if tiene_mem else 2
        
        if instr == 'LEA':
            return 4
        
        if instr in {'PUSH', 'POP'} and operandos:
            op = operandos[0].valor.upper()
            if op in self.registros_16bit or op in self.registros_segmento:
                return 1
            return 2
        
        if instr == 'MOV':
            return 3  # Promedio
        
        return 2

    def codificar_instruccion(self, tokens: List[Token], direccion_actual: int = 0) -> str:
        """
        Codifica instrucciones según las tablas del 8086.
        SOLO codifica las instrucciones permitidas:
        Sin operandos: CMC, CMPSB, NOP, POPA, AAD, AAM
        Con 1 operando: MUL, INC, IDIV, INT
        Con 2 operandos: AND, LEA, OR, XOR
        Saltos: JNAE, JNE, JNLE, LOOPE, JA, JC
        """
        if not tokens:
            return ""
        
        idx = 0
        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            idx = 1
        if idx >= len(tokens):
            return ""
        
        instr = tokens[idx].valor.upper()
        operandos = [t for t in tokens[idx + 1:] if t.valor != ',']
        
        # Verificar que la instrucción esté en la lista de permitidas
        if instr not in self.instrucciones:
            return ""  # No codificar instrucciones no permitidas
        
        # =====================================================================
        # INSTRUCCIONES SIN OPERANDOS PERMITIDAS
        # CMC, CMPSB, NOP, POPA, AAD, AAM
        # =====================================================================
        codigos_sin_op = {
            'CMC': 'F5',      # 11110101
            'CMPSB': 'A6',    # 10100110
            'NOP': '90',      # 10010000
            'POPA': '61',     # 01100001
            'AAD': 'D5 0A',   # 11010101 00001010
            'AAM': 'D4 0A',   # 11010100 00001010
        }
        if instr in codigos_sin_op:
            return codigos_sin_op[instr]
        
        # =====================================================================
        # INT Inm.byte - Codificación: 11001101 + byte inmediato
        # =====================================================================
        if instr == 'INT' and operandos:
            val = self.obtener_valor_numerico(operandos[0].valor)
            return f'CD {val:02X}'
        
        # =====================================================================
        # SALTOS PERMITIDOS: JNAE, JNE, JNLE, LOOPE, JA, JC
        # Con cálculo de desplazamiento
        # =====================================================================
        
        # LOOPE tiene código E1
        if instr == 'LOOPE':
            if operandos:
                etiqueta = operandos[0].valor
                if etiqueta in self.tabla_simbolos:
                    dir_etiqueta = self.tabla_simbolos[etiqueta].direccion
                    if dir_etiqueta:
                        dir_etiq_int = int(dir_etiqueta, 16)
                        dir_siguiente = direccion_actual + 2
                        desplazamiento = dir_etiq_int - dir_siguiente
                        if desplazamiento < 0:
                            desplazamiento = desplazamiento & 0xFF
                        return f'E1 {desplazamiento:02X}'
            return 'E1 00'
        
        # Otros saltos permitidos
        saltos_permitidos = {
            'JNAE': '72',  # 01110010
            'JC': '72',    # 01110010 (alias de JNAE)
            'JNE': '75',   # 01110101
            'JNLE': '7F',  # 01111111
            'JA': '77',    # 01110111
        }
        
        if instr in saltos_permitidos:
            opcode = saltos_permitidos[instr]
            if operandos:
                etiqueta = operandos[0].valor
                if etiqueta in self.tabla_simbolos:
                    dir_etiqueta = self.tabla_simbolos[etiqueta].direccion
                    if dir_etiqueta:
                        dir_etiq_int = int(dir_etiqueta, 16)
                        dir_siguiente = direccion_actual + 2
                        desplazamiento = dir_etiq_int - dir_siguiente
                        if desplazamiento < 0:
                            desplazamiento = desplazamiento & 0xFF
                        return f'{opcode} {desplazamiento:02X}'
            return f'{opcode} 00'
        
        # =====================================================================
        # INC Reg - 01000reg (16 bits) o FE /0 (8 bits)
        # =====================================================================
        if instr == 'INC' and operandos:
            op = operandos[0].valor.upper()
            if op in self.registros_16bit:
                codigo = 0x40 + int(self.reg_codigo[op], 2)
                return f'{codigo:02X}'
            if op in self.registros_8bit:
                mod_rm = 0xC0 | int(self.reg_codigo[op], 2)
                return f'FE {mod_rm:02X}'
        
        # =====================================================================
        # MUL Reg/Mem - 1111011w mod 100 r/m
        # =====================================================================
        if instr == 'MUL' and operandos:
            op = operandos[0].valor.upper()
            if op in self.reg_codigo:
                w = 1 if op in self.registros_16bit else 0
                opcode = 0xF7 if w else 0xF6
                mod_rm = 0xC0 | (0x04 << 3) | int(self.reg_codigo[op], 2)
                return f'{opcode:02X} {mod_rm:02X}'
        
        # =====================================================================
        # IDIV Reg/Mem - 1111011w mod 111 r/m
        # =====================================================================
        if instr == 'IDIV' and operandos:
            op = operandos[0].valor.upper()
            if op in self.reg_codigo:
                w = 1 if op in self.registros_16bit else 0
                opcode = 0xF7 if w else 0xF6
                mod_rm = 0xC0 | (0x07 << 3) | int(self.reg_codigo[op], 2)
                return f'{opcode:02X} {mod_rm:02X}'
        
        # =====================================================================
        # AND Reg, Reg - 001000dw mod reg r/m
        # =====================================================================
        if instr == 'AND' and len(operandos) >= 2:
            op1, op2 = operandos[0].valor.upper(), operandos[1].valor.upper()
            if op1 in self.reg_codigo and op2 in self.reg_codigo:
                w = 1 if op1 in self.registros_16bit else 0
                opcode = 0x23 if w else 0x22  # d=1
                mod_rm = 0xC0 | (int(self.reg_codigo[op1], 2) << 3) | int(self.reg_codigo[op2], 2)
                return f'{opcode:02X} {mod_rm:02X}'
        
        # =====================================================================
        # OR Reg, Reg - 000010dw mod reg r/m
        # =====================================================================
        if instr == 'OR' and len(operandos) >= 2:
            op1, op2 = operandos[0].valor.upper(), operandos[1].valor.upper()
            if op1 in self.reg_codigo and op2 in self.reg_codigo:
                w = 1 if op1 in self.registros_16bit else 0
                opcode = 0x0B if w else 0x0A  # d=1
                mod_rm = 0xC0 | (int(self.reg_codigo[op1], 2) << 3) | int(self.reg_codigo[op2], 2)
                return f'{opcode:02X} {mod_rm:02X}'
        
        # =====================================================================
        # XOR Reg, Reg - 001100dw mod reg r/m
        # =====================================================================
        if instr == 'XOR' and len(operandos) >= 2:
            op1, op2 = operandos[0].valor.upper(), operandos[1].valor.upper()
            if op1 in self.reg_codigo and op2 in self.reg_codigo:
                w = 1 if op1 in self.registros_16bit else 0
                opcode = 0x33 if w else 0x32  # d=1
                mod_rm = 0xC0 | (int(self.reg_codigo[op1], 2) << 3) | int(self.reg_codigo[op2], 2)
                return f'{opcode:02X} {mod_rm:02X}'
        
        # =====================================================================
        # LEA Reg, Mem - 10001101 mod reg r/m
        # =====================================================================
        if instr == 'LEA' and len(operandos) >= 2:
            op1 = operandos[0].valor.upper()
            if op1 in self.registros_16bit:
                mod_rm = (int(self.reg_codigo[op1], 2) << 3) | 0x06  # Dirección directa
                return f'8D {mod_rm:02X} 00 00'
        
        return ""
        
    def obtener_valor_numerico(self, valor_str: str) -> int:
        valor = valor_str.strip().upper()
        # Quitar sufijo D de decimal
        if valor.endswith('D'):
            valor = valor[:-1]
        if valor.endswith('H'):
            return int(valor[:-1], 16)
        if valor.endswith('B'):
            return int(valor[:-1], 2)
        try:
            return int(valor)
        except:
            return 0

    def generar_bytes_dato(self, tokens: List[Token]) -> str:
        if len(tokens) < 3:
            return ''
        
        directiva = tokens[1].valor.upper()
        valor_str = ' '.join([t.valor for t in tokens[2:]])
        
        string_match = re.search(r'["\']([^"\']*)["\']', valor_str)
        if string_match:
            return ' '.join([f'{ord(c):02X}' for c in string_match.group(1)])
        
        dup_match = re.match(r'^(\d+)\s+DUP\s*\(([^)]+)\)$', valor_str, re.IGNORECASE)
        if dup_match:
            cant = int(dup_match.group(1))
            val = dup_match.group(2).strip()
            byte_val = '00' if val == '?' else f'{self.obtener_valor_numerico(val):02X}'
            return ' '.join([byte_val] * min(cant, 8)) + (' ...' if cant > 8 else '')
        
        if 'DUP' in valor_str.upper():
            return ''
        
        if directiva == 'DB':
            if valor_str.strip() == '?':
                return '00'
            return f'{self.obtener_valor_numerico(valor_str) & 0xFF:02X}'
        
        if directiva == 'DW':
            if valor_str.strip() == '?':
                return '00 00'
            num = self.obtener_valor_numerico(valor_str)
            return f'{num & 0xFF:02X} {(num >> 8) & 0xFF:02X}'
        
        return ''

    def generar_codificacion(self):
        """
        Genera la codificación usando los resultados del análisis sintáctico.
        La columna de estado debe coincidir con el análisis sintáctico.
        NO incluye líneas de comentarios.
        Las instrucciones incorrectas solo muestran "Incorrecta" sin código máquina.
        
        Para los saltos JNAE, JNE, JNLE, LOOPE, JA, JC calcula el desplazamiento real.
        """
        self.lineas_codificadas = []
        segmento = None
        contadores = {'STACK': 0x0250, 'DATA': 0x0250, 'CODE': 0x0250}
        contador = 0x0250
        
        # Crear un diccionario para buscar resultados del análisis por número de línea
        resultados_analisis = {}
        for analisis in self.lineas_analizadas:
            resultados_analisis[analisis['numero']] = analisis

        # =====================================================================
        # PRIMERA PASADA: Asignar direcciones a todas las etiquetas
        # =====================================================================
        segmento_tmp = None
        contador_tmp = 0x0250
        contadores_tmp = {'STACK': 0x0250, 'DATA': 0x0250, 'CODE': 0x0250}
        
        for i, linea_raw in enumerate(self.lineas_codigo):
            num_linea = i + 1
            linea = linea_raw.strip()
            linea_limpia = self.limpiar_comentarios(linea).strip()
            
            if not linea_limpia or linea.startswith(';'):
                continue
            
            tokens_linea = self.tokenizar_linea(linea_limpia, num_linea)
            linea_upper = linea_limpia.upper()
            
            # Detectar segmentos
            if re.match(r'^\.STACK\s+SEGMENT$', linea_upper):
                segmento_tmp = 'STACK'
                contador_tmp = contadores_tmp['STACK']
                continue
            if re.match(r'^\.DATA\s+SEGMENT$', linea_upper):
                segmento_tmp = 'DATA'
                contador_tmp = contadores_tmp['DATA']
                continue
            if re.match(r'^\.CODE\s+SEGMENT$', linea_upper):
                segmento_tmp = 'CODE'
                contador_tmp = contadores_tmp['CODE']
                continue
            
            if tokens_linea and tokens_linea[0].valor.upper() == 'ENDS':
                segmento_tmp = None
                continue
            if tokens_linea and tokens_linea[0].valor.upper() == 'END':
                continue
            
            # Asignar dirección a etiquetas en CODE
            if segmento_tmp == 'CODE':
                if tokens_linea and tokens_linea[0].tipo == TipoToken.SIMBOLO and tokens_linea[0].valor.endswith(':'):
                    nombre = tokens_linea[0].valor.replace(':', '')
                    if nombre in self.tabla_simbolos:
                        self.tabla_simbolos[nombre].direccion = f'{contador_tmp:04X}'
                
                # Calcular tamaño para avanzar contador
                analisis = resultados_analisis.get(num_linea, None)
                es_correcta = analisis['resultado'] == 'Correcta' if analisis else False
                if es_correcta:
                    tamano = self.calcular_tamano_instruccion(tokens_linea)
                    contador_tmp += tamano
                    contadores_tmp['CODE'] = contador_tmp
            
            elif segmento_tmp == 'DATA':
                analisis = resultados_analisis.get(num_linea, None)
                es_correcta = analisis['resultado'] == 'Correcta' if analisis else False
                if es_correcta and len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
                    nombre = tokens_linea[0].valor.rstrip(':')
                    if nombre in self.tabla_simbolos:
                        self.tabla_simbolos[nombre].direccion = f'{contador_tmp:04X}'
                    tamano = self.calcular_tamano_dato(tokens_linea)
                    contador_tmp += tamano
                    contadores_tmp['DATA'] = contador_tmp
            
            elif segmento_tmp == 'STACK':
                analisis = resultados_analisis.get(num_linea, None)
                es_correcta = analisis['resultado'] == 'Correcta' if analisis else False
                if es_correcta and tokens_linea and tokens_linea[0].valor.upper() == 'DW':
                    tokens_tmp = [Token('STACK', TipoToken.SIMBOLO, i, 0)] + tokens_linea
                    tamano = self.calcular_tamano_dato(tokens_tmp)
                    contador_tmp += tamano
                    contadores_tmp['STACK'] = contador_tmp

        # =====================================================================
        # SEGUNDA PASADA: Generar código máquina con desplazamientos calculados
        # La dirección se renueva a 0250 en la primera instrucción DESPUÉS del inicio de segmento
        # =====================================================================
        segmento = None
        contador = 0x0250
        contadores = {'STACK': 0x0250, 'DATA': 0x0250, 'CODE': 0x0250}
        # Flag para saber si es la primera línea después del inicio de segmento
        es_primera_linea_segmento = False
        direccion_anterior_ends = 0x0250

        for i, linea_raw in enumerate(self.lineas_codigo):
            num_linea = i + 1
            linea = linea_raw.strip()
            linea_limpia = self.limpiar_comentarios(linea).strip()

            # OMITIR líneas vacías y comentarios
            if not linea_limpia or linea.startswith(';'):
                continue

            tokens_linea = self.tokenizar_linea(linea_limpia, num_linea)
            
            # Obtener resultado del análisis sintáctico
            analisis = resultados_analisis.get(num_linea, None)
            es_correcta = analisis['resultado'] == 'Correcta' if analisis else False

            linea_upper = linea_limpia.upper()
            
            # Detectar inicio de segmentos - mostrar dirección actual (donde terminó el anterior)
            if re.match(r'^\.STACK\s+SEGMENT$', linea_upper):
                segmento = 'STACK'
                es_primera_linea_segmento = True
                self.lineas_codificadas.append({
                    'numero': num_linea, 'direccion': f'{contador:04X}',
                    'linea': linea_limpia, 'codigo_maquina': 'Correcta' if es_correcta else 'Incorrecta',
                    'tamano': 0, 'segmento': segmento
                })
                continue
            
            if re.match(r'^\.DATA\s+SEGMENT$', linea_upper):
                segmento = 'DATA'
                es_primera_linea_segmento = True
                self.lineas_codificadas.append({
                    'numero': num_linea, 'direccion': f'{contador:04X}',
                    'linea': linea_limpia, 'codigo_maquina': 'Correcta' if es_correcta else 'Incorrecta',
                    'tamano': 0, 'segmento': segmento
                })
                continue
            
            if re.match(r'^\.CODE\s+SEGMENT$', linea_upper):
                segmento = 'CODE'
                es_primera_linea_segmento = True
                self.lineas_codificadas.append({
                    'numero': num_linea, 'direccion': f'{contador:04X}',
                    'linea': linea_limpia, 'codigo_maquina': 'Correcta' if es_correcta else 'Incorrecta',
                    'tamano': 0, 'segmento': segmento
                })
                continue
            
            # Detectar declaraciones de segmento INCORRECTAS
            if re.match(r'^\.\w+\s+SEGMENT$', linea_upper) and not re.match(r'^\.(?:STACK|DATA|CODE)\s+SEGMENT$', linea_upper):
                self.lineas_codificadas.append({
                    'numero': num_linea, 'direccion': f'{contador:04X}',
                    'linea': linea_limpia, 'codigo_maquina': 'Incorrecta',
                    'tamano': 0, 'segmento': segmento
                })
                continue

            # ENDS y END
            if tokens_linea and tokens_linea[0].valor.upper() == 'ENDS':
                self.lineas_codificadas.append({
                    'numero': num_linea, 'direccion': f'{contador:04X}',
                    'linea': linea_limpia, 'codigo_maquina': 'Correcta' if es_correcta else 'Incorrecta',
                    'tamano': 0, 'segmento': segmento
                })
                segmento = None
                continue

            if tokens_linea and tokens_linea[0].valor.upper() == 'END':
                self.lineas_codificadas.append({
                    'numero': num_linea, 'direccion': f'{contador:04X}',
                    'linea': linea_limpia, 'codigo_maquina': 'Correcta' if es_correcta else 'Incorrecta',
                    'tamano': 0, 'segmento': segmento
                })
                continue

            # Si es la primera línea después del inicio de segmento, renovar a 0250
            if es_primera_linea_segmento:
                contador = 0x0250
                es_primera_linea_segmento = False

            tamano = 0
            codigo = ''
            direccion = f'{contador:04X}'

            if segmento == 'STACK':
                if es_correcta:
                    codigo = 'Correcta'
                    if tokens_linea and tokens_linea[0].valor.upper() == 'DW':
                        tokens_tmp = [Token('STACK', TipoToken.SIMBOLO, i, 0)] + tokens_linea
                        tamano = self.calcular_tamano_dato(tokens_tmp)
                else:
                    codigo = 'Incorrecta'
                    tamano = 0

            elif segmento == 'DATA':
                if es_correcta:
                    codigo = 'Correcta'
                    if len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
                        tamano = self.calcular_tamano_dato(tokens_linea)
                else:
                    codigo = 'Incorrecta'
                    tamano = 0

            elif segmento == 'CODE':
                if es_correcta:
                    # Codificar instrucciones pasando la dirección actual
                    codigo_maq = self.codificar_instruccion(tokens_linea, contador)
                    if codigo_maq:
                        codigo = f'Correcta | {codigo_maq}'
                    else:
                        codigo = 'Correcta'
                    tamano = self.calcular_tamano_instruccion(tokens_linea)
                else:
                    codigo = 'Incorrecta'
                    tamano = 0
            
            else:
                codigo = 'Incorrecta' if not es_correcta else 'Correcta'

            self.lineas_codificadas.append({
                'numero': num_linea, 'direccion': direccion, 'linea': linea_limpia,
                'codigo_maquina': codigo, 'tamano': tamano, 'segmento': segmento
            })

            contador += tamano
            if segmento:
                contadores[segmento] = contador


# =========================================================================
# INTERFAZ GRÁFICA
# =========================================================================

class VentanaPrincipal:
    def __init__(self, root, ensamblador):
        self.root = root
        self.root.title("Ensamblador 8086 - Análisis Sintáctico Mejorado")
        self.root.geometry("1000x700+100+100")
        self.root.minsize(800, 600)

        self.ensamblador = ensamblador
        self.ventana_analisis = None
        self.ventana_codificacion = None
        self.pagina_actual = 0
        self.elementos_por_pagina = 25

        self.crear_interfaz()

    def crear_interfaz(self):
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Botones
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(btn_frame, text="Cargar Archivo", command=self.cargar_archivo).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Analizar", command=self.analizar).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Ventana Análisis", command=self.mostrar_analisis).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Ventana Codificación", command=self.mostrar_codificacion).pack(side=tk.LEFT, padx=4)

        self.label_archivo = ttk.Label(frame, text="Ningún archivo cargado")
        self.label_archivo.pack(anchor=tk.W)

        # Paneles
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=6)

        # Código fuente
        frame_codigo = ttk.LabelFrame(paned, text="Código Fuente", padding=5)
        paned.add(frame_codigo, weight=1)
        self.texto_codigo = tk.Text(frame_codigo, wrap=tk.NONE, font=('Courier', 10))
        self.texto_codigo.pack(fill=tk.BOTH, expand=True)

        # Tokens
        frame_tokens = ttk.LabelFrame(paned, text="Tokens", padding=5)
        paned.add(frame_tokens, weight=1)
        self.texto_tokens = tk.Text(frame_tokens, wrap=tk.NONE, font=('Courier', 10))
        self.texto_tokens.pack(fill=tk.BOTH, expand=True)

        # Paginación
        pag_frame = ttk.Frame(frame)
        pag_frame.pack(fill=tk.X, pady=4)
        ttk.Button(pag_frame, text="← Anterior", command=self.pag_anterior).pack(side=tk.LEFT, padx=2)
        self.label_pag = ttk.Label(pag_frame, text="Página 1")
        self.label_pag.pack(side=tk.LEFT, padx=6)
        ttk.Button(pag_frame, text="Siguiente →", command=self.pag_siguiente).pack(side=tk.LEFT, padx=2)

    def cargar_archivo(self):
        ruta = filedialog.askopenfilename(filetypes=[("ASM", "*.asm"), ("Todos", "*.*")])
        if not ruta:
            return
        if self.ensamblador.cargar_archivo(ruta):
            self.label_archivo.config(text=f"Archivo: {Path(ruta).name}")
            self.mostrar_codigo()
            self.mostrar_tokens()
            messagebox.showinfo("Listo", "Archivo cargado")
        else:
            messagebox.showerror("Error", "No se pudo cargar")

    def mostrar_codigo(self):
        self.texto_codigo.delete(1.0, tk.END)
        for i, ln in enumerate(self.ensamblador.lineas_codigo, 1):
            self.texto_codigo.insert(tk.END, f"{i:04d} | {ln}\n")

    def mostrar_tokens(self):
        self.pagina_actual = 0
        self.actualizar_tokens()

    def actualizar_tokens(self):
        self.texto_tokens.delete(1.0, tk.END)
        inicio = self.pagina_actual * self.elementos_por_pagina
        fin = min(inicio + self.elementos_por_pagina, len(self.ensamblador.tokens))

        self.texto_tokens.insert(tk.END, f"{'#':<5} {'Token':<30} {'Tipo':<30}\n")
        self.texto_tokens.insert(tk.END, "=" * 70 + "\n")
        for i in range(inicio, fin):
            t = self.ensamblador.tokens[i]
            self.texto_tokens.insert(tk.END, f"{i+1:<5} {t.valor:<30} {t.tipo.value:<30}\n")

        total = max(1, (len(self.ensamblador.tokens) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        self.label_pag.config(text=f"Página {self.pagina_actual + 1} de {total}")

    def pag_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar_tokens()

    def pag_siguiente(self):
        total = max(1, (len(self.ensamblador.tokens) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        if self.pagina_actual < total - 1:
            self.pagina_actual += 1
            self.actualizar_tokens()

    def analizar(self):
        if not self.ensamblador.lineas_codigo:
            messagebox.showwarning("Advertencia", "Primero cargue un archivo")
            return
        self.ensamblador.analizar_sintaxis()
        self.ensamblador.generar_codificacion()
        messagebox.showinfo("Listo", "Análisis completado")

    def mostrar_analisis(self):
        if not self.ventana_analisis or not self.ventana_analisis.winfo_exists():
            self.ventana_analisis = VentanaAnalisis(self.ensamblador)
        else:
            self.ventana_analisis.actualizar()
            self.ventana_analisis.lift()

    def mostrar_codificacion(self):
        if not self.ventana_codificacion or not self.ventana_codificacion.winfo_exists():
            self.ventana_codificacion = VentanaCodificacion(self.ensamblador)
        else:
            self.ventana_codificacion.actualizar()
            self.ventana_codificacion.lift()

    def exportar(self):
        if not self.ensamblador.tokens:
            messagebox.showwarning("Advertencia", "No hay datos")
            return
        
        ruta = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("TXT", "*.txt")])
        if not ruta:
            return
        
        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("ENSAMBLADOR 8086 - RESULTADOS\n")
                f.write("=" * 100 + "\n\n")

                f.write("TOKENS\n" + "-" * 80 + "\n")
                for i, t in enumerate(self.ensamblador.tokens, 1):
                    f.write(f"{i:4}. {t.valor:<25} -> {t.tipo.value}\n")

                if self.ensamblador.lineas_analizadas:
                    f.write("\n" + "=" * 80 + "\nANÁLISIS SINTÁCTICO\n" + "-" * 80 + "\n")
                    for a in self.ensamblador.lineas_analizadas:
                        f.write(f"Línea {a['numero']}: {a['resultado']}\n  {a['linea']}\n  -> {a['mensaje']}\n\n")

                if self.ensamblador.tabla_simbolos:
                    f.write("\n" + "=" * 80 + "\nTABLA DE SÍMBOLOS\n" + "-" * 80 + "\n")
                    f.write(f"{'Símbolo':<20} {'Tipo':<12} {'Valor':<20} {'Tam':<8} {'Dir':<10}\n")
                    for s in self.ensamblador.tabla_simbolos.values():
                        dir_str = s.direccion if s.direccion else '----'
                        f.write(f"{s.nombre:<20} {s.tipo:<12} {s.valor:<20} {s.tamanio:<8} {dir_str:<10}\n")

                if self.ensamblador.lineas_codificadas:
                    f.write("\n" + "=" * 80 + "\nCÓDIGO CON DIRECCIONES\n" + "-" * 80 + "\n")
                    f.write(f"{'Dir':<8} {'Código Fuente':<50} {'Estado/Código':<25}\n")
                    for lc in self.ensamblador.lineas_codificadas:
                        f.write(f"{lc['direccion']:<8} {lc['linea']:<50} {lc['codigo_maquina']:<25}\n")

            messagebox.showinfo("Listo", "Exportado correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")


class VentanaAnalisis(tk.Toplevel):
    def __init__(self, ensamblador):
        super().__init__()
        self.ensamblador = ensamblador
        self.title("Análisis Sintáctico y Símbolos")
        self.geometry("1000x700+150+150")
        self.minsize(900, 600)
        
        # Variables de paginación para análisis
        self.pagina_actual = 0
        self.elementos_por_pagina = 25

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab Análisis Sintáctico con paginación
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Análisis Sintáctico")
        
        frame_texto1 = ttk.Frame(tab1)
        frame_texto1.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.texto_analisis = tk.Text(frame_texto1, wrap=tk.NONE, font=('Courier New', 10))
        scroll_x1 = ttk.Scrollbar(frame_texto1, orient=tk.HORIZONTAL, command=self.texto_analisis.xview)
        scroll_y1 = ttk.Scrollbar(frame_texto1, orient=tk.VERTICAL, command=self.texto_analisis.yview)
        self.texto_analisis.configure(xscrollcommand=scroll_x1.set, yscrollcommand=scroll_y1.set)
        
        scroll_y1.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x1.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto_analisis.pack(fill=tk.BOTH, expand=True)
        
        # Frame de paginación para análisis
        frame_pag1 = ttk.Frame(tab1)
        frame_pag1.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(frame_pag1, text="← Anterior", command=self.pagina_anterior).pack(side=tk.LEFT, padx=2)
        self.label_pagina = ttk.Label(frame_pag1, text="Página 1")
        self.label_pagina.pack(side=tk.LEFT, padx=20)
        ttk.Button(frame_pag1, text="Siguiente →", command=self.pagina_siguiente).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame_pag1, text="Líneas/pág:").pack(side=tk.LEFT, padx=(30, 5))
        self.combo_elementos = ttk.Combobox(frame_pag1, values=[15, 20, 25, 30, 40, 50], width=5, state="readonly")
        self.combo_elementos.set(self.elementos_por_pagina)
        self.combo_elementos.pack(side=tk.LEFT)
        self.combo_elementos.bind("<<ComboboxSelected>>", lambda e: self.cambiar_elementos())

        # Tab Símbolos
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Tabla de Símbolos")
        
        frame_texto2 = ttk.Frame(tab2)
        frame_texto2.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.texto_simbolos = tk.Text(frame_texto2, wrap=tk.NONE, font=('Courier New', 10))
        scroll_x2 = ttk.Scrollbar(frame_texto2, orient=tk.HORIZONTAL, command=self.texto_simbolos.xview)
        scroll_y2 = ttk.Scrollbar(frame_texto2, orient=tk.VERTICAL, command=self.texto_simbolos.yview)
        self.texto_simbolos.configure(xscrollcommand=scroll_x2.set, yscrollcommand=scroll_y2.set)
        
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x2.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto_simbolos.pack(fill=tk.BOTH, expand=True)

        self.actualizar()
    
    def pagina_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar_analisis()
    
    def pagina_siguiente(self):
        if not self.ensamblador.lineas_analizadas:
            return
        total_paginas = max(1, (len(self.ensamblador.lineas_analizadas) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        if self.pagina_actual < total_paginas - 1:
            self.pagina_actual += 1
            self.actualizar_analisis()
    
    def cambiar_elementos(self):
        try:
            self.elementos_por_pagina = int(self.combo_elementos.get())
            self.pagina_actual = 0
            self.actualizar_analisis()
        except:
            pass

    def actualizar(self):
        self.actualizar_analisis()
        self.actualizar_simbolos()
    
    def actualizar_analisis(self):
        self.texto_analisis.delete(1.0, tk.END)
        if self.ensamblador.lineas_analizadas:
            self.texto_analisis.insert(tk.END, f"{'Código Fuente':<50} {'Resultado':<12} {'Descripción':<55}\n")
            self.texto_analisis.insert(tk.END, "=" * 120 + "\n")
            
            inicio = self.pagina_actual * self.elementos_por_pagina
            fin = min(inicio + self.elementos_por_pagina, len(self.ensamblador.lineas_analizadas))
            
            for i in range(inicio, fin):
                a = self.ensamblador.lineas_analizadas[i]
                linea_codigo = a['linea'][:47] + '...' if len(a['linea']) > 50 else a['linea']
                # Solo mostrar descripción si es incorrecta
                if a['resultado'] == 'Incorrecta':
                    mensaje = a['mensaje'][:52] + '...' if len(a['mensaje']) > 55 else a['mensaje']
                else:
                    mensaje = ''
                self.texto_analisis.insert(tk.END, f"{linea_codigo:<50} {a['resultado']:<12} {mensaje:<55}\n")
            
            total_paginas = max(1, (len(self.ensamblador.lineas_analizadas) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
            self.label_pagina.config(text=f"Página {self.pagina_actual + 1} de {total_paginas}")
        else:
            self.texto_analisis.insert(tk.END, "Realice el análisis primero.\n")
            self.label_pagina.config(text="Página 1 de 1")
    
    def actualizar_simbolos(self):
        self.texto_simbolos.delete(1.0, tk.END)
        if self.ensamblador.tabla_simbolos:
            self.texto_simbolos.insert(tk.END, f"{'Símbolo':<20} {'Tipo':<15} {'Valor':<25} {'Tamaño':<10} {'Dirección':<10}\n")
            self.texto_simbolos.insert(tk.END, "=" * 90 + "\n")
            for s in self.ensamblador.tabla_simbolos.values():
                dir_str = s.direccion if s.direccion else '----'
                valor_str = s.valor[:22] + '...' if len(s.valor) > 25 else s.valor
                self.texto_simbolos.insert(tk.END, f"{s.nombre:<20} {s.tipo:<15} {valor_str:<25} {s.tamanio:<10} {dir_str:<10}\n")
        else:
            self.texto_simbolos.insert(tk.END, "Realice el análisis primero.\n")


class VentanaCodificacion(tk.Toplevel):
    def __init__(self, ensamblador):
        super().__init__()
        self.ensamblador = ensamblador
        self.title("Codificación de Instrucciones y Direcciones")
        self.geometry("1100x700+200+50")
        self.minsize(900, 600)
        
        self.pagina_actual = 0
        self.elementos_por_pagina = 25

        info = ttk.Label(self, text="Dirección inicial de cada segmento: 0250h", font=('Helvetica', 11, 'bold'))
        info.pack(pady=10)

        # Notebook con pestañas
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tab Codificación
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Codificación")
        
        frame_codigo = ttk.Frame(tab1)
        frame_codigo.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.texto_codigo = tk.Text(frame_codigo, wrap=tk.NONE, font=('Courier New', 10))
        scroll_x = ttk.Scrollbar(frame_codigo, orient=tk.HORIZONTAL, command=self.texto_codigo.xview)
        scroll_y = ttk.Scrollbar(frame_codigo, orient=tk.VERTICAL, command=self.texto_codigo.yview)
        self.texto_codigo.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto_codigo.pack(fill=tk.BOTH, expand=True)
        
        # Frame de paginación
        frame_paginacion = ttk.Frame(tab1)
        frame_paginacion.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(frame_paginacion, text="← Anterior", command=self.pagina_anterior).pack(side=tk.LEFT, padx=2)
        self.label_pagina = ttk.Label(frame_paginacion, text="Página 1")
        self.label_pagina.pack(side=tk.LEFT, padx=20)
        ttk.Button(frame_paginacion, text="Siguiente →", command=self.pagina_siguiente).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame_paginacion, text="Líneas/pág:").pack(side=tk.LEFT, padx=(30, 5))
        self.combo_elementos = ttk.Combobox(frame_paginacion, values=[15, 20, 25, 30, 40, 50], width=5, state="readonly")
        self.combo_elementos.set(self.elementos_por_pagina)
        self.combo_elementos.pack(side=tk.LEFT)
        self.combo_elementos.bind("<<ComboboxSelected>>", lambda e: self.cambiar_elementos())
        
        # Tab Tabla de Símbolos
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Tabla de Símbolos")
        
        frame_simbolos = ttk.Frame(tab2)
        frame_simbolos.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.texto_simbolos = tk.Text(frame_simbolos, wrap=tk.NONE, font=('Courier New', 10))
        scroll_x2 = ttk.Scrollbar(frame_simbolos, orient=tk.HORIZONTAL, command=self.texto_simbolos.xview)
        scroll_y2 = ttk.Scrollbar(frame_simbolos, orient=tk.VERTICAL, command=self.texto_simbolos.yview)
        self.texto_simbolos.configure(xscrollcommand=scroll_x2.set, yscrollcommand=scroll_y2.set)
        
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x2.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto_simbolos.pack(fill=tk.BOTH, expand=True)

        self.actualizar()
    
    def pagina_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar_codificacion()
    
    def pagina_siguiente(self):
        if not self.ensamblador.lineas_codificadas:
            return
        total_paginas = max(1, (len(self.ensamblador.lineas_codificadas) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        if self.pagina_actual < total_paginas - 1:
            self.pagina_actual += 1
            self.actualizar_codificacion()
    
    def cambiar_elementos(self):
        try:
            self.elementos_por_pagina = int(self.combo_elementos.get())
            self.pagina_actual = 0
            self.actualizar_codificacion()
        except:
            pass

    def actualizar(self):
        self.actualizar_codificacion()
        self.actualizar_simbolos()
    
    def actualizar_codificacion(self):
        self.texto_codigo.delete(1.0, tk.END)
        if self.ensamblador.lineas_codificadas:
            self.texto_codigo.insert(tk.END, f"{'Dir.':<8} {'Código Fuente':<55} {'Codificación Instrucciones':<30}\n")
            self.texto_codigo.insert(tk.END, "=" * 100 + "\n")
            
            inicio = self.pagina_actual * self.elementos_por_pagina
            fin = min(inicio + self.elementos_por_pagina, len(self.ensamblador.lineas_codificadas))
            
            for i in range(inicio, fin):
                lc = self.ensamblador.lineas_codificadas[i]
                dir_str = lc['direccion'] if lc['direccion'] else '    '
                linea = lc['linea'][:52] + '...' if len(lc['linea']) > 55 else lc['linea']
                self.texto_codigo.insert(tk.END, f"{dir_str:<8} {linea:<55} {lc['codigo_maquina']:<30}\n")
            
            total_paginas = max(1, (len(self.ensamblador.lineas_codificadas) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
            self.label_pagina.config(text=f"Página {self.pagina_actual + 1} de {total_paginas}")
        else:
            self.texto_codigo.insert(tk.END, "Realice el análisis primero.\n")
            self.label_pagina.config(text="Página 1 de 1")
    
    def actualizar_simbolos(self):
        self.texto_simbolos.delete(1.0, tk.END)
        if self.ensamblador.tabla_simbolos:
            self.texto_simbolos.insert(tk.END, f"{'Símbolo':<20} {'Tipo':<15} {'Valor':<25} {'Tamaño':<10} {'Dirección':<10}\n")
            self.texto_simbolos.insert(tk.END, "=" * 90 + "\n")
            for s in self.ensamblador.tabla_simbolos.values():
                dir_str = s.direccion if s.direccion else '----'
                valor_str = s.valor[:22] + '...' if len(s.valor) > 25 else s.valor
                self.texto_simbolos.insert(tk.END, f"{s.nombre:<20} {s.tipo:<15} {valor_str:<25} {s.tamanio:<10} {dir_str:<10}\n")
        else:
            self.texto_simbolos.insert(tk.END, "Realice el análisis primero.\n")


if __name__ == "__main__":
    root = tk.Tk()
    ensamblador = Ensamblador8086()
    app = VentanaPrincipal(root, ensamblador)
    root.mainloop()