import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.vm import VM

class WithLambdaTests(unittest.TestCase):
    def test_python314_empty_parenthesized_with_manager_list(self):
        vm=VM(); vm.run(compile_source('결과=[]\nwith ():\n    결과.append(42)\n'))
        self.assertEqual(vm.globals["결과"],[42])

    def test_named_expression_in_parenthesized_with_manager_list(self):
        source='''
class 문맥:
    def __enter__(self): return 42
    def __exit__(self,*정보): pass
with (저장 := 문맥()):
    결과=isinstance(저장,문맥)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertIs(vm.globals["결과"],True)
    def test_with_assignment_target_destructuring_attribute_and_subscript(self):
        source='클래스 문맥:\n    데프 __init__(셀프, 값): 셀프.값 = 값\n    데프 __enter__(셀프): 리턴 셀프.값\n    데프 __exit__(셀프, *인자): 리턴 폴스\n클래스 상자: 패스\n대상 = 상자()\n자료 = [0]\n위드 문맥((20, 22)) 애즈 (가, 나), 문맥(42) 애즈 대상.값, 문맥(99) 애즈 자료[0]:\n    결과 = (가 + 나, 대상.값, 자료[0])\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,42,99))
    def test_lambda_full_parameter_binding(self):
        source='\n'.join([
            '함수 = 람다 가, /, 나=2, *, 다=3, **추가: 가 + 나 + 다 + 추가.get("라", 0)',
            '모음 = 람다 *값들: 썸(값들)',
            '결과 = (함수(1, 다=4, 라=5), 모음(1, 2, 3))',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(12,6))

    def test_lambda_defaults_live_closure_and_python_metadata(self):
        source='''
데프 바깥():
    값 = 20
    함수 = 람다 가=값, /, *, 나=3: (가, 나, 값)
    값 = 30
    리턴 함수
함수 = 바깥()
결과 = (함수(), 함수.__name__, 함수.__qualname__, 스트링(함수.__signature__), 함수.__defaults__, 함수.__kwdefaults__)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((20,3,30),"<lambda>","바깥.<locals>.<lambda>","(가=20, /, *, 나=3)",(20,),{"나":3}))

    def test_lambda_with_yield_expression_is_generator_function(self):
        source='함수 = 람다 값: (일드 값)\n생성기 = 함수(42)\n첫째 = 넥스트(생성기)\n트라이:\n    생성기.send(99)\n익셉트 스톱이터레이션 애즈 오류:\n    반환값 = 오류.value\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual((vm.globals["첫째"],vm.globals["반환값"]),(42,99))

    def test_lambda_with_yield_from_is_generator_function(self):
        source='함수 = 람다 값들: (일드 프롬 값들)\n결과 = 리스트(함수([1, 2, 3]))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[1,2,3])

    def test_parenthesized_multiple_context_managers(self):
        events=[]
        class Manager:
            def __init__(self,name): self.name=name
            def __enter__(self): events.append("enter-"+self.name); return self.name
            def __exit__(self,*exc): events.append("exit-"+self.name)
        source='기록 = []\n데프 실행(가, 나):\n    위드 (가 애즈 첫째, 나 애즈 둘째):\n        기록.append(첫째 + 둘째)\n실행(가, 나)\n'
        vm=VM(); vm.globals.update({"가":Manager("a"),"나":Manager("b")}); vm.run(compile_source(source))
        self.assertEqual(vm.globals["기록"],["ab"]); self.assertEqual(events,["enter-a","enter-b","exit-b","exit-a"])
    def run_source(self,source):
        vm=VM(); vm.run(loads(dumps(compile_source(source)))); return vm.globals

    def test_lambda_closure_and_keyword_call(self):
        source='배수 = 3\n함수 = 람다 값: 값 * 배수\n결과 = 함수(값=14)\n'
        self.assertEqual(self.run_source(source)["결과"],42)

    def test_context_manager_normal_order(self):
        source='기록 = []\n클래스 문맥:\n    데프 __init__(셀프, 이름):\n        셀프.이름 = 이름\n    데프 __enter__(셀프):\n        기록.append("입장" + 셀프.이름)\n        리턴 셀프.이름\n    데프 __exit__(셀프, 형식, 값, 추적):\n        기록.append("퇴장" + 셀프.이름)\n        리턴 폴스\n위드 문맥("A") 애즈 가, 문맥("B") 애즈 나:\n    기록.append(가 + 나)\n결과 = 기록\n'
        self.assertEqual(self.run_source(source)["결과"],["입장A","입장B","AB","퇴장B","퇴장A"])

    def test_context_manager_can_suppress_exception(self):
        source='클래스 억제:\n    데프 __enter__(셀프):\n        리턴 셀프\n    데프 __exit__(셀프, 형식, 값, 추적):\n        리턴 트루\n결과 = "전"\n위드 억제():\n    레이즈 밸류에러("숨김")\n결과 = "후"\n'
        self.assertEqual(self.run_source(source)["결과"],"후")

    def test_return_inside_with_calls_exit_then_returns(self):
        source='기록 = []\n클래스 문맥:\n    데프 __enter__(셀프):\n        기록.append("입장")\n        리턴 셀프\n    데프 __exit__(셀프, 형식, 값, 추적):\n        기록.append("퇴장")\n        리턴 폴스\n데프 함수():\n    위드 문맥():\n        리턴 42\n결과 = 함수()\n'
        values=self.run_source(source); self.assertEqual(values["결과"],42); self.assertEqual(values["기록"],["입장","퇴장"])

    def test_failed_enter_unwinds_only_successfully_entered_managers(self):
        events=[]
        class Manager:
            def __init__(self,name,fail=False): self.name=name; self.fail=fail
            def __enter__(self):
                events.append("enter-"+self.name)
                if self.fail: raise ValueError("진입 실패")
                return self
            def __exit__(self,kind,error,trace): events.append(("exit-"+self.name,kind)); return False
        vm=VM(); vm.globals.update({"바깥":Manager("outer"),"안쪽":Manager("inner",True)})
        with self.assertRaises(ValueError): vm.run(compile_source('위드 바깥, 안쪽:\n    패스\n'))
        self.assertEqual(events,["enter-outer","enter-inner",("exit-outer",ValueError)])

    def test_outer_exit_receives_and_can_suppress_inner_exit_failure(self):
        events=[]
        class Outer:
            def __enter__(self): return self
            def __exit__(self,kind,error,trace): events.append(kind); return kind is TypeError
        class Inner:
            def __enter__(self): return self
            def __exit__(self,*args): raise TypeError("퇴장 실패")
        vm=VM(); vm.globals.update({"바깥":Outer(),"안쪽":Inner()})
        vm.run(compile_source('결과=0\n위드 바깥, 안쪽:\n    결과=1\n결과=42\n'))
        self.assertEqual(vm.globals["결과"],42); self.assertEqual(events,[TypeError])

    def test_exit_reraising_same_exception_does_not_create_self_context(self):
        error=ValueError("동일")
        class Manager:
            def __enter__(self): return self
            def __exit__(self,*exc): raise error
        vm=VM(); vm.globals.update({"문맥":Manager(),"오류":error})
        with self.assertRaises(ValueError) as raised: vm.run(compile_source('위드 문맥:\n    레이즈 오류\n'))
        self.assertIs(raised.exception,error); self.assertIsNone(error.__context__)

    def test_return_is_not_reported_as_exception_to_exit(self):
        seen=[]
        class Manager:
            def __enter__(self): return self
            def __exit__(self,*exc): seen.append(exc); return False
        vm=VM(); vm.globals["문맥"]=Manager()
        vm.run(compile_source('데프 함수():\n    위드 문맥:\n        리턴 42\n결과=함수()\n'))
        self.assertEqual(vm.globals["결과"],42); self.assertEqual(seen,[(None,None,None)])

    def test_exit_failure_overrides_return_without_internal_exception_context(self):
        class Manager:
            def __enter__(self): return self
            def __exit__(self,*exc): raise ValueError("퇴장 실패")
        vm=VM(); vm.globals["문맥"]=Manager(); vm.run(compile_source('데프 함수():\n    위드 문맥:\n        리턴 42\n'))
        with self.assertRaises(ValueError) as raised: vm.globals["함수"]()
        self.assertIsNone(raised.exception.__context__)

    def test_with_special_methods_are_looked_up_on_type(self):
        events=[]
        class Manager:
            def __getattribute__(self,name):
                if name in {"__enter__","__exit__"}: raise AssertionError("instance lookup")
                return object.__getattribute__(self,name)
            def __enter__(self): events.append("type-enter"); return 42
            def __exit__(self,*exc): events.append("type-exit")
        manager=Manager()
        manager.__dict__["__enter__"]=lambda: events.append("instance-enter")
        manager.__dict__["__exit__"]=lambda *exc: events.append("instance-exit")
        vm=VM(); vm.globals["문맥"]=manager
        vm.run(compile_source('위드 문맥 애즈 값:\n    결과=값\n'))
        self.assertEqual(vm.globals["결과"],42)
        self.assertEqual(events,["type-enter","type-exit"])

    def test_missing_exit_is_reported_before_enter_runs(self):
        events=[]
        class Manager:
            def __enter__(self): events.append("enter")
        vm=VM(); vm.globals["문맥"]=Manager()
        with self.assertRaises(TypeError): vm.run(compile_source('위드 문맥:\n    패스\n'))
        self.assertEqual(events,[])

    def test_loop_control_inside_with_unwinds_normally(self):
        source='''
기록=[]
클래스 문맥:
    데프 __enter__(셀프): 리턴 셀프
    데프 __exit__(셀프, *정보): 기록.append(정보); 리턴 폴스
데프 함수():
    포 값 인 [1, 2]:
        위드 문맥():
            이프 값 == 1: 컨티뉴
            브레이크
    리턴 42
결과=함수()
'''
        values=self.run_source(source)
        self.assertEqual(values["결과"],42)
        self.assertEqual(values["기록"],[(None,None,None),(None,None,None)])
