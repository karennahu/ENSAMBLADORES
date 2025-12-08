#EQUIPO2 - Ensamblador 8086 con Codificación de Instrucciones

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
    ELEMENTO_COMPUESTO = "Elemento Compuesto"
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
        self.instrucciones = {
            'CMC', 'CMPSB', 'NOP', 'POPA', 'AAD', 'AAM', 'MUL',
            'INC', 'IDIV', 'INT', 'AND', 'LEA', 'OR', 'XOR',
            'JNAE', 'JNE', 'JNLE', 'LOOPE', 'JA', 'JC'
        }

        self.pseudoinstrucciones = {
            'SEGMENT', 'ENDS', 'END', 'DB', 'DW', 'DD', 'DQ', 'DT',
            'EQU', 'PROC', 'ENDP', 'ASSUME', 'ORG'
        }

        self.registros = {
            'AX', 'BX', 'CX', 'DX', 'AH', 'AL', 'BH', 'BL', 'CH', 'CL', 'DH', 'DL',
            'SI', 'DI', 'BP', 'SP', 'CS', 'DS', 'ES', 'SS', 'IP', 'FLAGS'
        }

        # Codificación de registros según el PDF
        self.reg_codigo = {
            'AL': '000', 'CL': '001', 'DL': '010', 'BL': '011',
            'AH': '100', 'CH': '101', 'DH': '110', 'BH': '111',
            'AX': '000', 'CX': '001', 'DX': '010', 'BX': '011',
            'SP': '100', 'BP': '101', 'SI': '110', 'DI': '111'
        }
        
        self.regs2_codigo = {'ES': '00', 'CS': '01', 'SS': '10', 'DS': '11'}

        self.tokens: List[Token] = []
        self.tabla_simbolos = {}
        self.lineas_codigo: List[str] = []
        self.lineas_analizadas: List[dict] = []
        self.lineas_codificadas: List[dict] = []

    def limpiar_comentarios(self, linea: str) -> str:
        pos = linea.find(';')
        return linea[:pos] if pos != -1 else linea

    def extraer_elementos_compuestos(self, texto: str) -> Tuple[str, List[Tuple[str, str]]]:
        elementos = []
        texto_mod = texto
        patrones = [
            (r'\.code\s+segment', 'COMP_CODE_SEG'),
            (r'\.data\s+segment', 'COMP_DATA_SEG'),
            (r'\.stack\s+segment', 'COMP_STACK_SEG'),
            (r'byte\s+ptr', 'COMP_BYTE_PTR'),
            (r'word\s+ptr', 'COMP_WORD_PTR'),
            (r'dup\s*\([^)]+\)', 'COMP_DUP'),
            (r'\[[^\]]+\]', 'COMP_BRACKET'),
            (r'"[^"]*"', 'COMP_STRING'),
            (r"'[^']*'", 'COMP_CHAR'),
        ]
        contador = 0
        for patron, prefijo in patrones:
            for match in list(re.finditer(patron, texto_mod, re.IGNORECASE))[::-1]:
                elem = match.group(0)
                marcador = f'{prefijo}_{contador}'
                elementos.append((marcador, elem))
                texto_mod = texto_mod[:match.start()] + marcador + texto_mod[match.end():]
                contador += 1
        return texto_mod, elementos

    def restaurar_elementos_compuestos(self, tokens: List[str], elementos: List[Tuple[str, str]]) -> List[str]:
        restaurados = []
        for token in tokens:
            rest = False
            for marcador, original in elementos:
                if marcador in token:
                    restaurados.append(token.replace(marcador, original))
                    rest = True
                    break
            if not rest:
                restaurados.append(token)
        return restaurados

    def sanitizar_tokens(self, tokens: List[str]) -> List[str]:
        saneados = []
        for t in tokens:
            if t is None:
                continue
            s = str(t).strip()
            s = re.sub(r'[\x00-\x1f\x7f]+', '', s)
            if s:
                saneados.append(s)
        return saneados

    def tiene_string_invalido(self, linea: str) -> bool:
        if len([c for c in linea if c == '"']) % 2 != 0:
            return True
        if len([c for c in linea if c == "'"]) % 2 != 0:
            return True
        if linea.count('[') != linea.count(']'):
            return True
        if linea.count('(') != linea.count(')'):
            return True
        return False

    def tokenizar_linea(self, linea: str, num_linea: int) -> List[Token]:
        linea_sin_com = self.limpiar_comentarios(linea).strip()
        if not linea_sin_com:
            return []

        if self.tiene_string_invalido(linea_sin_com):
            return [Token(linea_sin_com, TipoToken.NO_IDENTIFICADO, num_linea, 0)]

        texto_mod, elementos = self.extraer_elementos_compuestos(linea_sin_com)

        etiquetas = []
        patron_etiq = r'(?:^|(?<=\s))([A-Za-z_][A-Za-z0-9_]*:)(?=\s|$)'
        for match in re.finditer(patron_etiq, texto_mod):
            marcador = f'ETIQ_{len(etiquetas)}'
            etiquetas.append((marcador, match.group(1)))
            texto_mod = texto_mod[:match.start()] + ' ' + marcador + ' ' + texto_mod[match.end():]

        token_pattern = re.compile(
            r'(ETIQ_[0-9]+|COMP_[A-Z_]+_[0-9]+|\"[^\"]*\"|\'[^\']*\'|\[[^\]]+\]|'
            r'[A-Za-z_][A-Za-z0-9_]*:|[A-Za-z_][A-Za-z0-9_]*|0[0-9A-F]+H|[01]+B|\d+|[,:\[\]\(\)\+\-\*/%])',
            re.IGNORECASE
        )

        tokens_brutos = [t for t in token_pattern.findall(texto_mod) if t]
        tokens_rest = self.restaurar_elementos_compuestos(tokens_brutos, elementos)

        for marcador, etiq_orig in etiquetas:
            tokens_rest = [etiq_orig if t == marcador else t for t in tokens_rest]

        tokens_limpios = self.sanitizar_tokens(tokens_rest)

        tokens = []
        for pos, token_str in enumerate(tokens_limpios):
            tipo = self.identificar_tipo_token(token_str)
            tokens.append(Token(token_str, tipo, num_linea, pos))
        return tokens

    def identificar_tipo_token(self, token: str) -> TipoToken:
        t = token.strip()
        tu = t.upper()

        if (t.startswith('"') and not t.endswith('"')) or (t.startswith("'") and not t.endswith("'")):
            return TipoToken.NO_IDENTIFICADO
        if (t.startswith('[') and not t.endswith(']')) or (not t.startswith('[') and t.endswith(']')):
            return TipoToken.NO_IDENTIFICADO
        if t.count('(') != t.count(')'):
            return TipoToken.NO_IDENTIFICADO

        if re.match(r'^\.(?:CODE|DATA|STACK)\s+SEGMENT$', t, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^(?:BYTE|WORD)\s+PTR$', t, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^DUP\s*\([^)]+\)$', t, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^\[[^\]]+\]$', t):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^"[^"]*"$', t) or re.match(r"^'[^']*'$", t):
            return TipoToken.CONSTANTE_CARACTER

        if tu in self.instrucciones:
            return TipoToken.INSTRUCCION
        if tu in self.pseudoinstrucciones:
            return TipoToken.PSEUDOINSTRUCCION
        if tu in self.registros:
            return TipoToken.REGISTRO

        if re.match(r'^0[0-9A-F]+H$', tu):
            return TipoToken.CONSTANTE_HEXADECIMAL
        if re.match(r'^[01]+[Bb]$', t):
            return TipoToken.CONSTANTE_BINARIA
        if re.match(r'^\d+$', t):
            return TipoToken.CONSTANTE_DECIMAL
        if re.match(r'^\d+[A-Z]+$', tu) and not re.match(r'^[0-9A-F]+H$', tu):
            return TipoToken.NO_IDENTIFICADO

        if re.match(r'^\.[A-Za-z_]+$', tu) or re.match(r'^[A-Za-z_][A-Za-z0-9_]*:$', t) or \
           re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t):
            return TipoToken.SIMBOLO

        if re.search(r'[@#%&!~`]', t):
            return TipoToken.NO_IDENTIFICADO

        return TipoToken.NO_IDENTIFICADO

    def validar_instruccion(self, instr_texto: str) -> Tuple[bool, str]:
        instr = instr_texto.strip().upper()
        if not instr:
            return False, "Instrucción vacía"
        if instr not in self.instrucciones:
            return False, f"Instrucción no permitida: {instr}"
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

            if tokens_linea[0].tipo == TipoToken.SIMBOLO and tokens_linea[0].valor.endswith(':'):
                nombre = tokens_linea[0].valor.replace(':', '')
                self.tabla_simbolos[nombre] = Simbolo(nombre, 'Etiqueta', '', '')

            resultado, mensaje = self.validar_linea(tokens_linea, segmento)

            if segmento == 'DATA' and len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
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

        if '.stack segment' in linea_texto.lower():
            return "Correcta", "Inicio de segmento de pila"
        if '.data segment' in linea_texto.lower():
            return "Correcta", "Inicio de segmento de datos"
        if '.code segment' in linea_texto.lower():
            return "Correcta", "Inicio de segmento de código"
        if tokens[0].valor.upper() == 'ENDS':
            return "Correcta", "Fin de segmento"
        if tokens[0].valor.upper() == 'END':
            return "Correcta", "Fin de programa"

        if segmento == 'STACK':
            return self.validar_segmento_pila(tokens)
        elif segmento == 'DATA':
            return self.validar_segmento_datos(tokens)
        elif segmento == 'CODE':
            return self.validar_segmento_codigo(tokens)

        return "Incorrecta", "Línea No Válida"

    def validar_segmento_pila(self, tokens: List[Token]) -> Tuple[str, str]:
        if len(tokens) < 2:
            return "Incorrecta", "Definición de pila incompleta"
        if tokens[0].valor.upper() == 'DW':
            return "Correcta", "Definición de pila válida"
        return "Correcta", "Elemento de pila"

    def validar_segmento_datos(self, tokens: List[Token]) -> Tuple[str, str]:
        if len(tokens) < 3:
            return "Incorrecta", "Definición de datos incompleta"
        if tokens[0].tipo != TipoToken.SIMBOLO:
            return "Incorrecta", "Debe iniciar con un símbolo válido"
        directiva = tokens[1].valor.upper()
        if directiva not in ['DB', 'DW', 'DD', 'DQ', 'DT', 'EQU']:
            return "Incorrecta", f"Directiva inválida: {directiva}"
        
        # Validar el valor/expresión
        valor_str = ' '.join([t.valor for t in tokens[2:]])
        
        # Verificar sintaxis de DUP correcta
        if 'DUP' in valor_str.upper():
            # Formato correcto: número DUP(valor) - ejemplo: 128 DUP(0) o 10 DUP(?)
            if not re.match(r'^\d+\s+DUP\s*\([^)]+\)$', valor_str, re.IGNORECASE):
                # Detectar errores comunes
                if re.search(r'DUP[A-Z]', valor_str, re.IGNORECASE):
                    return "Incorrecta", "Error de sintaxis: 'DUP' mal escrito (¿quiso decir 'DUP(...)'?)"
                if not re.search(r'\d+\s+DUP', valor_str, re.IGNORECASE):
                    return "Incorrecta", "DUP requiere un número antes: cantidad DUP(valor)"
                if '(' not in valor_str or ')' not in valor_str:
                    return "Incorrecta", "DUP requiere paréntesis: cantidad DUP(valor)"
                return "Incorrecta", f"Sintaxis DUP inválida: {valor_str}"
        
        # Verificar strings cerrados
        if (valor_str.count('"') % 2 != 0) or (valor_str.count("'") % 2 != 0):
            return "Incorrecta", "Cadena de texto sin cerrar"
        
        return "Correcta", "Definición de dato válida"

    def validar_segmento_codigo(self, tokens: List[Token]) -> Tuple[str, str]:
        if not tokens:
            return "Correcta", "Línea vacía"

        tokens_val = tokens
        msg_etiq = ""

        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            msg_etiq = "Etiqueta definida"
            if len(tokens) == 1:
                return "Correcta", msg_etiq
            tokens_val = tokens[1:]

        if not tokens_val:
            return "Correcta", msg_etiq if msg_etiq else "Línea vacía"

        primer_texto = tokens_val[0].valor.strip()
        primer = primer_texto.upper()

        if primer not in self.instrucciones and tokens_val[0].tipo == TipoToken.INSTRUCCION:
            return "Incorrecta", f"Instrucción no permitida: {primer}"

        if tokens_val[0].tipo == TipoToken.PSEUDOINSTRUCCION:
            if primer in ['ASSUME', 'PROC', 'ENDP', 'ORG']:
                msg = f"Pseudoinstrucción {primer} válida"
                return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg
            return "Incorrecta", f"Pseudoinstrucción {primer} no permitida en código"

        if tokens_val[0].tipo == TipoToken.INSTRUCCION:
            valida, msg_val = self.validar_instruccion(primer_texto)
            if not valida:
                return "Incorrecta", msg_val
            sin_op = {'NOP', 'CMC', 'POPA', 'AAD', 'AAM', 'CMPSB'}
            if len(tokens_val) < 2 and primer not in sin_op:
                return "Incorrecta", f"Instrucción {primer} requiere operandos"
            msg = f"Instrucción {primer} válida"
            return "Correcta", f"{msg_etiq} + {msg}" if msg_etiq else msg

        if tokens_val[0].tipo == TipoToken.SIMBOLO:
            if primer in self.instrucciones:
                sin_op = {'NOP', 'CMC', 'POPA', 'AAD', 'AAM', 'CMPSB'}
                if len(tokens_val) < 2 and primer not in sin_op:
                    return "Incorrecta", f"Instrucción {primer} requiere operandos"
                return "Correcta", f"Instrucción {primer} válida"
            return "Incorrecta", f"'{tokens_val[0].valor}' no es instrucción reconocida"

        if tokens_val[0].tipo == TipoToken.NO_IDENTIFICADO:
            return "Incorrecta", f"Elemento '{tokens_val[0].valor}' no identificado"

        return "Incorrecta", "Sintaxis inválida"

    def agregar_simbolo(self, tokens_linea: List[Token]):
        nombre = tokens_linea[0].valor.rstrip(":")

        if tokens_linea[0].valor.endswith(":"):
            tipo = "Etiqueta"
            tamanio = ""
            valor = ""
        else:
            directiva = tokens_linea[1].valor.upper()
            tipo = "Constante" if directiva == "EQU" else "Variable"
            tamanio = directiva if directiva in ("DB", "DW") else ""
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
        
        # Verificar DUP con sintaxis correcta
        dup_match = re.match(r'^(\d+)\s+DUP\s*\([^)]+\)$', valor_str, re.IGNORECASE)
        if dup_match:
            return tam_base * int(dup_match.group(1))
        
        # Si contiene DUP pero no coincide con el patrón correcto, es error
        if 'DUP' in valor_str.upper():
            return 0  # Error de sintaxis, no incrementar dirección
        
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
        instr_1b = {'NOP', 'CMC', 'POPA', 'CMPSB', 'CLC', 'CLD', 'CLI', 'STC', 'STD', 'STI',
                   'PUSHF', 'POPF', 'LAHF', 'SAHF', 'AAA', 'AAS', 'DAA', 'DAS', 'CBW', 'CWD',
                   'MOVSB', 'MOVSW', 'LODSB', 'LODSW', 'STOSB', 'STOSW', 'RET', 'IRET'}
        if instr in instr_1b:
            return 1
        
        if instr in {'AAD', 'AAM', 'INT'}:
            return 2
        
        saltos = {'JA', 'JAE', 'JB', 'JBE', 'JC', 'JE', 'JG', 'JGE', 'JL', 'JLE', 'JNA',
                 'JNAE', 'JNB', 'JNBE', 'JNC', 'JNE', 'JNG', 'JNGE', 'JNL', 'JNLE', 'JNO',
                 'JNP', 'JNS', 'JNZ', 'JO', 'JP', 'JS', 'JZ', 'LOOP', 'LOOPE', 'LOOPNE'}
        if instr in saltos:
            return 2
        
        if instr in {'JMP', 'CALL'}:
            return 3
        
        if instr in {'INC', 'DEC'} and operandos:
            op = operandos[0].valor.upper()
            if op in {'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI'}:
                return 1
            return 2
        
        if instr in {'MUL', 'IDIV', 'DIV', 'IMUL'}:
            return 2
        
        if instr in {'AND', 'OR', 'XOR'}:
            tiene_mem = any('[' in t.valor for t in operandos)
            return 4 if tiene_mem else 2
        
        if instr == 'LEA':
            return 4
        
        if instr in {'PUSH', 'POP'} and operandos:
            op = operandos[0].valor.upper()
            if op in {'AX', 'BX', 'CX', 'DX', 'SP', 'BP', 'SI', 'DI', 'CS', 'DS', 'ES', 'SS'}:
                return 1
            return 2
        
        return 2

    def codificar_instruccion(self, tokens: List[Token]) -> str:
        if not tokens:
            return ""
        
        idx = 0
        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            idx = 1
        if idx >= len(tokens):
            return ""
        
        instr = tokens[idx].valor.upper()
        operandos = [t for t in tokens[idx + 1:] if t.valor != ',']
        
        # Instrucciones sin operandos
        codigos_sin_op = {
            'NOP': '90', 'CMC': 'F5', 'POPA': '61', 'CMPSB': 'A6',
            'AAD': 'D5 0A', 'AAM': 'D4 0A', 'AAA': '37', 'AAS': '3F',
            'CBW': '98', 'CWD': '99', 'DAA': '27', 'DAS': '2F',
            'LAHF': '9F', 'SAHF': '9E', 'PUSHF': '9C', 'POPF': '9D',
            'MOVSB': 'A4', 'MOVSW': 'A5', 'LODSB': 'AC', 'LODSW': 'AD',
            'STOSB': 'AA', 'STOSW': 'AB', 'RET': 'C3', 'IRET': 'CF',
            'CLC': 'F8', 'CLD': 'FC', 'CLI': 'FA', 'STC': 'F9', 'STD': 'FD', 'STI': 'FB'
        }
        if instr in codigos_sin_op:
            return codigos_sin_op[instr]
        
        # INT
        if instr == 'INT' and operandos:
            val = self.obtener_valor_numerico(operandos[0].valor)
            return f'CD {val:02X}'
        
        # Saltos condicionales
        codigos_saltos = {
            'JO': '70', 'JNO': '71', 'JB': '72', 'JNAE': '72', 'JC': '72',
            'JNB': '73', 'JAE': '73', 'JE': '74', 'JZ': '74', 'JNE': '75', 'JNZ': '75',
            'JBE': '76', 'JA': '77', 'JS': '78', 'JNS': '79', 'JP': '7A', 'JNP': '7B',
            'JL': '7C', 'JNGE': '7C', 'JNL': '7D', 'JGE': '7D', 'JLE': '7E', 'JNG': '7E',
            'JG': '7F', 'JNLE': '7F'
        }
        if instr in codigos_saltos:
            return f'{codigos_saltos[instr]} 00'
        
        codigos_loop = {'LOOP': 'E2', 'LOOPE': 'E1', 'LOOPZ': 'E1', 'LOOPNE': 'E0', 'LOOPNZ': 'E0'}
        if instr in codigos_loop:
            return f'{codigos_loop[instr]} 00'
        
        if instr == 'JMP':
            return 'E9 00 00'
        if instr == 'CALL':
            return 'E8 00 00'
        
        # INC registro
        if instr == 'INC' and operandos:
            op = operandos[0].valor.upper()
            if op in self.reg_codigo and op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'}:
                return f'{0x40 + int(self.reg_codigo[op], 2):02X}'
            elif op in self.reg_codigo:
                w = 1 if op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'} else 0
                mod_rm = 0xC0 | int(self.reg_codigo[op], 2)
                return f'{"FF" if w else "FE"} {mod_rm:02X}'
        
        # MUL
        if instr == 'MUL' and operandos:
            op = operandos[0].valor.upper()
            if op in self.reg_codigo:
                w = 1 if op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'} else 0
                mod_rm = 0xC0 | (0x04 << 3) | int(self.reg_codigo[op], 2)
                return f'{"F7" if w else "F6"} {mod_rm:02X}'
        
        # IDIV
        if instr == 'IDIV' and operandos:
            op = operandos[0].valor.upper()
            if op in self.reg_codigo:
                w = 1 if op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'} else 0
                mod_rm = 0xC0 | (0x07 << 3) | int(self.reg_codigo[op], 2)
                return f'{"F7" if w else "F6"} {mod_rm:02X}'
        
        # AND, OR, XOR
        ops_logicas = {'AND': ('21', '20'), 'OR': ('09', '08'), 'XOR': ('31', '30')}
        if instr in ops_logicas and len(operandos) >= 2:
            op1, op2 = operandos[0].valor.upper(), operandos[1].valor.upper()
            if op1 in self.reg_codigo and op2 in self.reg_codigo:
                w = 1 if op1 in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'} else 0
                mod_rm = 0xC0 | (int(self.reg_codigo[op1], 2) << 3) | int(self.reg_codigo[op2], 2)
                cod = ops_logicas[instr][0] if w else ops_logicas[instr][1]
                return f'{cod} {mod_rm:02X}'
        
        # LEA
        if instr == 'LEA' and len(operandos) >= 2:
            op1 = operandos[0].valor.upper()
            if op1 in self.reg_codigo:
                mod_rm = (int(self.reg_codigo[op1], 2) << 3) | 0x07
                return f'8D {mod_rm:02X}'
        
        # PUSH/POP
        if instr == 'PUSH' and operandos:
            op = operandos[0].valor.upper()
            if op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'}:
                return f'{0x50 + int(self.reg_codigo[op], 2):02X}'
            elif op in self.regs2_codigo:
                return f'{(int(self.regs2_codigo[op], 2) << 3) | 0x06:02X}'
        
        if instr == 'POP' and operandos:
            op = operandos[0].valor.upper()
            if op in {'AX', 'CX', 'DX', 'BX', 'SP', 'BP', 'SI', 'DI'}:
                return f'{0x58 + int(self.reg_codigo[op], 2):02X}'
            elif op in self.regs2_codigo:
                return f'{(int(self.regs2_codigo[op], 2) << 3) | 0x07:02X}'
        
        return "??"

    def obtener_valor_numerico(self, valor_str: str) -> int:
        valor = valor_str.strip().upper()
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
        
        # Verificar DUP con sintaxis correcta
        dup_match = re.match(r'^(\d+)\s+DUP\s*\(([^)]+)\)$', valor_str, re.IGNORECASE)
        if dup_match:
            cant = int(dup_match.group(1))
            val = dup_match.group(2).strip()
            byte_val = '00' if val == '?' else f'{self.obtener_valor_numerico(val):02X}'
            return ' '.join([byte_val] * min(cant, 8)) + (' ...' if cant > 8 else '')
        
        # Si contiene DUP pero no coincide con el patrón, es error
        if 'DUP' in valor_str.upper():
            return ''  # Error de sintaxis
        
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
        self.lineas_codificadas = []
        segmento = None
        contadores = {'STACK': 0x0250, 'DATA': 0x0250, 'CODE': 0x0250}
        contador = 0x0250

        for i, linea_raw in enumerate(self.lineas_codigo):
            linea = linea_raw.strip()
            linea_limpia = self.limpiar_comentarios(linea).strip()

            if not linea_limpia:
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': '', 'linea': linea_raw,
                    'codigo_maquina': '', 'tamano': 0, 'segmento': segmento
                })
                continue

            if linea.startswith(';'):
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': '', 'linea': linea_raw,
                    'codigo_maquina': '; Comentario', 'tamano': 0, 'segmento': segmento
                })
                continue

            tokens_linea = self.tokenizar_linea(linea_limpia, i + 1)

            # Detectar segmentos
            if '.STACK SEGMENT' in linea_limpia.upper():
                segmento = 'STACK'
                contador = contadores['STACK']
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': f'{contador:04X}',
                    'linea': linea_raw, 'codigo_maquina': '; Inicio STACK',
                    'tamano': 0, 'segmento': segmento
                })
                continue

            if '.DATA SEGMENT' in linea_limpia.upper():
                segmento = 'DATA'
                contador = contadores['DATA']
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': f'{contador:04X}',
                    'linea': linea_raw, 'codigo_maquina': '; Inicio DATA',
                    'tamano': 0, 'segmento': segmento
                })
                continue

            if '.CODE SEGMENT' in linea_limpia.upper():
                segmento = 'CODE'
                contador = contadores['CODE']
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': f'{contador:04X}',
                    'linea': linea_raw, 'codigo_maquina': '; Inicio CODE',
                    'tamano': 0, 'segmento': segmento
                })
                continue

            if tokens_linea and tokens_linea[0].valor.upper() == 'ENDS':
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': f'{contador:04X}',
                    'linea': linea_raw, 'codigo_maquina': '; Fin segmento',
                    'tamano': 0, 'segmento': segmento
                })
                segmento = None
                continue

            if tokens_linea and tokens_linea[0].valor.upper() == 'END':
                self.lineas_codificadas.append({
                    'numero': i + 1, 'direccion': f'{contador:04X}',
                    'linea': linea_raw, 'codigo_maquina': '; Fin programa',
                    'tamano': 0, 'segmento': segmento
                })
                continue

            tamano = 0
            codigo = ''
            direccion = f'{contador:04X}'

            if segmento == 'DATA':
                if len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
                    # Primero validar la sintaxis
                    res, msg = self.validar_linea(tokens_linea, 'DATA')
                    if res == 'Incorrecta':
                        codigo = f'ERROR: {msg}'
                        tamano = 0  # No incrementar dirección si hay error
                    else:
                        tamano = self.calcular_tamano_dato(tokens_linea)
                        nombre = tokens_linea[0].valor.rstrip(':')
                        if nombre in self.tabla_simbolos:
                            self.tabla_simbolos[nombre].direccion = direccion
                        codigo = self.generar_bytes_dato(tokens_linea)
                        if not codigo and tamano == 0:
                            codigo = 'ERROR: No se pudo generar código'

            elif segmento == 'CODE':
                if tokens_linea and tokens_linea[0].tipo == TipoToken.SIMBOLO and tokens_linea[0].valor.endswith(':'):
                    nombre = tokens_linea[0].valor.replace(':', '')
                    if nombre in self.tabla_simbolos:
                        self.tabla_simbolos[nombre].direccion = direccion

                # Primero validar
                if tokens_linea:
                    res, msg = self.validar_linea(tokens_linea, 'CODE')
                    if res == 'Incorrecta':
                        codigo = f'ERROR: {msg}'
                        tamano = 0  # No incrementar dirección si hay error
                    else:
                        tamano = self.calcular_tamano_instruccion(tokens_linea)
                        codigo = self.codificar_instruccion(tokens_linea)

            elif segmento == 'STACK':
                if tokens_linea and tokens_linea[0].valor.upper() == 'DW':
                    tokens_tmp = [Token('STACK', TipoToken.SIMBOLO, i, 0)] + tokens_linea
                    tamano = self.calcular_tamano_dato(tokens_tmp)
                    codigo = self.generar_bytes_dato(tokens_tmp)

            self.lineas_codificadas.append({
                'numero': i + 1, 'direccion': direccion, 'linea': linea_raw,
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
        self.root.title("Ensamblador 8086 - Código y Tokens")
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
        ttk.Button(btn_frame, text="Exportar", command=self.exportar).pack(side=tk.LEFT, padx=4)
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
                    f.write(f"{'Dir':<8} {'Código Fuente':<50} {'Código Máquina':<25}\n")
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
        self.geometry("900x600+150+150")

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab Análisis
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Análisis Sintáctico")
        self.texto_analisis = tk.Text(tab1, wrap=tk.WORD, font=('Courier', 10))
        self.texto_analisis.pack(fill=tk.BOTH, expand=True)

        # Tab Símbolos
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Tabla de Símbolos")
        self.texto_simbolos = tk.Text(tab2, wrap=tk.WORD, font=('Courier', 10))
        self.texto_simbolos.pack(fill=tk.BOTH, expand=True)

        self.actualizar()

    def actualizar(self):
        self.texto_analisis.delete(1.0, tk.END)
        if self.ensamblador.lineas_analizadas:
            self.texto_analisis.insert(tk.END, f"{'Resultado':<12} {'Descripción':<60}\n{'=' * 80}\n")
            for a in self.ensamblador.lineas_analizadas:
                self.texto_analisis.insert(tk.END, f"{a['resultado']:<12} {a['mensaje']:<60}\n")
        else:
            self.texto_analisis.insert(tk.END, "Realice el análisis primero.\n")

        self.texto_simbolos.delete(1.0, tk.END)
        if self.ensamblador.tabla_simbolos:
            self.texto_simbolos.insert(tk.END, f"{'Símbolo':<20} {'Tipo':<12} {'Valor':<20} {'Tam':<8} {'Dir':<10}\n{'=' * 80}\n")
            for s in self.ensamblador.tabla_simbolos.values():
                dir_str = s.direccion if s.direccion else '----'
                self.texto_simbolos.insert(tk.END, f"{s.nombre:<20} {s.tipo:<12} {s.valor:<20} {s.tamanio:<8} {dir_str:<10}\n")
        else:
            self.texto_simbolos.insert(tk.END, "Realice el análisis primero.\n")


class VentanaCodificacion(tk.Toplevel):
    def __init__(self, ensamblador):
        super().__init__()
        self.ensamblador = ensamblador
        self.title("Codificación de Instrucciones y Direcciones")
        self.geometry("1100x700+200+50")
        self.minsize(900, 600)
        
        # Paginación
        self.pagina_actual = 0
        self.elementos_por_pagina = 25

        # Info
        info = ttk.Label(self, text="Dirección inicial de cada segmento: 0250h", font=('Helvetica', 11, 'bold'))
        info.pack(pady=10)

        # Frame principal para el código
        frame_principal = ttk.Frame(self)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.texto_codigo = tk.Text(frame_principal, wrap=tk.NONE, font=('Courier New', 10))
        scroll_x = ttk.Scrollbar(frame_principal, orient=tk.HORIZONTAL, command=self.texto_codigo.xview)
        scroll_y = ttk.Scrollbar(frame_principal, orient=tk.VERTICAL, command=self.texto_codigo.yview)
        self.texto_codigo.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.texto_codigo.pack(fill=tk.BOTH, expand=True)
        
        # Frame de paginación
        frame_paginacion = ttk.Frame(self)
        frame_paginacion.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(frame_paginacion, text="← Anterior", command=self.pagina_anterior).pack(side=tk.LEFT, padx=2)
        self.label_pagina = ttk.Label(frame_paginacion, text="Página 1")
        self.label_pagina.pack(side=tk.LEFT, padx=20)
        ttk.Button(frame_paginacion, text="Siguiente →", command=self.pagina_siguiente).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame_paginacion, text="Líneas/pág:").pack(side=tk.LEFT, padx=(30, 5))
        self.combo_elementos = ttk.Combobox(frame_paginacion, values=[15, 20, 25, 30, 40, 50], width=5, state="readonly")
        self.combo_elementos.set(self.elementos_por_pagina)
        self.combo_elementos.pack(side=tk.LEFT)
        self.combo_elementos.bind("<<ComboboxSelected>>", lambda e: self.cambiar_elementos())

        self.actualizar()
    
    def pagina_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar()
    
    def pagina_siguiente(self):
        if not self.ensamblador.lineas_codificadas:
            return
        total_paginas = max(1, (len(self.ensamblador.lineas_codificadas) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        if self.pagina_actual < total_paginas - 1:
            self.pagina_actual += 1
            self.actualizar()
    
    def cambiar_elementos(self):
        try:
            self.elementos_por_pagina = int(self.combo_elementos.get())
            self.pagina_actual = 0
            self.actualizar()
        except:
            pass

    def actualizar(self):
        # Código con direcciones
        self.texto_codigo.delete(1.0, tk.END)
        if self.ensamblador.lineas_codificadas:
            self.texto_codigo.insert(tk.END, f"{'Dir.':<8} {'Código Fuente':<55} {'Código Máquina / Error':<30}\n")
            self.texto_codigo.insert(tk.END, "=" * 100 + "\n")
            
            # Paginación
            inicio = self.pagina_actual * self.elementos_por_pagina
            fin = min(inicio + self.elementos_por_pagina, len(self.ensamblador.lineas_codificadas))
            
            for i in range(inicio, fin):
                lc = self.ensamblador.lineas_codificadas[i]
                dir_str = lc['direccion'] if lc['direccion'] else '    '
                linea = lc['linea'][:52] + '...' if len(lc['linea']) > 55 else lc['linea']
                self.texto_codigo.insert(tk.END, f"{dir_str:<8} {linea:<55} {lc['codigo_maquina']:<30}\n")
            
            # Actualizar etiqueta de página
            total_paginas = max(1, (len(self.ensamblador.lineas_codificadas) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
            self.label_pagina.config(text=f"Página {self.pagina_actual + 1} de {total_paginas}")
        else:
            self.texto_codigo.insert(tk.END, "Realice el análisis primero.\n")
            self.label_pagina.config(text="Página 1 de 1")


if __name__ == "__main__":
    root = tk.Tk()
    ensamblador = Ensamblador8086()
    app = VentanaPrincipal(root, ensamblador)
    root.mainloop()