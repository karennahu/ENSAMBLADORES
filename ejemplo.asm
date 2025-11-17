; Programa de ejemplo para el ensamblador 8086
; Este archivo demuestra todas las características

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
    mov ax, @data
    mov ds, ax
    
    ; Instrucciones asignadas al equipo 2
    nop
    cmc
    inc ax
    inc bx
    
    mov al, byte ptr [numero]
    mov ax, word ptr [valor]
    
    and ax, 0Fh
    or bx, 1
    xor cx, cx
    
    lea si, mensaje
    
    mov cx, 10
ciclo:
    mul cx
    inc cx
    loope ciclo
    
    cmp ax, bx
    ja etiqueta1
    jc etiqueta2
    jnae etiqueta1
    jne ciclo
    jnle etiqueta1
    
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
