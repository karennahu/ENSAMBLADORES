import unittest
from ensamblador import Ensamblador8086

class TestValidacion(unittest.TestCase):

    def setUp(self):
        self.asm = Ensamblador8086()

    def test_instrucciones_validas(self):
        lineas_validas = [
            "NOP",
            "CMC",
            "XOR AX, BX",
            "AND AL, 10",
            "INC CX",
            "IDIV BX",
            "LEA AX, [BX]",
            "INT 21h",
            "JA etiqueta",
            "JC salto",
            "LOOPE ciclo",
        ]

        for linea in lineas_validas:
            resultado = self.asm.validar_linea(linea)
            self.assertEqual(resultado, "Correcta", f"Falló con: {linea}")

    def test_instrucciones_invalidas(self):
        lineas_invalidas = [
            "MOV AX, BX",
            "ADD AX, 1",
            "PUSH AX",
            "SUB BX, AX",
            "HLT",
            "JMP etiqueta",
            "invalid instruction",
            "XYZ",
        ]

        for linea in lineas_invalidas:
            resultado = self.asm.validar_linea(linea)
            self.assertEqual(resultado, "Incorrecta", f"No detectó error en: {linea}")


if __name__ == '__main__':
    unittest.main()
