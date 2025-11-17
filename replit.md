# Ensamblador 8086 - Proyecto Universitario

## Descripción General
Ensamblador didáctico para procesador 8086 que implementa las Fases 1 y 2 del proyecto de curso. Realiza análisis léxico, sintáctico y semántico de código assembly, generando una tabla de símbolos completa.

## Estado Actual del Proyecto
**Fecha:** 17 de noviembre de 2025
**Versión:** 1.0
**Estado:** Desarrollo activo - Fases 1 y 2 implementadas

## Funcionalidades Implementadas

### Fase 1 - Separación e Identificación de Elementos
- ✅ Carga de archivos .asm desde cualquier ubicación
- ✅ Validación de existencia de archivos
- ✅ Visualización del código fuente con numeración
- ✅ Tokenización respetando elementos compuestos:
  - `.code segment`, `.data segment`, `.stack segment`
  - `byte ptr`, `word ptr`
  - `dup(xxx)`, `[xxx]`
  - Cadenas `"xxx"` y caracteres `'x'`
- ✅ Eliminación automática de comentarios (`;`)
- ✅ Identificación de tipos de elementos:
  - Pseudoinstrucciones
  - Instrucciones (CMC, CMPSB, NOP, POPA, AAD, AAM, MUL, INC, IDIV, INT, AND, LEA, OR, XOR, JNAE, JNE, JNLE, LOOPE, JA, JC)
  - Registros (AX, BX, CX, DX, etc.)
  - Símbolos
  - Constantes (decimal, hexadecimal, binaria, caracter)
- ✅ Visualización paginada de elementos (20 por página)

### Fase 2 - Análisis Sintáctico y Semántico
- ✅ Validación de sintaxis de segmentos .stack, .data y .code
- ✅ Análisis línea por línea con resultado "Correcta" o "Incorrecta"
- ✅ Mensajes descriptivos de error
- ✅ Tabla de símbolos con campos:
  - Símbolo
  - Tipo (DB, DW, EQU)
  - Valor
  - Tamaño (bytes)
- ✅ Exportación de resultados a archivo de texto

## Arquitectura del Proyecto

### Estructura de Archivos
```
/
├── ensamblador.py          # Código principal del ensamblador
├── ejemplo.asm             # Archivo de ejemplo para pruebas
├── replit.md              # Documentación del proyecto
├── .gitignore             # Archivos a ignorar en git
└── attached_assets/       # Especificaciones del proyecto
    ├── Pasted-Separaci-n-de-elementos...txt
    ├── Pasted-A-Identificaci-n-de-l-neas...txt
    └── image_1763338134106.png
```

### Componentes Principales

#### Clase `Ensamblador8086`
Núcleo del análisis léxico, sintáctico y semántico:
- `tokenizar_linea()`: Separa elementos respetando compuestos
- `identificar_tipo_token()`: Clasifica cada token
- `analizar_sintaxis()`: Valida estructura del programa
- `validar_segmento_*()`: Valida sintaxis de cada segmento

#### Clase `EnsambladorGUI`
Interfaz gráfica con Tkinter:
- Pestañas para código fuente, tokens, análisis y símbolos
- Navegación paginada de resultados
- Exportación de análisis completo

## Instrucciones de Uso

### Ejecutar el Ensamblador
1. Haz clic en el botón "Run" o ejecuta `python ensamblador.py`
2. Se abrirá la interfaz gráfica

### Analizar un Archivo
1. Click en "Cargar Archivo"
2. Selecciona un archivo .asm (puedes usar `ejemplo.asm`)
3. El código se mostrará en la pestaña "Código Fuente"
4. Los tokens se listarán automáticamente en "Tokens Identificados"
5. Click en "Analizar" para validación sintáctica
6. Revisa resultados en pestañas "Análisis Sintáctico" y "Tabla de Símbolos"
7. Click en "Exportar Resultados" para guardar el análisis

## Especificaciones Técnicas

### Separadores de Elementos
- Espacio
- Dos puntos (`:`)
- Coma (`,`)

### Elementos Compuestos (no se separan)
- `.code segment`, `.data segment`, `.stack segment`
- `byte ptr`, `word ptr`
- `dup(xxx)` donde xxx es cualquier contenido
- `[xxx]` direccionamiento entre corchetes
- `"xxx"` cadenas con comillas dobles
- `'x'` caracteres con comillas simples

### Instrucciones Soportadas (Equipo 2)
CMC, CMPSB, NOP, POPA, AAD, AAM, MUL, INC, IDIV, INT, AND, LEA, OR, XOR, JNAE, JNE, JNLE, LOOPE, JA, JC

### Sintaxis Validada

#### Segmento de Pila
```
.stack segment
    dw constante dup(constante)
ends
```

#### Segmento de Datos
```
.data segment
    simbolo db constante_caracter
    simbolo db constante_numerica
    simbolo dw constante
    simbolo equ constante
ends
```

#### Segmento de Código
```
.code segment
    etiqueta:
    instruccion operandos
ends
end etiqueta_inicio
```

## Características Destacadas

### Manejo Robusto de Elementos Compuestos
El tokenizador utiliza un sistema de marcadores temporales que:
1. Identifica elementos compuestos con regex
2. Los reemplaza temporalmente por marcadores únicos
3. Tokeniza el texto modificado
4. Restaura los elementos originales

Esto garantiza que elementos como `byte ptr [bx+si]` se mantengan unidos correctamente.

### Análisis Sintáctico Contextual
El analizador mantiene el estado del segmento actual para aplicar reglas de validación específicas a cada tipo de segmento.

### Tabla de Símbolos Completa
Incluye información completa de cada símbolo:
- Nombre del símbolo
- Tipo de directiva (DB, DW, EQU)
- Valor inicial
- Tamaño en bytes

## Tecnologías Utilizadas
- **Lenguaje:** Python 3.11
- **GUI:** Tkinter
- **Procesamiento:** Regex (re module)
- **Estructuras:** Dataclasses, Enums

## Cambios Recientes
- **2025-11-17:** Implementación inicial completa de Fase 1 y Fase 2
  - Tokenizador con soporte completo para elementos compuestos
  - Análisis léxico de 20 instrucciones asignadas
  - Validación sintáctica de segmentos
  - Generación de tabla de símbolos
  - Interfaz gráfica funcional con exportación

## Próximas Fases (Pendientes)
- **Fase 3:** Generación de código objeto
- **Fase 4:** Enlazado y generación de ejecutable
- Optimizaciones y validaciones adicionales

## Notas de Desarrollo
- El proyecto respeta todas las especificaciones del documento de requisitos
- Todas las instrucciones no asignadas se consideran símbolos
- Los comentarios (líneas con `;`) se eliminan automáticamente
- La paginación facilita la visualización de programas largos

## Autor
Proyecto universitario - Curso de Ensambladores
