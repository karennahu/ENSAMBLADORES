import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
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
    tamanio: int

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
        
        self.tokens = []
        self.tabla_simbolos = {}
        self.lineas_codigo = []
        self.lineas_analizadas = []
        
    def limpiar_comentarios(self, linea: str) -> str:
        pos_comentario = linea.find(';')
        if pos_comentario != -1:
            return linea[:pos_comentario]
        return linea
    
    def extraer_elementos_compuestos(self, texto: str) -> Tuple[str, List[Tuple[str, str]]]:
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
            matches = list(re.finditer(patron, texto_modificado, re.IGNORECASE))
            for match in reversed(matches):
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
    
    def tokenizar_linea(self, linea: str, num_linea: int) -> List[Token]:
        linea = self.limpiar_comentarios(linea).strip()
        if not linea:
            return []
        
        texto_modificado, elementos_compuestos = self.extraer_elementos_compuestos(linea)
        
        etiquetas = []
        patron_etiqueta = r'(?:^|(?<=\s))([A-Za-z_][A-Za-z0-9_]*):(?=\s|$)'
        for match in re.finditer(patron_etiqueta, texto_modificado):
            marcador = f'ETIQ_{len(etiquetas)}'
            etiquetas.append((marcador, match.group(0).strip()))
            texto_modificado = texto_modificado[:match.start()] + ' ' + marcador + ' ' + texto_modificado[match.end():]
        
        tokens_brutos = re.split(r'[\s,:]+', texto_modificado)
        tokens_brutos = [t for t in tokens_brutos if t]
        
        tokens_restaurados = self.restaurar_elementos_compuestos(tokens_brutos, elementos_compuestos)
        
        for marcador, etiqueta_original in etiquetas:
            tokens_restaurados = [etiqueta_original if t == marcador else t for t in tokens_restaurados]
        
        tokens = []
        for pos, token_str in enumerate(tokens_restaurados):
            if token_str:
                tipo = self.identificar_tipo_token(token_str)
                tokens.append(Token(token_str, tipo, num_linea, pos))
        
        return tokens
    
    def identificar_tipo_token(self, token: str) -> TipoToken:
        token_upper = token.upper()
        
        if re.match(r'^\.(?:CODE|DATA|STACK)\s+SEGMENT$', token, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        
        if re.match(r'^(?:BYTE|WORD)\s+PTR$', token, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        
        if re.match(r'^DUP\s*\([^)]+\)$', token, re.IGNORECASE):
            return TipoToken.ELEMENTO_COMPUESTO
        
        if re.match(r'^\[[^\]]+\]$', token):
            return TipoToken.ELEMENTO_COMPUESTO
        
        if re.match(r'^"[^"]*"$', token):
            return TipoToken.CONSTANTE_CARACTER
        
        if re.match(r"^'[^']*'$", token):
            return TipoToken.CONSTANTE_CARACTER
        
        if token_upper in self.instrucciones:
            return TipoToken.INSTRUCCION
        
        if token_upper in self.pseudoinstrucciones:
            return TipoToken.PSEUDOINSTRUCCION
        
        if token_upper in self.registros:
            return TipoToken.REGISTRO
        
        if re.match(r'^[0-9A-F]+H$', token_upper):
            return TipoToken.CONSTANTE_HEXADECIMAL
        
        if re.match(r'^[01]+B$', token_upper):
            return TipoToken.CONSTANTE_BINARIA
        
        if re.match(r'^\d+$', token):
            return TipoToken.CONSTANTE_DECIMAL
        
        if re.match(r'^\.(?:CODE|DATA|STACK|BSS)$', token_upper):
            return TipoToken.SIMBOLO
        
        if re.match(r'^[A-Z_][A-Z0-9_]*:$', token_upper):
            return TipoToken.SIMBOLO
        
        if re.match(r'^[A-Z_][A-Z0-9_]*$', token_upper):
            return TipoToken.SIMBOLO
        
        return TipoToken.NO_IDENTIFICADO
    
    def cargar_archivo(self, ruta_archivo: str) -> bool:
        try:
            archivo_path = Path(ruta_archivo)
            if not archivo_path.exists():
                return False
            
            with open(archivo_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.lineas_codigo = f.readlines()
            
            self.tokens = []
            for num_linea, linea in enumerate(self.lineas_codigo, 1):
                tokens_linea = self.tokenizar_linea(linea, num_linea)
                self.tokens.extend(tokens_linea)
            
            return True
        except Exception as e:
            print(f"Error al cargar archivo: {e}")
            return False
    
    def analizar_sintaxis(self):
        self.lineas_analizadas = []
        self.tabla_simbolos = {}
        
        segmento_actual = None
        i = 0
        
        while i < len(self.lineas_codigo):
            linea = self.lineas_codigo[i].strip()
            linea_limpia = self.limpiar_comentarios(linea).strip()
            
            if not linea_limpia:
                i += 1
                continue
            
            tokens_linea = self.tokenizar_linea(linea_limpia, i + 1)
            if not tokens_linea:
                i += 1
                continue
            
            primer_token = tokens_linea[0].valor.upper()
            if '.STACK SEGMENT' in linea_limpia.upper():
                segmento_actual = 'STACK'
            elif '.DATA SEGMENT' in linea_limpia.upper():
                segmento_actual = 'DATA'
            elif '.CODE SEGMENT' in linea_limpia.upper():
                segmento_actual = 'CODE'
            elif primer_token == 'ENDS':
                segmento_actual = None
            
            resultado, mensaje = self.validar_linea(tokens_linea, segmento_actual)
            
            if segmento_actual == 'DATA' and len(tokens_linea) >= 3 and tokens_linea[0].tipo == TipoToken.SIMBOLO:
                self.agregar_simbolo(tokens_linea)
            
            self.lineas_analizadas.append({
                'numero': i + 1,
                'linea': linea_limpia,
                'resultado': resultado,
                'mensaje': mensaje
            })
            
            i += 1
    
    def validar_linea(self, tokens: List[Token], segmento: Optional[str]) -> Tuple[str, str]:
        if not tokens:
            return "Correcta", "Línea vacía"
        
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
        
        return "Correcta", "Línea válida"
    
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
            return "Incorrecta", "Debe iniciar con un símbolo"
        
        directiva = tokens[1].valor.upper()
        if directiva not in ['DB', 'DW', 'EQU']:
            return "Incorrecta", f"Directiva inválida: {directiva}"
        
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
        
        primer_token = tokens_a_validar[0].valor.upper()
        
        if tokens_a_validar[0].tipo == TipoToken.PSEUDOINSTRUCCION:
            if primer_token in ['ASSUME', 'PROC', 'ENDP', 'ORG']:
                resultado_msg = f"Pseudoinstrucción {primer_token} válida"
                if mensaje_etiqueta:
                    resultado_msg = f"{mensaje_etiqueta} + {resultado_msg}"
                return "Correcta", resultado_msg
            else:
                return "Incorrecta", f"Pseudoinstrucción {primer_token} no permitida en segmento de código"
        
        if tokens_a_validar[0].tipo == TipoToken.INSTRUCCION:
            if len(tokens_a_validar) < 2 and primer_token not in ['NOP', 'CMC', 'POPA', 'AAD', 'AAM', 'CMPSB']:
                return "Incorrecta", f"Instrucción {primer_token} requiere operandos"
            resultado_msg = f"Instrucción {primer_token} válida"
            if mensaje_etiqueta:
                resultado_msg = f"{mensaje_etiqueta} + {resultado_msg}"
            return "Correcta", resultado_msg
        
        if tokens_a_validar[0].tipo == TipoToken.SIMBOLO and len(tokens_a_validar) > 1:
            return "Incorrecta", f"'{tokens_a_validar[0].valor}' no es una instrucción reconocida (puede ser instrucción no asignada al equipo)"
        
        if tokens_a_validar[0].tipo == TipoToken.SIMBOLO:
            return "Incorrecta", f"'{tokens_a_validar[0].valor}' no es una instrucción reconocida (puede ser instrucción no asignada al equipo)"
        
        if tokens_a_validar[0].tipo == TipoToken.NO_IDENTIFICADO:
            return "Incorrecta", f"Elemento '{tokens_a_validar[0].valor}' no identificado"
        
        return "Incorrecta", "Línea de código con sintaxis inválida"
    
    def agregar_simbolo(self, tokens: List[Token]):
        if len(tokens) < 3:
            return
        
        nombre = tokens[0].valor
        directiva = tokens[1].valor.upper()
        valor = tokens[2].valor if len(tokens) > 2 else ""
        
        tamanio = 0
        if directiva == 'DB':
            tamanio = 1
        elif directiva == 'DW':
            tamanio = 2
        elif directiva == 'EQU':
            tamanio = 0
        
        self.tabla_simbolos[nombre] = Simbolo(nombre, directiva, valor, tamanio)

class EnsambladorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ensamblador 8086 - Fase 1 y 2")
        self.root.geometry("1200x800")
        
        self.ensamblador = Ensamblador8086()
        self.pagina_actual = 0
        self.elementos_por_pagina = 20
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        frame_principal = ttk.Frame(self.root, padding="10")
        frame_principal.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame_principal.columnconfigure(0, weight=1)
        frame_principal.rowconfigure(2, weight=1)
        
        frame_botones = ttk.Frame(frame_principal)
        frame_botones.grid(row=0, column=0, sticky="ew", pady=5)
        
        ttk.Button(frame_botones, text="Cargar Archivo", command=self.cargar_archivo).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Analizar", command=self.analizar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Exportar Resultados", command=self.exportar_resultados).pack(side=tk.LEFT, padx=5)
        
        self.label_archivo = ttk.Label(frame_principal, text="Ningún archivo cargado")
        self.label_archivo.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.notebook = ttk.Notebook(frame_principal)
        self.notebook.grid(row=2, column=0, sticky="nsew", pady=5)
        
        self.frame_codigo = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_codigo, text="Código Fuente")
        self.texto_codigo = scrolledtext.ScrolledText(self.frame_codigo, wrap=tk.WORD, width=80, height=20)
        self.texto_codigo.pack(fill=tk.BOTH, expand=True)
        
        self.frame_tokens = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tokens, text="Tokens Identificados")
        self.texto_tokens = scrolledtext.ScrolledText(self.frame_tokens, wrap=tk.WORD, width=80, height=20)
        self.texto_tokens.pack(fill=tk.BOTH, expand=True)
        
        frame_paginacion = ttk.Frame(self.frame_tokens)
        frame_paginacion.pack(fill=tk.X, pady=5)
        ttk.Button(frame_paginacion, text="← Anterior", command=self.pagina_anterior).pack(side=tk.LEFT, padx=5)
        self.label_pagina = ttk.Label(frame_paginacion, text="Página 1")
        self.label_pagina.pack(side=tk.LEFT, padx=10)
        ttk.Button(frame_paginacion, text="Siguiente →", command=self.pagina_siguiente).pack(side=tk.LEFT, padx=5)
        
        self.frame_analisis = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_analisis, text="Análisis Sintáctico")
        self.texto_analisis = scrolledtext.ScrolledText(self.frame_analisis, wrap=tk.WORD, width=80, height=20)
        self.texto_analisis.pack(fill=tk.BOTH, expand=True)
        
        self.frame_simbolos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_simbolos, text="Tabla de Símbolos")
        self.texto_simbolos = scrolledtext.ScrolledText(self.frame_simbolos, wrap=tk.WORD, width=80, height=20)
        self.texto_simbolos.pack(fill=tk.BOTH, expand=True)
    
    def cargar_archivo(self):
        ruta_archivo = filedialog.askopenfilename(
            title="Seleccionar archivo",
            filetypes=[("Archivos Assembly", "*.asm"), ("Todos los archivos", "*.*")]
        )
        
        if ruta_archivo:
            if self.ensamblador.cargar_archivo(ruta_archivo):
                self.label_archivo.config(text=f"Archivo: {Path(ruta_archivo).name}")
                self.mostrar_codigo()
                self.mostrar_tokens()
                messagebox.showinfo("Éxito", "Archivo cargado correctamente")
            else:
                messagebox.showerror("Error", "No se pudo cargar el archivo")
    
    def mostrar_codigo(self):
        self.texto_codigo.delete(1.0, tk.END)
        for i, linea in enumerate(self.ensamblador.lineas_codigo, 1):
            self.texto_codigo.insert(tk.END, f"{i:4d} | {linea}")
    
    def mostrar_tokens(self):
        self.pagina_actual = 0
        self.actualizar_pagina_tokens()
    
    def actualizar_pagina_tokens(self):
        self.texto_tokens.delete(1.0, tk.END)
        
        inicio = self.pagina_actual * self.elementos_por_pagina
        fin = min(inicio + self.elementos_por_pagina, len(self.ensamblador.tokens))
        
        self.texto_tokens.insert(tk.END, f"{'Núm.':<6} {'Token':<25} {'Tipo':<30} {'Línea':<6}\n")
        self.texto_tokens.insert(tk.END, "=" * 80 + "\n")
        
        for i in range(inicio, fin):
            token = self.ensamblador.tokens[i]
            self.texto_tokens.insert(tk.END, 
                f"{i+1:<6} {token.valor:<25} {token.tipo.value:<30} {token.linea:<6}\n")
        
        total_paginas = (len(self.ensamblador.tokens) + self.elementos_por_pagina - 1) // self.elementos_por_pagina
        self.label_pagina.config(text=f"Página {self.pagina_actual + 1} de {total_paginas}")
    
    def pagina_anterior(self):
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
            self.actualizar_pagina_tokens()
    
    def pagina_siguiente(self):
        total_paginas = (len(self.ensamblador.tokens) + self.elementos_por_pagina - 1) // self.elementos_por_pagina
        if self.pagina_actual < total_paginas - 1:
            self.pagina_actual += 1
            self.actualizar_pagina_tokens()
    
    def analizar(self):
        if not self.ensamblador.lineas_codigo:
            messagebox.showwarning("Advertencia", "Primero debe cargar un archivo")
            return
        
        self.ensamblador.analizar_sintaxis()
        self.mostrar_analisis()
        self.mostrar_tabla_simbolos()
        messagebox.showinfo("Éxito", "Análisis completado")
    
    def mostrar_analisis(self):
        self.texto_analisis.delete(1.0, tk.END)
        
        self.texto_analisis.insert(tk.END, f"{'Línea':<6} {'Resultado':<12} {'Descripción':<50}\n")
        self.texto_analisis.insert(tk.END, "=" * 100 + "\n")
        
        for analisis in self.ensamblador.lineas_analizadas:
            linea_num = analisis['numero']
            linea = analisis['linea'][:40]
            resultado = analisis['resultado']
            mensaje = analisis['mensaje']
            
            self.texto_analisis.insert(tk.END, f"{linea_num:<6} {resultado:<12} {mensaje:<50}\n")
            self.texto_analisis.insert(tk.END, f"       {linea}\n")
            self.texto_analisis.insert(tk.END, "-" * 100 + "\n")
    
    def mostrar_tabla_simbolos(self):
        self.texto_simbolos.delete(1.0, tk.END)
        
        self.texto_simbolos.insert(tk.END, f"{'Símbolo':<20} {'Tipo':<10} {'Valor':<20} {'Tamaño':<10}\n")
        self.texto_simbolos.insert(tk.END, "=" * 70 + "\n")
        
        for simbolo in self.ensamblador.tabla_simbolos.values():
            self.texto_simbolos.insert(tk.END, 
                f"{simbolo.nombre:<20} {simbolo.tipo:<10} {simbolo.valor:<20} {simbolo.tamanio:<10}\n")
    
    def exportar_resultados(self):
        if not self.ensamblador.tokens:
            messagebox.showwarning("Advertencia", "No hay datos para exportar")
            return
        
        ruta_archivo = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        
        if ruta_archivo:
            try:
                with open(ruta_archivo, 'w', encoding='utf-8') as f:
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
                
                messagebox.showinfo("Éxito", "Resultados exportados correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EnsambladorGUI(root)
    root.mainloop()
