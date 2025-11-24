import unittest
from ensamblador import Ensamblador8086

class TestEtiquetas(unittest.TestCase):

    def setUp(self):
        self.asm = Ensamblador8086()

    def test_etiquetas_validas(self):
        pruebas = [
            ("inicio: NOP", "Correcta"),
            ("loop1: XOR AX, BX", "Correcta"),
            ("salto: JA destino", "Correcta"),
            ("ciclo: LOOPE etiqueta", "Correcta"),
        ]

        for linea, esperado in pruebas:
            resultado = self.asm.validar_linea(linea)
            self.assertEqual(resultado, esperado, f"Falló con: {linea}")

    def test_etiquetas_invalidas(self):
        pruebas = [
            ("inicio: MOV AX, BX", "Incorrecta"),
            ("etiq: ADD AX, 5", "Incorrecta"),
            ("prueba: JMP t", "Incorrecta"),
            ("xyz: HLT", "Incorrecta"),
        ]

        for linea, esperado in pruebas:
            resultado = self.asm.validar_linea(linea)
            self.assertEqual(resultado, esperado, f"Falló con: {linea}")


if __name__ == '__main__':
    unittest.main()
