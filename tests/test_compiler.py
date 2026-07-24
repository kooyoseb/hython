import unittest
from contextlib import redirect_stdout
from io import StringIO
from hython.bytecode import BytecodeError, CodeObject, dumps, loads
from hython.compiler import CompileError,compile_source
from hython.vm import VM

class CompilerTests(unittest.TestCase):
    def test_rejects_statements_outside_required_function_context(self):
        invalid=[
            "리턴 1\n",
            "일드 1\n",
            "어웨이트 작업\n",
            "데프 함수():\n    리턴 어웨이트 작업\n",
            "어싱크 포 값 인 자료:\n    패스\n",
            "어싱크 위드 문맥():\n    패스\n",
            "데프 함수():\n    논로컬 값\n",
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(CompileError): compile_source(source)

    def test_rejects_global_nonlocal_declaration_conflicts(self):
        invalid=[
            "데프 함수(값):\n    글로벌 값\n",
            "데프 바깥():\n    값=1\n    데프 안(값):\n        논로컬 값\n",
            "데프 바깥():\n    값=1\n    데프 안():\n        글로벌 값\n        논로컬 값\n",
            "데프 함수():\n    프린트(값)\n    글로벌 값\n",
            "데프 함수():\n    값=1\n    글로벌 값\n",
            "데프 바깥():\n    값=1\n    데프 안():\n        프린트(값)\n        논로컬 값\n",
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(CompileError): compile_source(source)

    def test_definition_time_expressions_count_as_use_before_global(self):
        invalid=(
            '데프 바깥():\n    데프 안쪽(값=이름): 패스\n    글로벌 이름\n',
            '데프 바깥():\n    클래스 안쪽(기반): 패스\n    글로벌 기반\n',
            '데프 바깥():\n    @장식\n    데프 안쪽(값=이름): 패스\n    글로벌 이름\n',
        )
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(CompileError): compile_source(source)
        compile_source('데프 바깥():\n    데프 안쪽(값: 이름): 패스\n    글로벌 이름\n')

    def test_rejects_async_collection_comprehension_outside_async_function(self):
        for source in ("결과=[값 어싱크 포 값 인 자료]\n","결과={값 어싱크 포 값 인 자료}\n"):
            with self.subTest(source=source),self.assertRaises(CompileError): compile_source(source)

    def test_rejects_context_sensitive_python_syntax(self):
        invalid=[
            '어싱크 데프 생성():\n    일드 1\n    리턴 2\n',
            '어싱크 데프 생성():\n    일드 1\n    리턴 넌\n',
            '어싱크 데프 생성():\n    일드 프롬 [1]\n',
            '데프 함수():\n    프롬 math 인폴트 *\n',
            '클래스 대상:\n    프롬 math 인폴트 *\n',
            '데프 함수():\n    트라이:\n        브레이크\n    파이널리:\n        패스\n',
            '데프 함수():\n    와일 폴스:\n        패스\n    엘스:\n        컨티뉴\n',
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(CompileError): compile_source(source)

    def test_named_expression_parentheses_rules(self):
        invalid=[
            '값 := 1\n',
            '결과 = 값 := 1\n',
            '결과 = 값 := 1, 2\n',
            '함수(키=값 := 1)\n',
            '어설트 값 := 1\n',
            '데프 함수():\n    리턴 값 := 1\n',
            '데프 함수():\n    일드 값 := 1\n',
            '위드 문맥 := 생성():\n    패스\n',
            '데프 함수(값=기본 := 1):\n    패스\n',
            '함수 = 람다: 값 := 1\n',
            '자료={"키": 값 := 1}\n',
            '자료={키 := 1: "값"}\n',
            '값: (형식 := 인트) = 1\n',
            '데프 함수(값: (형식 := 인트)):\n    패스\n',
            '데프 함수() -> (형식 := 인트):\n    패스\n',
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)

        valid='결과=(값 := 1)\n목록=[다른값 := 2]\n자료={"키": (셋째 := 3)}\n함수(인자 := 3)\n이프 조건 := 트루:\n    패스\n'
        compile_source(valid)

    def test_rejects_duplicate_definition_and_call_names(self):
        invalid=[
            "데프 함수(값, 값): 패스\n",
            "데프 함수(값, *값): 패스\n",
            "데프 함수(값, **값): 패스\n",
            "데프 함수(*): 패스\n",
            "함수(값=1, 값=2)\n",
            "클래스 대상(메타클래스=타입, 메타클래스=타입): 패스\n",
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_compiles_and_runs_independent_bytecode(self):
        source = "데프 제곱(값):\n    리턴 값 * 값\n포 수 인 레인지(3):\n    프린트(제곱(수))\n"
        code = loads(dumps(compile_source(source)))
        output = StringIO()
        with redirect_stdout(output): VM().run(code)
        self.assertEqual(output.getvalue(), "0\n1\n4\n")

    def test_detects_tampering(self):
        data = bytearray(dumps(compile_source("값 = 1\n")))
        data[-1] ^= 1
        with self.assertRaises(BytecodeError): loads(bytes(data))

    def test_rejects_unknown_opcode_even_with_valid_checksum(self):
        data=dumps(CodeObject("악성",[],[],[["EXEC_PYTHON"]]))
        with self.assertRaisesRegex(BytecodeError,"허용되지 않은"): loads(data)

    def test_rejects_statically_detectable_stack_underflow(self):
        data=dumps(CodeObject("악성",[],[None],[["POP"],["CONST",0],["RETURN"]]))
        with self.assertRaisesRegex(BytecodeError,"스택 언더플로"): loads(data)
