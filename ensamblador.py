#EQUIPO2

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


# AQUI COLOCARE LOS : Tipos y estructuras

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
    tamanio: int

class Ensamblador8086:
    def __init__(self):
        # Lista de instrucciones permitidas (edítala aquí si quieres agregar/quitar)
        self.instrucciones = {
            'CMC', 'CMPSB', 'NOP', 'POPA', 'AAD', 'AAM', 'MUL',
            'INC', 'IDIV', 'INT', 'AND', 'LEA', 'OR', 'XOR',
            'JNAE', 'JNE', 'JNLE', 'LOOPE', 'JA', 'JC'
        }

        # Pseudoinstrucciones
        self.pseudoinstrucciones = {
            'SEGMENT', 'ENDS', 'END', 'DB', 'DW', 'DD', 'DQ', 'DT',
            'EQU', 'PROC', 'ENDP', 'ASSUME', 'ORG'
        }

        # Registros
        self.registros = {
            'AX', 'BX', 'CX', 'DX', 'AH', 'AL', 'BH', 'BL', 'CH', 'CL', 'DH', 'DL',
            'SI', 'DI', 'BP', 'SP', 'CS', 'DS', 'ES', 'SS', 'IP', 'FLAGS'
        }

        # Estructuras
        self.tokens: List[Token] = []
        self.tabla_simbolos = {}
        self.lineas_codigo: List[str] = []
        self.lineas_analizadas: List[dict] = []

        # Guardado de paginas si se necesita
        self.paginas = []

    # -------------------------
    # Utilidades
    # -------------------------
    def limpiar_comentarios(self, linea: str) -> str:
        pos_comentario = linea.find(';')
        if pos_comentario != -1:
            return linea[:pos_comentario]
        return linea

    def extraer_elementos_compuestos(self, texto: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Reemplaza por marcadores ciertas partes compuestas (strings, [..], dup(...), segment defs).
        Devuelve texto con marcadores + lista de (marcador, original).
        """
        elementos_compuestos = []
        texto_modificado = texto

        patrones_compuestos = [
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
        for patron, prefijo in patrones_compuestos:
            for match in list(re.finditer(patron, texto_modificado, re.IGNORECASE))[::-1]:
                elemento = match.group(0)
                marcador = f'{prefijo}_{contador}'
                elementos_compuestos.append((marcador, elemento))
                texto_modificado = texto_modificado[:match.start()] + marcador + texto_modificado[match.end():]
                contador += 1

        return texto_modificado, elementos_compuestos

    def restaurar_elementos_compuestos(self, tokens: List[str], elementos_compuestos: List[Tuple[str, str]]) -> List[str]:
        tokens_restaurados = []
        for token in tokens:
            restaurado = False
            for marcador, elemento_original in elementos_compuestos:
                if marcador in token:
                    tokens_restaurados.append(token.replace(marcador, elemento_original))
                    restaurado = True
                    break
            if not restaurado:
                tokens_restaurados.append(token)
        return tokens_restaurados

    # -------------------------
    # SANITIZACIÓN (quita rastros de IA u otros ruidos)
    # -------------------------
    def sanitizar_tokens(self, tokens: List[str]) -> List[str]:
        saneados = []
        for t in tokens:
            if t is None:
                continue
            s = str(t).strip()

            # Quitar rastros típicos (por si quedaron)
            s = re.sub(r"meacheaning|auto_generated|AI:|This was generated:", "", s, flags=re.IGNORECASE)

            # eliminar caracteres de control invisibles
            s = re.sub(r'[\x00-\x1f\x7f]+', '', s)

            # Si quedó vacío, saltar
            if s == "":
                continue

            saneados.append(s)
        return saneados

    # -------------------------
    # Tokenización (preserva orden)
    # -------------------------
    def tokenizar_linea(self, linea: str, num_linea: int) -> List[Token]:
        """
        Tokeniza una línea y detecta elementos inválidos como strings sin cerrar
        """
        linea_sin_com = self.limpiar_comentarios(linea).strip()
        if not linea_sin_com:
            return []

        # VALIDACIÓN PREVIA: Detectar strings mal formados ANTES de tokenizar
        if self.tiene_string_invalido(linea_sin_com):
            # Retornar toda la línea como un solo token NO_IDENTIFICADO
            return [Token(
                valor=linea_sin_com,
                tipo=TipoToken.NO_IDENTIFICADO,
                linea=num_linea,
                posicion=0
            )]

        texto_modificado, elementos_compuestos = self.extraer_elementos_compuestos(linea_sin_com)

        # Detectar etiquetas (name:) y reemplazarlas por marcador temporal
        etiquetas = []
        patron_etiqueta = r'(?:^|(?<=\s))([A-Za-z_][A-Za-z0-9_]*:)(?=\s|$)'
        for match in re.finditer(patron_etiqueta, texto_modificado):
            marcador = f'ETIQ_{len(etiquetas)}'
            etiquetas.append((marcador, match.group(1)))
            texto_modificado = texto_modificado[:match.start()] + ' ' + marcador + ' ' + texto_modificado[match.end():]

        # Tokenización robusta que respeta el orden:
        token_pattern = re.compile(
            r'(ETIQ_[0-9]+|COMP_[A-Z_]+_[0-9]+|\"[^\"]*\"|\'[^\']*\'|\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_]*:|[A-Za-z_][A-Za-z0-9_]*|0[0-9A-F]+H|[01]+B|\d+|[,:\[\]\(\)\+\-\*/%])',
            re.IGNORECASE
        )

        tokens_brutos = token_pattern.findall(texto_modificado)
        tokens_brutos = [t for t in tokens_brutos if t is not None and t != ""]

        # Restaurar elementos compuestos (los marcadores COMP_ -> su contenido)
        tokens_restaurados = self.restaurar_elementos_compuestos(tokens_brutos, elementos_compuestos)

        # Restaurar etiquetas originales (ETIQ_ -> label:)
        for marcador, etiqueta_original in etiquetas:
            tokens_restaurados = [etiqueta_original if t == marcador else t for t in tokens_restaurados]

        # Sanitizar tokens (quita ruido)
        tokens_limpios = self.sanitizar_tokens(tokens_restaurados)

        # Convertir a Token dataclass (preservando orden)
        tokens = []
        for pos, token_str in enumerate(tokens_limpios):
            tipo = self.identificar_tipo_token(token_str)
            tokens.append(Token(token_str, tipo, num_linea, pos))
        
        return tokens


    def identificar_tipo_token(self, token: str) -> TipoToken:
        """
        Identifica el tipo de token con validaciones mejoradas
        """
        t = token.strip()
        tu = t.upper()

        # VALIDACIÓN 1: Strings mal formados (comillas sin cerrar)
        if (t.startswith('"') and not t.endswith('"')) or \
        (t.startswith("'") and not t.endswith("'")):
            return TipoToken.NO_IDENTIFICADO
        
        # VALIDACIÓN 2: Corchetes sin cerrar
        if (t.startswith('[') and not t.endswith(']')) or \
        (not t.startswith('[') and t.endswith(']')):
            return TipoToken.NO_IDENTIFICADO
        
        # VALIDACIÓN 3: Paréntesis sin cerrar
        if t.count('(') != t.count(')'):
            return TipoToken.NO_IDENTIFICADO

        # Elementos compuestos válidos
        if re.match(r'^\.(?:CODE|DATA|STACK)\s+SEGMENT$', t, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^(?:BYTE|WORD)\s+PTR$', t, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^DUP\s*\([^)]+\)$', t, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        if re.match(r'^\[[^\]]+\]$', t):
            return TipoToken.ELEMENTO_COMPUESTO
        
        # Strings y caracteres válidos (con comillas cerradas correctamente)
        if (re.match(r'^"[^"]*"$', t) or re.match(r"^'[^']*'$", t)):
            return TipoToken.CONSTANTE_CARACTER

        # Instrucción / pseudoinstrucción / registro
        if tu in self.instrucciones:
            return TipoToken.INSTRUCCION
        if tu in self.pseudoinstrucciones:
            return TipoToken.PSEUDOINSTRUCCION
        if tu in self.registros:
            return TipoToken.REGISTRO

        # Constantes
        if re.match(r'^0[0-9A-F]+H$', tu):
            return TipoToken.CONSTANTE_HEXADECIMAL
        if re.match(r'^[01]+[Bb]$', t):
            return TipoToken.CONSTANTE_BINARIA
        if re.match(r'^\d+$', t):
            return TipoToken.CONSTANTE_DECIMAL

        # VALIDACIÓN 4: Números con formato inválido
        if re.match(r'^\d+[A-Z]+$', tu) and not re.match(r'^[0-9A-F]+H$', tu):
            return TipoToken.NO_IDENTIFICADO

        # Símbolos/etiquetas válidos
        if re.match(r'^\.[A-Za-z_]+$', tu) or \
        re.match(r'^[A-Za-z_][A-Za-z0-9_]*:$', t) or \
        re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t):
            return TipoToken.SIMBOLO

        # VALIDACIÓN 5: Caracteres especiales inválidos
        if re.search(r'[@#%&!~`]', t):
            return TipoToken.NO_IDENTIFICADO

        # Por defecto: no identificado
        return TipoToken.NO_IDENTIFICADO


    def tiene_string_invalido(self, linea: str) -> bool:
        """
        Detecta si una línea tiene un string mal formado
        """
        # Buscar comillas sin cerrar
        comillas_dobles = [i for i, c in enumerate(linea) if c == '"']
        comillas_simples = [i for i, c in enumerate(linea) if c == "'"]
        
        # Si hay número impar de comillas, está mal formado
        if len(comillas_dobles) % 2 != 0:
            return True
        if len(comillas_simples) % 2 != 0:
            return True
        
        # Verificar corchetes balanceados
        if linea.count('[') != linea.count(']'):
            return True
        
        # Verificar paréntesis balanceados
        if linea.count('(') != linea.count(')'):
            return True
        
        return False

    # -------------------------
    # NUEVO: Validar instrucción explícitamente
    # -------------------------
    def validar_instruccion(self, instruccion_texto: str) -> Tuple[bool, str]:
        """
        Devuelve (True, "OK") si la instrucción está permitida.
        Si no, devuelve (False, mensaje_error).
        """
        instr = instruccion_texto.strip().upper()
        if instr == "":
            return False, "Instrucción vacía"

        # Si la instrucción no está en la lista estricta, devolver error
        if instr not in self.instrucciones:
            return False, f"Instrucción no permitida: {instr}"

        return True, "OK"

    # -------------------------
    # Cargar archivo y generar tokens
    # -------------------------
    def cargar_archivo(self, ruta_archivo: str) -> bool:
        try:
            archivo_path = Path(ruta_archivo)
            if not archivo_path.exists():
                return False

            with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.lineas_codigo = [ln.rstrip('\n') for ln in f]

            self.tokens = []
            for num_linea, linea in enumerate(self.lineas_codigo, 1):
                tokens_linea = self.tokenizar_linea(linea, num_linea)
                self.tokens.extend(tokens_linea)
            return True
        except Exception as e:
            print("Error al cargar archivo:", e)
            return False

    # -------------------------
    # Análisis sintáctico (mantiene orden)
    # -------------------------

    def analizar_sintaxis(self):
            self.lineas_analizadas = []
            self.tabla_simbolos = {}
            segmento_actual = None

            for i, linea_raw in enumerate(self.lineas_codigo):
                linea = linea_raw.strip()
                
                if not linea:
                    continue
                if linea.startswith(';'):
                    continue
                
                linea_limpia = self.limpiar_comentarios(linea).strip()
                if not linea_limpia:
                    continue

                tokens_linea = self.tokenizar_linea(linea_limpia, i + 1)
                if not tokens_linea:
                    continue

                primer_token = tokens_linea[0].valor.upper()

                # Detectar segmento actual
                if '.STACK SEGMENT' in linea_limpia.upper():
                    segmento_actual = 'STACK'
                elif '.DATA SEGMENT' in linea_limpia.upper():
                    segmento_actual = 'DATA'
                elif '.CODE SEGMENT' in linea_limpia.upper():
                    segmento_actual = 'CODE'
                elif primer_token == 'ENDS':
                    segmento_actual = None

                # ✅ AGREGAR ETIQUETAS A LA TABLA DE SÍMBOLOS
                if tokens_linea[0].tipo == TipoToken.SIMBOLO and tokens_linea[0].valor.endswith(':'):
                    nombre_etiqueta = tokens_linea[0].valor.replace(':', '')
                    
                    # Crear objeto Simbolo para la etiqueta
                    self.tabla_simbolos[nombre_etiqueta] = Simbolo(
                        nombre=nombre_etiqueta,
                        tipo='Etiqueta',
                        valor='',  # Las etiquetas no tienen valor
                        tamanio=''  # Las etiquetas no tienen tamaño
                    )

                # Validar línea
                resultado, mensaje = self.validar_linea(tokens_linea, segmento_actual)

                # Agregar símbolos de DATA (variables y constantes)
                if segmento_actual == 'DATA' and len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
                    self.agregar_simbolo(tokens_linea)

                # Limpiar mensajes
                mensaje = re.sub(
                    r"meacheaning|auto_generated|AI:|This was generated:",
                    "",
                    str(mensaje),
                    flags=re.IGNORECASE
                ).strip()

                self.lineas_analizadas.append({
                    'numero': i + 1,
                    'linea': linea_limpia,
                    'resultado': resultado,
                    'mensaje': mensaje
                })

    # -------------------------
    # Validaciones por segmento
    # -------------------------
    def validar_linea(self, tokens: List[Token], segmento: Optional[str]) -> Tuple[str, str]:
        # Comportamiento simple: detecta segmentos, end, pseudoinstr e instrucciones
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

        # Si no sabemos, marcar correcta (evita mover/romper)
        return "Incorrecta", "Línea No Valida"

    def validar_segmento_pila(self, tokens: List[Token]) -> Tuple[str, str]:
        if len(tokens) < 2:
            return "Incorrecta", "Definición de pila incompleta"
        if tokens[0].valor.upper() == 'DW':
            return "Correcta", "Definición de pila válida"
        return "Correcta", "Elemento de pila"

    def validar_segmento_datos(self, tokens: List[Token]) -> Tuple[str, str]:
        """
        Valida líneas en el segmento DATA con verificaciones estrictas
        """
        # Verificar cantidad mínima de tokens
        if len(tokens) < 3:
            return "Incorrecta", "Definición de datos incompleta"
        
        # El primer token debe ser un símbolo (nombre de variable)
        if tokens[0].tipo != TipoToken.SIMBOLO:
            return "Incorrecta", "Debe iniciar con un símbolo válido"
        
        # El segundo token debe ser una directiva válida
        directiva = tokens[1].valor.upper()
        if directiva not in ['DB', 'DW','EQU']:
            return "Incorrecta", f"Directiva inválida: {directiva}"
        
        # Validar el valor (tercer token en adelante)
        valor_tokens = tokens[2:]
        
        # Reconstruir la línea original para validaciones adicionales
        linea_completa = ' '.join([t.valor for t in tokens])
        
        # VALIDACIÓN 1: Verificar comillas sin cerrar en strings
        if '"' in linea_completa:
            # Contar comillas dobles
            count_comillas = linea_completa.count('"')
            if count_comillas % 2 != 0:
                return "Incorrecta", "Cadena de texto sin cerrar (falta comilla de cierre)"
        
        # VALIDACIÓN 2: Verificar comillas simples sin cerrar
        if "'" in linea_completa:
            # Contar comillas simples
            count_comillas_simples = linea_completa.count("'")
            if count_comillas_simples % 2 != 0:
                return "Incorrecta", "Constante de caracter sin cerrar (falta comilla de cierre)"
        
        # VALIDACIÓN 3: Verificar corchetes balanceados
        if '[' in linea_completa or ']' in linea_completa:
            if linea_completa.count('[') != linea_completa.count(']'):
                return "Incorrecta", "Corchetes no balanceados"
        
        # VALIDACIÓN 4: Verificar paréntesis balanceados (para DUP)
        if '(' in linea_completa or ')' in linea_completa:
            if linea_completa.count('(') != linea_completa.count(')'):
                return "Incorrecta", "Paréntesis no balanceados"
        
        # VALIDACIÓN 5: Si usa DUP, verificar formato correcto
        if 'DUP' in linea_completa.upper():
            # Formato esperado: cantidad DUP(valor)
            if not re.search(r'\d+\s+DUP\s*\([^)]+\)', linea_completa, re.IGNORECASE):
                return "Incorrecta", "Formato de DUP incorrecto (debe ser: cantidad DUP(valor))"
        
        # VALIDACIÓN 6: Verificar que el valor no esté vacío
        if not valor_tokens or all(t.valor.strip() == '' for t in valor_tokens):
            return "Incorrecta", "Falta el valor de inicialización"
        
        # VALIDACIÓN 7: Para DB y DW, verificar tipos de datos válidos
        if directiva in ['DB', 'DW']:
            valor_str = ' '.join([t.valor for t in valor_tokens])
            
            # Si es un string, verificar que esté correctamente formateado
            if valor_str.startswith('"') or valor_str.startswith("'"):
                # Ya se validó arriba que las comillas estén cerradas
                pass
            # Si es un número, verificar formato
            elif re.match(r'^\d+$', valor_str.strip()):
                pass  # Número decimal válido
            elif re.match(r'^[0-9A-F]+H$', valor_str.strip().upper()):
                pass  # Número hexadecimal válido
            elif re.match(r'^[01]+B$', valor_str.strip().upper()):
                pass  # Número binario válido
            elif 'DUP' in valor_str.upper():
                pass  # Ya se validó arriba
            elif '?' in valor_str:
                pass  # Variable sin inicializar (válido)
            else:
                # Verificar si hay caracteres inválidos
                if re.search(r'[^\w\s,\[\]\(\)\+\-\*\$\?"\']', valor_str):
                    return "Incorrecta", "Valor contiene caracteres inválidos"
        
        # Si pasó todas las validaciones
        return "Correcta", "Definición de dato válida"

    def validar_segmento_codigo(self, tokens: List[Token]) -> Tuple[str, str]:
        if not tokens:
            return "Correcta", "Línea vacía"

        tokens_a_validar = tokens
        mensaje_etiqueta = ""

        if tokens[0].tipo == TipoToken.SIMBOLO and tokens[0].valor.endswith(':'):
            mensaje_etiqueta = "Etiqueta definida"
            if len(tokens) == 1:
                return "Correcta", mensaje_etiqueta
            tokens_a_validar = tokens[1:]

        if not tokens_a_validar:
            return "Correcta", mensaje_etiqueta if mensaje_etiqueta else "Línea vacía"

        primer_token_text = tokens_a_validar[0].valor.strip()
        primer_token = primer_token_text.upper()

        # Si la primera palabra no está en la lista de instrucciones pero fue marcada como INSTRUCCION
        # o si fue marcada como SIMBOLO pero su texto coincide con alguna instrucción, validamos estrictamente.
        # Validación estricta: la instrucción debe estar en self.instrucciones
        if primer_token not in self.instrucciones and tokens_a_validar[0].tipo == TipoToken.INSTRUCCION:
            return "Incorrecta", f"Instrucción no permitida: {primer_token}"

        # Pseudoinstrucción
        if tokens_a_validar[0].tipo == TipoToken.PSEUDOINSTRUCCION:
            if primer_token in ['ASSUME', 'PROC', 'ENDP', 'ORG']:
                resultado_msg = f"Pseudoinstrucción {primer_token} válida"
                if mensaje_etiqueta:
                    resultado_msg = f"{mensaje_etiqueta} + {resultado_msg}"
                return "Correcta", resultado_msg
            return "Incorrecta", f"Pseudoinstrucción {primer_token} no permitida en segmento de código"

        # Instrucción
        if tokens_a_validar[0].tipo == TipoToken.INSTRUCCION:
            # Validar explícitamente contra la lista permitida (refuerzo)
            valida, msg_val = self.validar_instruccion(primer_token_text)
            if not valida:
                return "Incorrecta", msg_val

            # algunas instrucciones no requieren operandos
            sin_operandos_ok = {'NOP', 'CMC', 'POPA', 'AAD', 'AAM', 'CMPSB'}
            if len(tokens_a_validar) < 2 and primer_token not in sin_operandos_ok:
                return "Incorrecta", f"Instrucción {primer_token} requiere operandos"
            resultado_msg = f"Instrucción {primer_token} válida"
            if mensaje_etiqueta:
                resultado_msg = f"{mensaje_etiqueta} + {resultado_msg}"
            return "Correcta", resultado_msg

        # Si empieza con símbolo/identificador pero no es instrucción
        if tokens_a_validar[0].tipo == TipoToken.SIMBOLO and len(tokens_a_validar) > 1:
            # Si el texto coincide con una instrucción permitida, considerarlo instrucción
            if primer_token in self.instrucciones:
                # aunque token fue marcado como SIMBOLO, su texto es instrucción permitida
                # esto maneja casos de tokenización con mayúsculas/minúsculas
                sin_operandos_ok = {'NOP', 'CMC', 'POPA', 'AAD', 'AAM', 'CMPSB'}
                if len(tokens_a_validar) < 2 and primer_token not in sin_operandos_ok:
                    return "Incorrecta", f"Instrucción {primer_token} requiere operandos"
                return "Correcta", f"Instrucción {primer_token} válida"
            return "Incorrecta", f"'{tokens_a_validar[0].valor}' no es una instrucción reconocida"

        if tokens_a_validar[0].tipo == TipoToken.SIMBOLO:
            return "Incorrecta", f"'{tokens_a_validar[0].valor}' no es una instrucción reconocida"

        if tokens_a_validar[0].tipo == TipoToken.NO_IDENTIFICADO:
            return "Incorrecta", f"Elemento '{tokens_a_validar[0].valor}' no identificado"

        return "Incorrecta", "Línea de código con sintaxis inválida"

    # -------------------------
    # Agregar símbolo simple
    # -------------------------
    def agregar_simbolo(self, tokens_linea: List[Token]):
        """
        Construye la tabla de símbolos con el formato solicitado:
        tipo: Variable | Constante | Etiqueta
        tamaño: DB | DW | ""
        valor: hexadecimales terminados en H, o el valor indicado. Las etiquetas no tienen valor.
        """

        nombre = tokens_linea[0].valor.rstrip(":")  # Quitar dos puntos si es etiqueta

        # 1) IDENTIFICAR TIPO
        if tokens_linea[0].valor.endswith(":"):
            tipo = "Etiqueta"
            tamanio = ""
            valor = ""
        else:
            directiva = tokens_linea[1].valor.upper()

            if directiva == "EQU":
                tipo = "Constante"
                tamanio = ""
            else:
                tipo = "Variable"

            # Tamaño: DB / DW si aplica
            tamanio = directiva if directiva in ("DB", "DW") else ""

            # Valor: tomar todo lo que está después
            raw_valor = " ".join(tok.valor for tok in tokens_linea[2:])

            # ✅ Detectar hexadecimal válido (DEBE empezar con 0)
            if re.match(r'^0[0-9A-F]+H$', raw_valor.upper()):
                valor = raw_valor.upper()
            # ✅ Detectar binario válido (termina en B o b)
            elif re.match(r'^[01]+[Bb]$', raw_valor):
                valor = raw_valor.upper()
            else:
                valor = raw_valor

        # Guardar en tabla de símbolos
        self.tabla_simbolos[nombre] = Simbolo(
            nombre=nombre,
            tipo=tipo,
            valor=valor,
            tamanio=tamanio
        )

    # -------------------------
    # Paginador (útil si quieres exportar o mostrar en UI por páginas)
    # -------------------------
    def paginar_salida(self, texto: str, lineas_por_pagina: int = 30) -> List[str]:
        lineas = texto.splitlines()
        paginas = []
        for i in range(0, len(lineas), lineas_por_pagina):
            paginas.append("\n".join(lineas[i:i + lineas_por_pagina]))
        return paginas

# -------------------------
# GUI (Tkinter) - simple y usable
# -------------------------
class EnsambladorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ensamblador 8086 - Limpio")
        self.root.geometry("1100x700")

        self.ensamblador = Ensamblador8086()

        # Paginación tokens
        self.pagina_actual = 0
        self.elementos_por_pagina = 25

        self.crear_interfaz()

    def crear_interfaz(self):
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Botones
        botones = ttk.Frame(frame)
        botones.pack(fill=tk.X, pady=6)
        ttk.Button(botones, text="Cargar Archivo", command=self.cargar_archivo).pack(side=tk.LEFT, padx=4)
        ttk.Button(botones, text="Analizar", command=self.analizar).pack(side=tk.LEFT, padx=4)
        ttk.Button(botones, text="Exportar Resultados", command=self.exportar_resultados).pack(side=tk.LEFT, padx=4)

        # Etiqueta archivo
        self.label_archivo = ttk.Label(frame, text="Ningún archivo cargado")
        self.label_archivo.pack(anchor=tk.W)

        # Notebook con pestañas
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=6)

        # Código
        self.tab_codigo = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_codigo, text="Código Fuente")
        self.texto_codigo = scrolledtext.ScrolledText(self.tab_codigo, wrap=tk.WORD, height=18)
        self.texto_codigo.pack(fill=tk.BOTH, expand=True)

        # Tokens (con paginación)
        self.tab_tokens = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tokens, text="Tokens Identificados")
        self.texto_tokens = scrolledtext.ScrolledText(self.tab_tokens, wrap=tk.WORD, height=16)
        self.texto_tokens.pack(fill=tk.BOTH, expand=True)

        pag_frame = ttk.Frame(self.tab_tokens)
        pag_frame.pack(fill=tk.X, pady=4)
        ttk.Button(pag_frame, text="← Anterior", command=self.pagina_anterior).pack(side=tk.LEFT, padx=2)
        self.label_pagina = ttk.Label(pag_frame, text="Página 1")
        self.label_pagina.pack(side=tk.LEFT, padx=6)
        ttk.Button(pag_frame, text="Siguiente →", command=self.pagina_siguiente).pack(side=tk.LEFT, padx=2)
        ttk.Label(pag_frame, text="Elementos/pág:").pack(side=tk.RIGHT)
        self.entry_elementos = ttk.Combobox(pag_frame, values=[10, 20, 25, 50], width=4, state="readonly")
        self.entry_elementos.set(self.elementos_por_pagina)
        self.entry_elementos.pack(side=tk.RIGHT, padx=6)
        self.entry_elementos.bind("<<ComboboxSelected>>", lambda e: self.cambiar_elementos_por_pagina())

        # Análisis sintáctico
        self.tab_analisis = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_analisis, text="Análisis Sintáctico")
        self.texto_analisis = scrolledtext.ScrolledText(self.tab_analisis, wrap=tk.WORD, height=18)
        self.texto_analisis.pack(fill=tk.BOTH, expand=True)

        # Tabla de símbolos
        self.tab_simbolos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_simbolos, text="Tabla de Símbolos")
        self.texto_simbolos = scrolledtext.ScrolledText(self.tab_simbolos, wrap=tk.WORD, height=12)
        self.texto_simbolos.pack(fill=tk.BOTH, expand=True)

    # -------------------------
    # Carga y muestra
    # -------------------------
    def cargar_archivo(self):
        ruta = filedialog.askopenfilename(title="Seleccionar archivo", filetypes=[("ASM", "*.asm"), ("Todos", "*.*")])
        if not ruta:
            return
        ok = self.ensamblador.cargar_archivo(ruta)
        if ok:
            self.label_archivo.config(text=f"Archivo: {Path(ruta).name}")
            self.mostrar_codigo()
            self.mostrar_tokens()
            messagebox.showinfo("Listo", "Archivo cargado correctamente")
        else:
            messagebox.showerror("Error", "No se pudo cargar el archivo")

    def mostrar_codigo(self):
        self.texto_codigo.delete(1.0, tk.END)
        for i, ln in enumerate(self.ensamblador.lineas_codigo, 1):
            self.texto_codigo.insert(tk.END, f"{i:04d} | {ln}\n")

    def mostrar_tokens(self):
        self.pagina_actual = 0
        self.actualizar_pagina_tokens()

    def actualizar_pagina_tokens(self):
        self.texto_tokens.delete(1.0, tk.END)
        inicio = self.pagina_actual * self.elementos_por_pagina
        fin = min(inicio + self.elementos_por_pagina, len(self.ensamblador.tokens))

        self.texto_tokens.insert(tk.END, f"{'Núm.':<6} {'Token':<30} {'Tipo':<30} {'Línea':<6}\n")
        self.texto_tokens.insert(tk.END, "=" * 100 + "\n")
        for i in range(inicio, fin):
            tkobj = self.ensamblador.tokens[i]
            self.texto_tokens.insert(tk.END, f"{i+1:<6} {tkobj.valor:<30} {tkobj.tipo.value:<30} {tkobj.linea:<6}\n")

        total_paginas = max(1, (len(self.ensamblador.tokens) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        self.label_pagina.config(text=f"Página {self.pagina_actual + 1} de {total_paginas}")

    def pagina_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar_pagina_tokens()

    def pagina_siguiente(self):
        total_paginas = max(1, (len(self.ensamblador.tokens) + self.elementos_por_pagina - 1) // self.elementos_por_pagina)
        if self.pagina_actual < total_paginas - 1:
            self.pagina_actual += 1
            self.actualizar_pagina_tokens()

    def cambiar_elementos_por_pagina(self):
        try:
            v = int(self.entry_elementos.get())
            self.elementos_por_pagina = v
            self.pagina_actual = 0
            self.actualizar_pagina_tokens()
        except Exception:
            pass

    # -------------------------
    # Análisis y salida
    # -------------------------
    def analizar(self):
        if not self.ensamblador.lineas_codigo:
            messagebox.showwarning("Advertencia", "Primero debe cargar un archivo")
            return
        self.ensamblador.analizar_sintaxis()
        self.mostrar_analisis()
        self.mostrar_tabla_simbolos()
        messagebox.showinfo("Listo", "Análisis completado")

    def mostrar_analisis(self):
        self.texto_analisis.delete(1.0, tk.END)
        self.texto_analisis.insert(tk.END, f"{'Línea':<6} {'Resultado':<12} {'Descripción':<60}\n")
        self.texto_analisis.insert(tk.END, "=" * 120 + "\n")
        # Mantenemos el orden en que se analizaron las líneas
        for analisis in self.ensamblador.lineas_analizadas:
            num = analisis['numero']
            res = analisis['resultado']
            msg = analisis['mensaje']
            
            self.texto_analisis.insert(tk.END, f"{num:<6} {res:<12} {msg:<60}\n")
            

    def mostrar_tabla_simbolos(self):
        self.texto_simbolos.delete(1.0, tk.END)
        self.texto_simbolos.insert(tk.END, f"{'Símbolo':<20} {'Tipo':<10} {'Valor':<20} {'Tamaño':<10}\n")
        self.texto_simbolos.insert(tk.END, "=" * 70 + "\n")
        for simbolo in self.ensamblador.tabla_simbolos.values():
            self.texto_simbolos.insert(tk.END, f"{simbolo.nombre:<20} {simbolo.tipo:<10} {simbolo.valor:<20} {simbolo.tamanio:<10}\n")

    # -------------------------
    # Exportar
    # -------------------------
    def exportar_resultados(self):
        if not (self.ensamblador.tokens or self.ensamblador.lineas_analizadas):
            messagebox.showwarning("Advertencia", "No hay datos para exportar")
            return

        ruta = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("TXT", "*.txt"), ("Todos", "*.*")])
        if not ruta:
            return

        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("ENSAMBLADOR 8086 - RESULTADOS DEL ANÁLISIS\n")
                f.write("=" * 80 + "\n\n")

                f.write("TOKENS IDENTIFICADOS\n")
                f.write("-" * 80 + "\n")
                for i, token in enumerate(self.ensamblador.tokens, 1):
                    f.write(f"{i:4d}. {token.valor:<25} -> {token.tipo.value}\n")

                if self.ensamblador.lineas_analizadas:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("ANÁLISIS SINTÁCTICO\n")
                    f.write("-" * 80 + "\n")
                    for analisis in self.ensamblador.lineas_analizadas:
                        f.write(f"Línea {analisis['numero']}: {analisis['resultado']}\n")
                        f.write(f"  {analisis['linea']}\n")
                        f.write(f"  -> {analisis['mensaje']}\n\n")

                if self.ensamblador.tabla_simbolos:
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("TABLA DE SÍMBOLOS\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"{'Símbolo':<20} {'Tipo':<10} {'Valor':<20} {'Tamaño':<10}\n")
                    f.write("-" * 80 + "\n")
                    for simbolo in self.ensamblador.tabla_simbolos.values():
                        f.write(f"{simbolo.nombre:<20} {simbolo.tipo:<10} {simbolo.valor:<20} {simbolo.tamanio:<10}\n")

            messagebox.showinfo("Listo", "Resultados exportados correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

# -------------------------
# main
# -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = EnsambladorGUI(root)
    root.mainloop()
