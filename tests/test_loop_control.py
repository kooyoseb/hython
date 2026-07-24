import unittest
from hython.compiler import CompileError, compile_source
from hython.vm import VM

class LoopControlTests(unittest.TestCase):
    def test_for_attribute_and_subscript_targets(self):
        source='클래스 상자: 패스\n대상=상자()\n자료=[0]\n결과=[]\n포 대상.값 인 [20, 21]: 결과.append(대상.값)\n포 자료[0] 인 [41, 42]: 패스\n결과=(결과, 자료[0])\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],([20,21],42))
    def test_break_continue_and_augmented_assignment(self):
        source='합 = 0\n포 수 인 레인지(10):\n    이프 수 == 2:\n        컨티뉴\n    이프 수 == 5:\n        브레이크\n    합 += 수\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["합"],8)

    def test_break_outside_loop_is_compile_error(self):
        with self.assertRaisesRegex(CompileError,"루프 밖"):
            compile_source("브레이크\n")
