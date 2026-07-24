import inspect
import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.vm import VM

class AdvancedFunctionTests(unittest.TestCase):
    def test_definition_and_lambda_parameter_trailing_commas(self):
        source='''
def 일반(값,): return 값
def 위치(값,/,): return 값
def 가변(*값들,): return 값들
def 전용(*,값,): return 값
람다들=(lambda 값,:값, lambda 값,/:값, lambda *값들,:값들, lambda *,값,:값)
결과=(일반(1),위치(2),가변(3,4),전용(값=5),람다들[0](6),람다들[1](7),람다들[2](8,9),람다들[3](값=10))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(1,2,(3,4),5,6,7,(8,9),10))

    def test_lambda_parameter_validation_matches_function_definitions(self):
        for source in ('결과=lambda 값,값:값\n','결과=lambda 값,*값:값\n','결과=lambda *:1\n','결과=lambda /:1\n','결과=lambda 값,/,값:값\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_function_defaults_metadata_is_writable_and_changes_calls(self):
        source='데프 함수(가, 나=2, *, 키=3): 리턴 (가,나,키)\n'
        vm=VM(); vm.run(compile_source(source)); function=vm.globals["함수"]
        self.assertEqual((function.__defaults__,function.__kwdefaults__),((2,),{"키":3}))
        function.__defaults__=(10,20,30); function.__kwdefaults__={"키":40,"무시":99}
        self.assertEqual((function.__defaults__,function.__kwdefaults__),((10,20,30),{"키":40,"무시":99}))
        self.assertEqual(function(),(20,30,40))
        self.assertEqual(str(inspect.signature(function)),"(가=20, 나=30, *, 키=40)")

    def test_clearing_function_defaults_makes_parameters_required(self):
        vm=VM(); vm.run(compile_source('데프 함수(값=1, *, 키=2): 리턴 값+키\n')); function=vm.globals["함수"]
        function.__defaults__=None; function.__kwdefaults__=None
        self.assertIsNone(function.__defaults__); self.assertIsNone(function.__kwdefaults__)
        with self.assertRaises(TypeError): function()
        self.assertEqual(function(20,키=22),42)

    def test_function_defaults_setters_validate_container_types(self):
        vm=VM(); vm.run(compile_source('데프 함수(값=1, *, 키=2): 패스\n')); function=vm.globals["함수"]
        with self.assertRaises(TypeError): function.__defaults__=[1]
        with self.assertRaises(TypeError): function.__kwdefaults__=(2,)

    def test_function_identity_metadata_is_writable(self):
        vm=VM(); vm.run(compile_source('데프 함수(): 패스\n')); function=vm.globals["함수"]
        function.__name__="새이름"; function.__qualname__="공간.새이름"; function.__module__=42; function.__doc__={"문서":True}
        self.assertEqual((function.__name__,function.__qualname__,function.__module__,function.__doc__),("새이름","공간.새이름",42,{"문서":True}))
        with self.assertRaises(TypeError): function.__name__=1
        with self.assertRaises(TypeError): function.__qualname__=None

    def test_function_annotations_are_writable_and_update_signature(self):
        vm=VM(); vm.run(compile_source('데프 함수(값: 인트) -> 스트링: 패스\n')); function=vm.globals["함수"]
        function.__annotations__={"값":float,"return":bytes}
        self.assertIsNone(function.__annotate__)
        self.assertEqual(function.__annotations__,{"값":float,"return":bytes})
        self.assertEqual(str(inspect.signature(function)),"(값: float) -> bytes")
        function.__annotations__=None; self.assertEqual(function.__annotations__,{})
        with self.assertRaises(TypeError): function.__annotations__=[]

    def test_custom_annotate_function_is_lazy_and_cached(self):
        vm=VM(); vm.run(compile_source('데프 함수(값): 패스\n')); function=vm.globals["함수"]; calls=[]
        def annotate(format): calls.append(format); return {"값":str}
        function.__annotate__=annotate
        self.assertIs(function.__annotate__,annotate); self.assertEqual(calls,[])
        self.assertEqual(function.__annotations__,{"값":str}); self.assertEqual(function.__annotations__,{"값":str})
        self.assertEqual(calls,[__import__("annotationlib").Format.VALUE])
        with self.assertRaises(TypeError): function.__annotate__=42

    def test_function_type_parameters_metadata_is_writable(self):
        vm=VM(); vm.run(compile_source('데프 함수[T](): 패스\n')); function=vm.globals["함수"]
        original=function.__type_params__; self.assertEqual(len(original),1)
        function.__type_params__=(int,str); self.assertEqual(function.__type_params__,(int,str))
        with self.assertRaises(TypeError): function.__type_params__=[int]

    def test_inspect_signature_code_globals_and_bound_method(self):
        source='데프 함수(가: 인트, /, 나: 스트링="x", *값들: 튜플, 키: 플로트=1.5, **옵션: 딕트) -> 불: 패스\n클래스 대상:\n    데프 메서드(셀프, 값: 인트=1): 패스\n인스턴스=대상()\n'
        vm=VM(); vm.run(compile_source(source)); function=vm.globals["함수"]
        self.assertEqual(str(inspect.signature(function)),"(가: int, /, 나: str = 'x', *값들: tuple, 키: float = 1.5, **옵션: dict) -> bool")
        self.assertEqual(function.__code__.name,"함수"); self.assertIs(function.__globals__,vm.globals)
        self.assertEqual(str(inspect.signature(vm.globals["대상"].메서드)),"(셀프, 값: int = 1)")
        self.assertEqual(str(inspect.signature(vm.globals["인스턴스"].메서드)),"(값: int = 1)")
    def test_generator_argument_and_trailing_call_comma(self):
        source='데프 더하기(가, 나):\n    리턴 가 + 나\n결과 = (썸(값 * 2 포 값 인 레인지(4)), 더하기(20, 22,))\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(12,42))
    def test_star_unpack_after_keyword_unpack_is_rejected(self):
        with self.assertRaises(SyntaxError): compile_source('결과=함수(**키워드, *위치값)\n')
    def test_star_unpack_after_regular_keyword_remains_valid(self):
        vm=VM(); vm.run(compile_source('def 함수(*위치값, **키워드): return 위치값,키워드\n결과=함수(이름=1, *[2,3])\n'))
        self.assertEqual(vm.globals["결과"],((2,3),{"이름":1}))
    def run_source(self,source):
        vm=VM(); vm.run(loads(dumps(compile_source(source)))); return vm.globals

    def test_defaults_and_keyword_arguments(self):
        source='데프 소개(이름, 인사="안녕", 문장부호="!"):\n    리턴 f"{인사}, {이름}{문장부호}"\n결과 = 소개(문장부호="?", 이름="하이썬")\n'
        self.assertEqual(self.run_source(source)["결과"],"안녕, 하이썬?")

    def test_default_is_evaluated_once_at_definition(self):
        source='기본값 = [1]\n데프 읽기(자료=기본값):\n    리턴 자료[0]\n기본값[0] = 42\n결과 = 읽기()\n'
        self.assertEqual(self.run_source(source)["결과"],42)

    def test_duplicate_argument_is_rejected(self):
        source='데프 함수(값):\n    리턴 값\n결과 = 함수(1, 값=2)\n'
        with self.assertRaisesRegex(TypeError,"중복"):
            self.run_source(source)

    def test_missing_argument_is_rejected(self):
        source='데프 함수(필수):\n    리턴 필수\n결과 = 함수()\n'
        with self.assertRaisesRegex(TypeError,"필수 인자 누락"):
            self.run_source(source)

    def test_varargs_kwargs_and_keyword_only(self):
        source='데프 모으기(첫째, *나머지, 이름="기본", **추가):\n    리턴 (첫째, 나머지, 이름, 추가)\n위치 = [2, 3]\n키워드 = {"이름": "하이썬", "버전": 2}\n결과 = 모으기(1, *위치, **키워드)\n'
        self.assertEqual(self.run_source(source)["결과"],(1,(2,3),"하이썬",{"버전":2}))

    def test_bare_star_keyword_only(self):
        source='데프 함수(값, *, 배수=2):\n    리턴 값 * 배수\n결과 = 함수(4, 배수=3)\n'
        self.assertEqual(self.run_source(source)["결과"],12)

    def test_positional_only_parameter(self):
        source='데프 함수(위치, /, 일반):\n    리턴 위치 + 일반\n결과 = 함수(20, 일반=22)\n'
        self.assertEqual(self.run_source(source)["결과"],42)
        with self.assertRaisesRegex(TypeError,"위치 전용"):
            self.run_source('데프 함수(위치, /):\n    리턴 위치\n결과 = 함수(위치=1)\n')

    def test_positional_only_name_may_also_enter_kwargs(self):
        source='데프 함수(값, /, **옵션):\n    리턴 (값, 옵션["값"])\n결과 = 함수(1, 값=2)\n'
        self.assertEqual(self.run_source(source)["결과"],(1,2))

    def test_call_shape_errors_are_type_errors(self):
        with self.assertRaises(TypeError):
            self.run_source('데프 함수(값):\n    패스\n함수(1, 2)\n')
        with self.assertRaises(TypeError):
            self.run_source('데프 함수():\n    패스\n함수(없는값=1)\n')

    def test_keyword_unpack_requires_mapping_with_string_keys(self):
        function='데프 함수(**옵션):\n    리턴 옵션\n'
        with self.assertRaises(TypeError):
            self.run_source(function+'결과 = 함수(**{1: 2})\n')
        with self.assertRaises(TypeError):
            self.run_source(function+'결과 = 함수(**42)\n')

    def test_non_string_keyword_error_is_deferred_until_all_arguments_are_evaluated(self):
        class MappingWithBadKey:
            def __init__(self,log): self.log=log
            def keys(self): self.log.append("키"); return [1,"정상"]
            def __getitem__(self,key): self.log.append(("값",key)); return key
        log=[]
        vm=VM(); vm.globals.update({"매핑":MappingWithBadKey(log),"기록":log})
        source='데프 나중(): 기록.append("나중"); 리턴 3\n데프 함수(**옵션): 패스\n함수(**매핑, 뒤=나중())\n'
        with self.assertRaisesRegex(TypeError,"keywords must be strings"): vm.run(compile_source(source))
        self.assertEqual(log,["키",("값",1),("값","정상"),"나중"])

    def test_keyword_unpack_accepts_mapping_protocol(self):
        class DuckMapping:
            def keys(self): return ["값"]
            def __getitem__(self,key): return 42
        vm=VM(); vm.globals["매핑"]=DuckMapping()
        vm.run(compile_source('데프 함수(**옵션):\n    리턴 옵션["값"]\n결과 = 함수(**매핑)\n'))
        self.assertEqual(vm.globals["결과"],42)

    def test_call_unpacking_fails_before_later_argument_evaluation(self):
        source='기록=[]\n데프 표시(이름,값): 기록.append(이름); 리턴 값\n데프 함수(*값,**키워드): 패스\n트라이: 함수(*표시("별",42), 표시("후",1))\n익셉트 타입에러: 패스\n첫째=기록[:]\n기록=[]\n트라이: 함수(**표시("별별",42), 나중=표시("후",1))\n익셉트 타입에러: 패스\n결과=(첫째,기록)\n'
        self.assertEqual(self.run_source(source)["결과"],(["별"],["별별"]))

    def test_star_unpack_preserves_iterator_type_error_for_calls_and_classes(self):
        source='''
클래스 나쁨:
    데프 __iter__(셀프): 리턴 셀프
    데프 __next__(셀프): 레이즈 타입에러("boom")
데프 함수(*값): 패스
오류들=[]
트라이: 함수(*나쁨())
익셉트 타입에러 애즈 오류: 오류들.append(스트링(오류))
트라이:
    클래스 대상(*나쁨()): 패스
익셉트 타입에러 애즈 오류: 오류들.append(스트링(오류))
결과=오류들
'''
        self.assertEqual(self.run_source(source)["결과"],["boom","boom"])

    def test_duplicate_keyword_unpack_fails_before_later_argument(self):
        source='기록=[]\n데프 표시(): 기록.append("후"); 리턴 3\n데프 함수(**키워드): 패스\n트라이: 함수(값=1, **{"값":2}, 나중=표시())\n익셉트 타입에러: 패스\n결과=기록\n'
        self.assertEqual(self.run_source(source)["결과"],[])
