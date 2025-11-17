; Programa con errores intencionales para probar validación

.stack segment
    dw 100h dup(0)
ends

.data segment
    mensaje db "Test"
    numero db 25
    invalido abc xyz    ; Error: falta directiva
ends

.code segment
inicio:
    mov ax, bx          ; Correcto
    nop                 ; Correcto
    add                 ; Error: falta operandos
    mov ax, bx          ; Correcto
    push                ; Error: falta operandos
    jmp inicio          ; Correcto
    sub ax, cx          ; Error: SUB no está asignada
    xor cx, cx          ; Correcto
    hlt                 ; Error: HLT no está asignada
    cmc                 ; Correcto
    invalidainst ax     ; Error: instrucción no válida
ends
end inicio
