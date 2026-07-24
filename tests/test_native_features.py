import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.vm import VM

class NativeFeatureTests(unittest.TestCase):
    def test_not_binds_looser_than_comparisons_but_tighter_than_and_or(self):
        source='결과=(not 0 == 2, not 1 < 2, not 1 == 2 and 3, not 1 == 2 or 0)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,False,3,True))
    def test_extended_literals_survive_hbc_round_trip(self):
        source='문자 = "하이" "썬"\n바이트 = b"hy" b"thon"\n복소수 = 2j + 3\n생략 = ...\n결과 = (문자, 바이트, 복소수, 생략 이즈 ...)\n'
        vm=VM(); vm.run(loads(dumps(compile_source(source))))
        self.assertEqual(vm.globals["결과"],("하이썬",b"hython",3+2j,True))
    def run_source(self, source):
        vm=VM(); vm.run(compile_source(source)); return vm.globals

    def test_dictionary_and_subscript_assignment(self):
        values=self.run_source('자료 = {"이름": "하이썬", "버전": 1}\n자료["버전"] = 자료["버전"] + 1\n결과 = 자료["버전"]\n')
        self.assertEqual(values["결과"],2)

    def test_attribute_and_boolean_expression(self):
        values=self.run_source('문자 = "hython"\n결과 = 문자.upper() == "HYTHON" 앤드 렌(문자) > 3\n')
        self.assertIs(values["결과"],True)

    def test_boolean_operators_short_circuit(self):
        values=self.run_source('횟수 = [0]\n데프 호출():\n    횟수[0] = 횟수[0] + 1\n    리턴 트루\n왼쪽 = 폴스 앤드 호출()\n오른쪽 = 트루 오어 호출()\n결과 = 횟수[0]\n')
        self.assertEqual(values["결과"],0)

    def test_bitwise_shift_and_invert_precedence(self):
        source='결과 = ((5 | 2) ^ (12 & 10), 3 << 4, 128 >> 3, ~5)\n'
        native=self.run_source(source)["결과"]; compatible={}
        from hython.translator import compile_hython
        exec(compile_hython(source),compatible)
        self.assertEqual(native,compatible["결과"])
