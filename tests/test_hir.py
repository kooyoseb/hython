import unittest
from hython.compiler import compile_hir

class HIRTests(unittest.TestCase):
    def test_constant_folding_preserves_offsets(self):
        plain = compile_hir("값 = 2 + 3 * 4\n", optimize=False)
        optimized = compile_hir("값 = 2 + 3 * 4\n", optimize=True)
        self.assertEqual(len(plain.instructions), len(optimized.instructions))
        self.assertGreater(sum(i[0] == "NOP" for i in optimized.instructions), 0)

