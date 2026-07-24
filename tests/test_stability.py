import random
import tempfile
import unittest
from pathlib import Path

from hython.bytecode import BytecodeError, dumps, loads, write
from hython.compiler import compile_source
from hython.translator import compile_hython
from hython.vm import VM


class StabilityTests(unittest.TestCase):
    def native(self, source):
        vm = VM()
        vm.run(loads(dumps(compile_source(source))))
        return vm.globals

    def compatible(self, source):
        namespace = {}
        exec(compile_hython(source), namespace)
        return namespace

    def test_native_and_compatibility_arithmetic_agree(self):
        randomizer = random.Random(1000)
        operators = ["+", "-", "*", "//", "%"]
        for case in range(200):
            left = randomizer.randint(-1000, 1000)
            right = randomizer.randint(1, 1000)
            operator = randomizer.choice(operators)
            source = f"결과 = ({left} {operator} {right}) * 3 + 7\n"
            with self.subTest(case=case, source=source):
                self.assertEqual(self.native(source)["결과"], self.compatible(source)["결과"])

    def test_large_loop_is_stable(self):
        source = "합계 = 0\n포 숫자 인 레인지(100000):\n    합계 += 숫자\n"
        self.assertEqual(self.native(source)["합계"], 4_999_950_000)

    def test_repeated_function_calls_do_not_leak_stack_values(self):
        source = "데프 더하기(값):\n    리턴 값 + 1\n결과 = 0\n포 숫자 인 레인지(20000):\n    결과 = 더하기(결과)\n"
        self.assertEqual(self.native(source)["결과"], 20000)

    def test_recursive_calls(self):
        source = "데프 팩토리얼(수):\n    이프 수 <= 1:\n        리턴 1\n    리턴 수 * 팩토리얼(수 - 1)\n결과 = 팩토리얼(100)\n"
        self.assertEqual(self.native(source)["결과"], __import__("math").factorial(100))

    def test_large_collection_round_trip(self):
        source = "자료 = []\n포 숫자 인 레인지(10000):\n    자료.append(숫자 * 2)\n결과 = 렌(자료)\n"
        values = self.native(source)
        self.assertEqual(values["결과"], 10000)
        self.assertEqual(values["자료"][-1], 19998)

    def test_native_module_is_executed_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root / "상태.hbc", compile_source("횟수 = 1\n", str(root / "상태.hy")))
            main = compile_source("인폴트 상태 애즈 첫째\n인폴트 상태 애즈 둘째\n결과 = 첫째 이즈 둘째\n", str(root / "main.hy"))
            vm = VM([root])
            vm.run(main)
            self.assertIs(vm.globals["결과"], True)
            self.assertEqual(len(vm.modules), 1)

    def test_truncation_at_every_header_boundary_is_rejected(self):
        artifact = dumps(compile_source("값 = 42\n"))
        for size in range(0, 42):
            with self.subTest(size=size), self.assertRaises(BytecodeError):
                loads(artifact[:size])

    def test_corruption_samples_are_rejected(self):
        original = dumps(compile_source("값 = 42\n"))
        for index in range(0, len(original), max(1, len(original) // 25)):
            corrupted = bytearray(original)
            corrupted[index] ^= 0xFF
            with self.subTest(index=index), self.assertRaises(BytecodeError):
                loads(bytes(corrupted))

