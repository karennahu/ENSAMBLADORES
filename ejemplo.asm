; Programa de ejemplo para el ensamblador 8086
; Usa SOLO las instrucciones asignadas al equipo 2:
; CMC, CMPSB, NOP, POPA, AAD, AAM, MUL, INC, IDIV, INT
; AND, LEA, OR, XOR, JNAE, JNE, JNLE, LOOPE, JA, JC

.stack segment
    dw 100h dup(0)
ends

.data segment
    mensaje db "Hola Mundo"
    numero db 25
    valor dw 1000h
    contador dw 100 dup(0)
    letra db 'A'
    constante equ 255
ends

.code segment
    assume cs:.code, ds:.data, ss:.stack
    
inicio:
    nop
    cmc
    
    inc ax
    inc bx
    inc cx
    
    and ax, 0Fh
    or bx, 1
    xor cx, cx
    
    lea si, mensaje
    lea di, contador
    
ciclo:
    inc ax
    mul cx
    loope ciclo
    
    jnae etiqueta1
    jne etiqueta2
    jnle etiqueta1
    ja etiqueta2
    jc etiqueta1
    
etiqueta1:
    aam
    aad
    popa
    cmpsb
    
etiqueta2:
    idiv bx
    int 21h
    
ends
end inicio
