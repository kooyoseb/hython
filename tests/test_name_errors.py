import asyncio
import unittest

from hython.compiler import compile_source
from hython.vm import VM


class NameErrorTests(unittest.TestCase):
    def test_undefined_module_name_raises_name_error(self):
        with self.assertRaises(NameError):
            VM().run(compile_source("결과 = 없는이름\n"))

    def test_deleting_unbound_function_local_raises_unbound_local_error(self):
        vm=VM(); vm.run(compile_source("데프 함수():\n    델 값\n"))
        with self.assertRaises(UnboundLocalError): vm.globals["함수"]()

    def test_deleting_missing_declared_global_raises_name_error(self):
        vm=VM(); vm.run(compile_source("데프 함수():\n    글로벌 값\n    델 값\n"))
        with self.assertRaises(NameError): vm.globals["함수"]()

    def test_deleted_nonlocal_does_not_fall_back_to_global(self):
        source='값=99\n데프 바깥():\n    값=1\n    데프 안쪽():\n        논로컬 값\n        델 값\n        리턴 값\n    리턴 안쪽\n함수=바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaises(NameError): vm.globals["함수"]()

    def test_async_delete_uses_python_error_types(self):
        vm=VM(); vm.run(compile_source("어싱크 데프 함수():\n    델 값\n"))
        with self.assertRaises(UnboundLocalError): asyncio.run(vm.globals["함수"]())
