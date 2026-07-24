import unittest
from hython.compiler import compile_source
from hython.vm import VM

class LoopElseTests(unittest.TestCase):
    def test_for_iterable_unparenthesized_tuple_and_trailing_comma(self):
        source='결과=[]\nfor 값 in [1],[2],:\n    결과.append(값)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[[1],[2]])

    def test_async_for_iterable_tuple_syntax_compiles(self):
        compile_source('async def 함수():\n    async for 값 in 첫째,둘째,: pass\n')
    def run_source(self,source):
        vm=VM(); vm.run(compile_source(source)); return vm.globals

    def test_for_else_normal_and_break(self):
        normal=self.run_source('결과 = []\n포 값 인 레인지(3):\n    결과.append(값)\n엘스:\n    결과.append("완료")\n')["결과"]
        broken=self.run_source('결과 = []\n포 값 인 레인지(3):\n    브레이크\n엘스:\n    결과.append("실행안됨")\n')["결과"]
        self.assertEqual(normal,[0,1,2,"완료"]); self.assertEqual(broken,[])

    def test_while_else(self):
        source='값 = 0\n와일 값 < 2:\n    값 += 1\n엘스:\n    값 += 40\n결과 = 값\n'
        self.assertEqual(self.run_source(source)["결과"],42)
