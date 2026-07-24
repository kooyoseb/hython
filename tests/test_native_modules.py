import tempfile
import unittest
from pathlib import Path
from hython.bytecode import write
from hython.compiler import compile_source
from hython.vm import VM

class NativeModuleTests(unittest.TestCase):
    def test_imports_python_standard_library_module(self):
        source='인폴트 math 애즈 수학\n결과 = 수학.sqrt(1764)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)

    def test_from_imports_python_standard_library_name(self):
        source='프롬 math 인폴트 prod 애즈 곱\n결과 = 곱([2, 3, 7])\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)

    def test_missing_python_from_import_raises_import_error(self):
        with self.assertRaises(ImportError):
            VM().run(compile_source('프롬 math 인폴트 없는이름\n'))

    def test_local_hbc_module_precedes_python_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/"json.hbc",compile_source('정답 = 42\n',str(root/"json.hy")))
            vm=VM([root]); vm.run(compile_source('인폴트 json\n결과 = json.정답\n',str(root/"main.hy")))
            self.assertEqual(vm.globals["결과"],42)

    def test_imports_verified_hbc_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/"계산.hbc",compile_source("데프 두배(값):\n    리턴 값 * 2\n",str(root/"계산.hy")))
            main=compile_source("인폴트 계산\n결과 = 계산.두배(21)\n",str(root/"main.hy"))
            vm=VM([root]); vm.run(main)
            self.assertEqual(vm.globals["결과"],42)

    def test_missing_native_module_is_clear(self):
        with self.assertRaisesRegex(ModuleNotFoundError,"찾을 수 없습니다"):
            VM().run(compile_source("인폴트 없음\n"))

    def test_imported_module_lazy_annotations_keep_module_owner(self):
        import annotationlib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source='기록=[]\n데프 표식(): 기록.append("평가"); 리턴 인트\n값: 나중\n다른값: 표식()\n전방: 없는타입\n클래스 나중: 패스\n'
            write(root/"주석모듈.hbc",compile_source(source,str(root/"주석모듈.hy")))
            vm=VM([root]); vm.run(compile_source('인폴트 주석모듈\n',str(root/"main.hy")))
            module=vm.globals["주석모듈"]
            self.assertEqual(module.기록,[])
            strings=annotationlib.get_annotations(module,format=annotationlib.Format.STRING)
            self.assertEqual(strings,{"값":"나중","다른값":"표식()","전방":"없는타입"}); self.assertEqual(module.기록,["평가"])
            refs=annotationlib.get_annotations(module,format=annotationlib.Format.FORWARDREF)
            self.assertIs(refs["전방"].__owner__,module); self.assertEqual(module.기록,["평가","평가","평가"])
            module.없는타입=str
            values=annotationlib.get_annotations(module,format=annotationlib.Format.VALUE)
            self.assertIs(values["값"],module.나중); self.assertIs(values["다른값"],int); self.assertIs(values["전방"],str)
            self.assertEqual(module.기록,["평가","평가","평가","평가"]); self.assertIs(module.__annotate__(),module.__annotations__)

    def test_imported_module_annotation_attributes_follow_module_type_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/"주석쓰기.hbc",compile_source('값: 없는타입\n',str(root/"주석쓰기.hy")))
            vm=VM([root]); vm.run(compile_source('인폴트 주석쓰기\n',str(root/"main.hy")))
            module=vm.globals["주석쓰기"]
            module.__annotations__={"수동":int}
            self.assertEqual(module.__annotations__,{"수동":int}); self.assertIsNone(module.__annotate__)
            module.__annotate__=lambda format=1:{"재생성":str}
            self.assertIsNone(vars(module).get("__annotations__")); self.assertEqual(module.__annotations__,{"재생성":str})
            with self.assertRaises(TypeError): module.__annotate__=42
