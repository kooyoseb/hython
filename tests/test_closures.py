import unittest
from hython.compiler import compile_source
from hython.vm import VM

class ClosureTests(unittest.TestCase):
    def test_nested_class_can_assign_nonlocal_function_binding(self):
        source='데프 바깥():\n    값=1\n    클래스 대상:\n        논로컬 값\n        값=42\n    리턴 (값, 대상.__name__)\n결과=바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,"대상"))

    def test_nonlocal_in_nested_class_skips_enclosing_class_namespace(self):
        source='데프 바깥():\n    값=1\n    클래스 외부:\n        값=2\n        클래스 내부:\n            논로컬 값\n            값=42\n    리턴 (값, 외부.값)\n결과=바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,2))

    def test_nonlocal_read_in_nested_class_skips_enclosing_class_namespace(self):
        source='데프 바깥():\n    값=1\n    클래스 외부:\n        값=2\n        클래스 내부:\n            논로컬 값\n            읽음=값\n    리턴 (값, 외부.내부.읽음)\n결과=바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(1,1))

    def test_class_scope_uses_outer_closure_and_implicit_class_cell(self):
        source='\n'.join([
            '클래스 기본:',
            '    데프 값(셀프):',
            '        리턴 40',
            '데프 생성(추가):',
            '    클래스 파생(기본):',
            '        클래스값 = 100',
            '        데프 값(셀프):',
            '            리턴 수퍼().값() + 추가',
            '    리턴 파생',
            '파생 = 생성(2)',
            '결과 = (파생().값(), 파생.__mro__[1] 이즈 기본)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(42,True))
    def test_nested_function_captures_outer_values(self):
        source='데프 곱셈기(배수):\n    데프 곱하기(값):\n        리턴 값 * 배수\n    리턴 곱하기\n세배 = 곱셈기(3)\n결과 = 세배(14)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],42)

    def test_each_closure_has_independent_capture(self):
        source='데프 생성(값):\n    데프 읽기():\n        리턴 값\n    리턴 읽기\n하나 = 생성(1)\n둘 = 생성(2)\n결과 = (하나(), 둘())\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(1,2))

    def test_nonlocal_mutates_live_outer_frame(self):
        source='데프 카운터():\n    값 = 0\n    데프 증가():\n        논로컬 값\n        값 += 1\n        리턴 값\n    리턴 증가\n가 = 카운터()\n나 = 카운터()\n결과 = (가(), 가(), 나(), 가())\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(1,2,1,3))

    def test_local_read_before_assignment_does_not_fall_back_to_global(self):
        source='값 = 10\n데프 함수():\n    이전 = 값\n    값 = 20\n    리턴 이전\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaises(UnboundLocalError): vm.globals["함수"]()

    def test_nonlocal_finds_binding_beyond_immediate_parent(self):
        source='데프 바깥():\n    값 = 1\n    데프 중간():\n        데프 안쪽():\n            논로컬 값\n            값 += 1\n            리턴 값\n        리턴 안쪽\n    함수 = 중간()\n    리턴 (함수(), 함수(), 값)\n결과 = 바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(2,3,3))

    def test_nonlocal_declaration_applies_inside_try_code_objects(self):
        source='데프 바깥():\n    값 = 1\n    데프 변경():\n        논로컬 값\n        트라이:\n            값 = 42\n        파이널리:\n            패스\n    변경()\n    리턴 값\n결과 = 바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)

    def test_global_declared_in_try_applies_to_following_function_body(self):
        source='값 = 1\n데프 변경():\n    트라이:\n        글로벌 값\n    파이널리:\n        패스\n    값 = 42\n변경()\n결과 = 값\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)

    def test_nonlocal_reads_live_cell_after_sibling_mutation(self):
        source='데프 바깥():\n    값 = 0\n    데프 설정(새값):\n        논로컬 값\n        값 = 새값\n    데프 시험():\n        논로컬 값\n        값 = 1\n        설정(2)\n        리턴 값\n    리턴 시험()\n결과 = 바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],2)

    def test_async_function_can_delete_nonlocal_cell(self):
        import asyncio
        source='데프 바깥():\n    값 = 1\n    어싱크 데프 삭제():\n        논로컬 값\n        델 값\n    리턴 삭제\n삭제함수 = 바깥()\n'
        vm=VM(); vm.run(compile_source(source)); function=vm.globals["삭제함수"]
        asyncio.run(function())
        self.assertNotIn("값",function.closure)

    def test_nonlocal_declaration_applies_to_def_class_import_and_named_expression(self):
        source='데프 바깥():\n    함수=넌\n    종류=넌\n    모듈=넌\n    값=0\n    데프 변경():\n        논로컬 함수, 종류, 모듈, 값\n        데프 함수(): 리턴 40\n        클래스 종류: 패스\n        인폴트 math 애즈 모듈\n        (값 := 2)\n    변경()\n    리턴 (함수()+값, 종류.__name__, 모듈.sqrt(9))\n결과=바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,"종류",3))
