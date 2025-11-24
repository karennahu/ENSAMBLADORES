import unittest
from ensamblador import Ensamblador8086

class TestEnsamblador(unittest.TestCase):

    def setUp(self):
        self.asm = Ensamblador8086()

    def test_tokenizacion(self):
        linea = "XOR AX, BX"
        tokens = self.asm.tokenizar(linea)

        instrucciones = [t.valor for t in tokens if t.tipo == "INSTRUCCION"]
        registros = [t.valor for t in tokens if t.tipo == "REGISTRO"]

        self.assertIn("XOR", instrucciones)
        self.assertIn("AX", registros)
        self.assertIn("BX", registros)

    def test_token_invalido(self):
        linea = "MOV AX, BX"
        tokens = self.asm.tokenizar(linea)

        tipos = [t.tipo for t in tokens]
        self.assertIn("NO_IDENTIFICADO", tipos)


if __name__ == '__main__':
    unittest.main()
