import tempfile
import types
import unittest
from pathlib import Path
from hython.bytecode import write
from hython.compiler import compile_source
from hython.vm import VM

class ControlImportTests(unittest.TestCase):
    def test_future_import_position_and_feature_validation(self):
        compile_source('"문서"\nfrom __future__ import (annotations as 주석,)\n')
        invalid=(
            '값=1\nfrom __future__ import annotations\n',
            'def 함수():\n    from __future__ import annotations\n',
            'class 대상:\n    from __future__ import annotations\n',
            'from __future__ import 없는기능\n',
            'from __future__ import braces\n',
            'from __future__ import *\n',
        )
        for source in invalid:
                with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_barry_future_switches_not_equal_spelling(self):
        source='from __future__ import barry_as_FLUFL\n결과=(1 <> 2, 1 <> 1)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,False))
        with self.assertRaises(SyntaxError): compile_source('결과=1 <> 2\n')
        with self.assertRaises(SyntaxError): compile_source('from __future__ import barry_as_FLUFL\n결과=1 != 2\n')
    def test_relative_import_accepts_ellipsis_token_depth(self):
        from hython.frontend import parse
        tree=parse('from ...꾸러미 import 값\nfrom .... import 다른값\n')
        self.assertEqual([node.value[0] for node in tree.children],["...꾸러미","...."])

    def test_relative_import_without_parent_package_raises_import_error(self):
        with tempfile.TemporaryDirectory() as directory:
            code=compile_source('프롬 . 인폴트 값\n',str(Path(directory)/"main.hy"))
            with self.assertRaisesRegex(ImportError,"no known parent package"):
                VM([Path(directory)]).run(code)

    def test_import_star_grammar_restrictions(self):
        for source in ('import *\n','from 모듈 import * as 전체\n','from 모듈 import *, 값\n','from 모듈 import (*)\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_from_import_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); write(root/"도구.hbc",compile_source("정답 = 42\n",str(root/"도구.hy")))
            vm=VM([root]); vm.run(compile_source("프롬 도구 인폴트 정답 애즈 값\n결과 = 값\n",str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42)

    def test_multiple_and_dotted_native_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(root/"가.hbc",compile_source("값 = 10\n",str(root/"가.hy")))
            write(root/"나.hbc",compile_source("값 = 20\n",str(root/"나.hy")))
            write(package/"수학.hbc",compile_source("정답 = 12\n",str(package/"수학.hy")))
            source='인폴트 가 애즈 첫째, 나 애즈 둘째\n프롬 도구.수학 인폴트 정답 애즈 셋째\n결과 = 첫째.값 + 둘째.값 + 셋째\n'
            vm=VM([root]); vm.run(compile_source(source,str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42)

    def test_dotted_import_binds_package_and_attaches_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"수학.hbc",compile_source("정답 = 42\n",str(package/"수학.hy")))
            source="인폴트 도구.수학\n결과 = 도구.수학.정답\n"
            vm=VM([root]); vm.run(compile_source(source,str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42)
            self.assertEqual(vm.globals["도구"].__path__,[str(package.resolve())])

    def test_dotted_import_initializes_parent_package_before_child(self):
        import builtins
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"__init__.hbc",compile_source('인폴트 builtins\nbuiltins._hython_import_events.append("parent")\n',str(package/"__init__.hy")))
            write(package/"자식.hbc",compile_source('인폴트 builtins\nbuiltins._hython_import_events.append("child")\n',str(package/"자식.hy")))
            builtins._hython_import_events=[]
            try:
                vm=VM([root]); vm.run(compile_source('인폴트 도구.자식\n',str(root/"main.hy")))
                self.assertEqual(builtins._hython_import_events,["parent","child"])
                self.assertIs(vm.modules["도구"].자식,vm.modules["도구.자식"])
            finally: del builtins._hython_import_events

    def test_dotted_import_with_alias_binds_leaf_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"수학.hbc",compile_source("정답 = 42\n",str(package/"수학.hy")))
            source="인폴트 도구.수학 애즈 수학\n결과 = 수학.정답\n"
            vm=VM([root]); vm.run(compile_source(source,str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42)

    def test_star_import_only_exposes_public_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); write(root/"도구.hbc",compile_source("공개 = 42\n_숨김 = 99\n",str(root/"도구.hy")))
            vm=VM([root]); vm.run(compile_source("프롬 도구 인폴트 *\n결과 = 공개\n",str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42); self.assertNotIn("_숨김",vm.globals)

    def test_star_import_honors_all(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/"도구.hbc",compile_source('__all__ = ["공개"]\n공개 = 42\n숨김 = 99\n',str(root/"도구.hy")))
            vm=VM([root]); vm.run(compile_source("프롬 도구 인폴트 *\n결과 = 공개\n",str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42); self.assertNotIn("숨김",vm.globals)

    def test_module_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"__init__.hbc",compile_source("값 = 42\n",str(package/"__init__.hy")))
            vm=VM([root]); vm.run(compile_source("인폴트 도구 애즈 모듈\n결과 = (모듈.__name__, 모듈.__package__, 모듈.__file__)\n",str(root/"main.hy")))
            name,package_name,filename=vm.globals["결과"]
            self.assertEqual((name,package_name),("도구","도구"))
            self.assertEqual(Path(filename),package/"__init__.hbc")

    def test_hbc_modules_expose_standard_module_spec_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"값.hbc",compile_source("정답=42\n",str(package/"값.hy")))
            write(package/"__init__.hbc",compile_source("프롬 . 인폴트 값\n",str(package/"__init__.hy")))
            vm=VM([root]); vm.run(compile_source("인폴트 도구\n결과=(도구, 도구.값)\n",str(root/"main.hy")))
            parent,child=vm.globals["결과"]
            self.assertIsInstance(parent,types.ModuleType); self.assertIsInstance(child,types.ModuleType)
            self.assertEqual((parent.__name__,child.__name__),("도구","도구.값"))
            self.assertEqual((parent.__package__,child.__package__),("도구","도구"))
            self.assertEqual((parent.__spec__.name,child.__spec__.name),("도구","도구.값"))
            self.assertTrue(parent.__spec__.submodule_search_locations)
            self.assertIs(parent.값,vm.modules["도구.값"])

    def test_relative_and_absolute_import_share_resolved_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"값.hbc",compile_source("정답 = 42\n",str(package/"값.hy")))
            vm=VM([root])
            absolute=vm.import_module("도구.값",compile_source("",str(root/"main.hy")))
            relative=vm.import_module(".값",compile_source("",str(package/"main.hy")))
            self.assertIs(absolute,relative)

    def test_from_relative_package_imports_submodule(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"값.hbc",compile_source("정답 = 42\n",str(package/"값.hy")))
            vm=VM([root]); code=compile_source("프롬 . 인폴트 값\n결과 = 값.정답\n",str(package/"main.hy"))
            vm.run(code)
            self.assertEqual(vm.globals["결과"],42)

    def test_from_package_falls_back_to_child_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/"도구"; package.mkdir()
            write(package/"__init__.hbc",compile_source("패키지값 = 1\n",str(package/"__init__.hy")))
            write(package/"수학.hbc",compile_source("정답 = 42\n",str(package/"수학.hy")))
            vm=VM([root]); code=compile_source("프롬 도구 인폴트 수학\n결과 = 수학.정답\n",str(root/"main.hy"))
            vm.run(code)
            self.assertEqual(vm.globals["결과"],42)

    def test_circular_import_exposes_already_initialized_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/"가.hbc",compile_source("값 = 20\n인폴트 나\n결과 = 값 + 나.값\n",str(root/"가.hy")))
            write(root/"나.hbc",compile_source("값 = 22\n인폴트 가\n확인 = 가.값\n",str(root/"나.hy")))
            vm=VM([root]); vm.run(compile_source("인폴트 가\n결과 = (가.결과, 가.나.확인)\n",str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],(42,20))

    def test_parenthesized_from_import_with_trailing_comma(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); write(root/"도구.hbc",compile_source("가 = 20\n나 = 22\n",str(root/"도구.hy")))
            source='프롬 도구 인폴트 (가 애즈 첫째, 나 애즈 둘째,)\n결과 = 첫째 + 둘째\n'
            vm=VM([root]); vm.run(compile_source(source,str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42)

    def test_global_assignment_and_delete(self):
        source='값 = 1\n데프 변경():\n    글로벌 값\n    값 = 42\n변경()\n결과 = 값\n자료 = {"삭제": 1, "유지": 2}\n델 자료["삭제"]\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],42); self.assertEqual(vm.globals["자료"],{"유지":2})

    def test_assert_can_be_caught(self):
        source='결과 = "실패"\n트라이:\n    어설트 2 + 2 == 5, "수학 오류"\n익셉트 어설션에러 애즈 오류:\n    결과 = 스트링(오류)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],"수학 오류")

    def test_assert_message_is_evaluated_only_on_failure(self):
        source='''
기록=[]
데프 메시지(값): 기록.append(값); 리턴 값
어설트 트루, 메시지("실행안됨")
트라이: 어설트 폴스, 메시지("실패")
익셉트 어설션에러 애즈 오류: 일반=스트링(오류)
데프 생성기():
    일드 1
    어설트 트루, 메시지("생성기실행안됨")
어싱크 데프 비동기():
    어설트 트루, 메시지("비동기실행안됨")
    리턴 42
흐름=생성기(); 넥스트(흐름)
트라이: 넥스트(흐름)
익셉트 스톱이터레이션: 패스
결과=(일반,기록,어싱크실행(비동기()))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("실패",["실패"],42))

    def test_compound_identity_membership(self):
        source='자료 = [1, 2]\n결과 = (3 낫 인 자료) 앤드 (자료 이즈 낫 넌)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertTrue(vm.globals["결과"])

    def test_global_declaration_applies_to_all_name_binding_statements(self):
        source='클래스 문맥:\n    데프 __enter__(셀프): 리턴 40\n    데프 __exit__(셀프, *인자): 리턴 폴스\n데프 변경():\n    글로벌 함수, 종류, 모듈, 값, 문맥값, 패턴값\n    데프 함수(): 리턴 1\n    클래스 종류: 패스\n    인폴트 math 애즈 모듈\n    (값 := 2)\n    위드 문맥() 애즈 문맥값: 패스\n    매치 42:\n        케이스 패턴값: 패스\n변경()\n결과=(함수(), 종류.__name__, 모듈.sqrt(9), 값, 문맥값, 패턴값)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(1,"종류",3,2,40,42))

    def test_global_exception_alias_is_deleted_after_handler(self):
        source='오류="이전"\n데프 실행():\n    글로벌 오류\n    트라이:\n        레이즈 밸류에러()\n    익셉트 밸류에러 애즈 오류:\n        패스\n실행()\n결과="오류" 인 globals()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertFalse(vm.globals["결과"])

    def test_returned_closure_sees_exception_alias_cell_cleared(self):
        source='데프 만들기():\n    트라이:\n        레이즈 밸류에러("값")\n    익셉트 밸류에러 애즈 오류:\n        데프 읽기(): 리턴 오류\n        리턴 읽기\n함수=만들기()\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaises(NameError): vm.globals["함수"]()
