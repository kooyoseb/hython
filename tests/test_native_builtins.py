import unittest
from hython.compiler import compile_source
from hython.vm import VM
from hython.vocabulary import BUILTINS, KEYWORDS

class NativeBuiltinsTests(unittest.TestCase):
    def test_collection_and_numeric_builtins(self):
        source='자료 = [3, 1, 2]\n결과 = (썸(자료), 민(자료), 맥스(자료), 소티드(자료), 앱스(-42), 애니([폴스, 트루]), 올([트루, 트루]))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(6,1,3,[1,2,3],42,True,True))

    def test_runtime_exposes_every_public_python_builtin(self):
        import builtins
        vm=VM()
        expected={name for name in dir(builtins) if not name.startswith("_")}
        self.assertTrue(expected <= vm.globals.keys())
        self.assertTrue(expected <= (BUILTINS.keys() | KEYWORDS.keys()))

    def test_newly_generated_builtin_spellings_compile_natively(self):
        names={name:BUILTINS[name] for name in ("bin","chr","divmod","bytes","frozenset","callable")}
        source=(f'결과 = ({names["bin"]}(10), {names["chr"]}(65), {names["divmod"]}(17, 5), '
                f'{names["bytes"]}([65, 66]), {names["frozenset"]}([1, 1, 2]), {names["callable"]}({names["bin"]}))\n')
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("0b1010","A",(3,2),b"AB",frozenset({1,2}),True))

    def test_canonical_spoken_builtin_names_are_human_pronounceable(self):
        self.assertEqual(BUILTINS["hash"],"해시")
        self.assertEqual(BUILTINS["compile"],"컴파일")
        self.assertEqual(BUILTINS["RuntimeError"],"런타임에러")
        source='자료=[1,2,3]\n결과=(해시("값"), 이터(자료).__next__(), 헥스(255), 포맷(42, "04d"), 콜러블(컴파일), 런타임에러.__name__)\n'
        vm=VM(); vm.run(compile_source(source))
        result=vm.globals["결과"]
        self.assertEqual(result[1:],(1,"0xff","0042",True,"RuntimeError"))

    def test_spoken_exception_names_work_in_raise_and_except(self):
        source='결과=폴스\n트라이:\n    레이즈 런타임에러("실패")\n익셉트 런타임에러 애즈 오류:\n    결과=(스트링(오류), 이즈인스턴스(오류, 베이스익셉션))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("실패",True))

    def test_globals_locals_vars_and_dir_use_hbc_scope(self):
        source='전역값=20\n데프 함수(매개변수):\n    지역값=22\n    현재=locals()\n    리턴 (globals()["전역값"], 현재["매개변수"], vars()["지역값"], "지역값" 인 dir(), "전역값" 인 현재, "$closure" 인 현재)\n결과=함수(21)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(20,21,22,True,False,False))

    def test_eval_and_exec_use_current_hbc_scope(self):
        source='값=40\n모듈평가=이밸("값+2")\n이그젝("새값=값+1")\n데프 함수(매개변수):\n    지역값=2\n    이그젝("실행값=매개변수+지역값")\n    리턴 (이밸("매개변수+지역값"), 로컬스()["실행값"])\n결과=(모듈평가, 새값, 함수(40))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,41,(42,42)))

    def test_eval_explicit_namespaces_keep_native_python_contract(self):
        source='공간={"값": 40}\n결과=이밸("값+2", 공간)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)
