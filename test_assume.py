import unittest
from ensamblador import Ensamblador8086

class TestAssume(unittest.TestCase):

    def setUp(self):
        self.asm = Ensamblador8086()

    def test_assume_correcto(self):
        linea = "ASSUME CS:code, DS:data"
        resultado = self.asm.validar_linea(linea)
        self.assertEqual(resultado, "Correcta")

    def test_assume_incorrecto(self):
        linea = "ASSUME XYZ"
        resultado = self.asm.validar_linea(linea)
        self.assertEqual(resultado, "Incorrecta")


if __name__ == '__main__':
    unittest.main()
