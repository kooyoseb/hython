import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.vm import VM

class PatternExpressionTests(unittest.TestCase):
    def test_private_names_in_class_body_pattern_paths_are_mangled_but_keywords_are_not(self):
        source='''
class Point:
    def __init__(self): setattr(self,"__x",42)
class Namespace: pass
class Container:
    __Point=Point
    __Namespace=Namespace
    __Namespace.__token=42
    match Point():
        case __Point(): class_name=True
        case _: class_name=False
    match 42:
        case __Namespace.__token: value_path=True
        case _: value_path=False
    match Point():
        case Point(__x=item): keyword=item
        case _: keyword=None
result=(Container.class_name,Container.value_path,Container.keyword)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["result"],(True,True,42))

    def test_match_subject_expression_list_trailing_comma_and_star(self):
        source='''
첫째=1
나머지=[2,3]
match 첫째,*나머지,:
    case (1,2,3): 결과="일치"
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],"일치")

    def test_single_match_subject_trailing_comma_forms_tuple(self):
        vm=VM(); vm.run(compile_source('match 42,:\n case (값,): 결과=값\n'))
        self.assertEqual(vm.globals["결과"],42)
    def test_python314_literal_group_and_open_sequence_patterns(self):
        source='''
결과=[]
for 값 in (-1, 1+2j, (3,4)):
    match 값:
        case -1: 결과.append("음수")
        case 1+2j: 결과.append("복소수")
        case 첫째, 둘째: 결과.append((첫째,둘째))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["음수","복소수",(3,4)])

    def test_group_pattern_does_not_require_sequence_subject(self):
        vm=VM(); vm.run(compile_source('match 3:\n case (값): 결과=값\n'))
        self.assertEqual(vm.globals["결과"],3)

    def test_rejects_invalid_pattern_capture_forms_and_order(self):
        invalid=('match 값:\n case 1 as _: pass\n','match 값:\n case {"x": 항목, **_}: pass\n','match 값:\n case {**첫째, **둘째}: pass\n','match 값:\n case 대상(속성=항목, 위치): pass\n')
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_rejects_unreachable_irrefutable_cases(self):
        for source in ("매치 값:\n    케이스 대상: 패스\n    케이스 1: 패스\n","매치 값:\n    케이스 _: 패스\n    케이스 1: 패스\n"):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_chained_comparison_short_circuits_and_evaluates_middle_once(self):
        source='\n'.join([
            '기록 = []',
            '데프 값(이름, 숫자):',
            '    기록.append(이름)',
            '    리턴 숫자',
            '첫째 = 값("가", 1) < 값("나", 2) < 값("다", 3)',
            '두번째 = 값("라", 5) < 값("마", 4) < 값("바", 9)',
            '결과 = (첫째, 두번째, 기록)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,False,["가","나","다","라","마"]))

    def test_chained_comparison_preserves_comparison_result_objects(self):
        truth_calls=[]
        class Outcome:
            def __init__(self,name,truth): self.name=name; self.truth=truth
            def __bool__(self): truth_calls.append(self.name); return self.truth
        class Value:
            def __init__(self,result): self.result=result
            def __lt__(self,other): return self.result
        first=Outcome("첫째",True); last=Outcome("마지막",False); stopped=Outcome("중단",False)
        a,b,c=Value(first),Value(last),Value(None)
        source='데프 일반(): 리턴 가 < 나 < 다\n데프 생성기(): 일드 가 < 나 < 다\n어싱크 데프 비동기(): 리턴 가 < 나 < 다\n중단결과=라 < 마 < 바\n결과=(일반(),넥스트(생성기()),어싱크실행(비동기()),중단결과)\n'
        vm=VM(); vm.globals.update({"가":a,"나":b,"다":c,"라":Value(stopped),"마":Value(last),"바":Value(None)}); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(last,last,last,stopped))
        self.assertEqual(truth_calls,["중단","첫째","첫째","첫째"])

    def test_multidimensional_extended_slice(self):
        class Target:
            def __getitem__(self,index): return index
        vm=VM(); vm.globals["대상"]=Target(); vm.run(compile_source('결과 = 대상[1:4, ::-1, 7]\n'))
        result=vm.globals["결과"]
        self.assertEqual(result,(slice(1,4,None),slice(None,None,-1),7))

    def test_singleton_identity_and_collection_protocol_patterns(self):
        from collections import UserDict,UserList
        source='\n'.join([
            '결과 = []',
            '매치 1:',
            '    케이스 트루:',
            '        결과.append("잘못")',
            '    케이스 _:',
            '        결과.append("싱글턴")',
            '매치 순서:',
            '    케이스 [가, 나]:',
            '        결과.append(가 + 나)',
            '매치 사전값:',
            '    케이스 {"x": 값}:',
            '        결과.append(값)',
            ''
        ])
        vm=VM(); vm.globals.update({"순서":UserList([20,22]),"사전값":UserDict({"x":42})}); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["싱글턴",42,42])

    def test_value_and_as_patterns(self):
        class Color: 빨강=7
        source='\n'.join([
            '결과 = []',
            '매치 색상값:',
            '    케이스 색.빨강 애즈 전체:',
            '        결과.append(전체)',
            '매치 [42]:',
            '    케이스 [값] | (값,):',
            '        결과.append(값)',
            ''
        ])
        vm=VM(); vm.globals.update({"색":Color,"색상값":7}); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[7,42])

    def test_pattern_binding_validation(self):
        from hython.compiler import CompileError
        with self.assertRaises(CompileError): compile_source('매치 [1, 2]:\n    케이스 [값, 값]:\n        패스\n')
        with self.assertRaises(CompileError): compile_source('매치 [1]:\n    케이스 [값] | [_]:\n        패스\n')
    def run_source(self,source):
        vm=VM(); vm.run(loads(dumps(compile_source(source)))); return vm.globals

    def test_slices(self):
        values=self.run_source('자료 = [0, 1, 2, 3, 4, 5]\n결과 = (자료[1:5:2], 자료[:3], 자료[3:])\n')
        self.assertEqual(values["결과"],([1,3],[0,1,2],[3,4,5]))

    def test_subscription_trailing_comma_and_starred_items(self):
        source='''
class 기록기:
    def __getitem__(self,키): return 키
대상=기록기()
항목들=(3,4)
결과=(대상[1,],대상[*항목들],대상[1,*항목들,2])
'''
        values=self.run_source(source)
        self.assertEqual(values["결과"],((1,),(3,4),(1,3,4,2)))

    def test_empty_subscription_and_starred_slice_bound_are_rejected(self):
        for source in ('결과=대상[,]\n','결과=대상[*항목들:]\n','결과=대상[:*항목들]\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)

    def test_conditional_and_named_expression(self):
        values=self.run_source('결과 = (값 := 21) * 2 이프 트루 엘스 0\n저장 = 값\n')
        self.assertEqual((values["결과"],values["저장"]),(42,21))

    def test_match_literal_capture_wildcard_and_guard(self):
        source='값 = 42\n매치 값:\n    케이스 0:\n        결과 = "영"\n    케이스 잡음 이프 잡음 > 40:\n        결과 = f"큼:{잡음}"\n    케이스 _:\n        결과 = "기타"\n'
        self.assertEqual(self.run_source(source)["결과"],"큼:42")

    def test_sequence_star_and_or_patterns(self):
        source='값 = [1, 2, 3, 4]\n매치 값:\n    케이스 [0, *_]:\n        결과 = "영"\n    케이스 [1 | 9, *나머지]:\n        결과 = 나머지\n    케이스 _:\n        결과 = []\n'
        self.assertEqual(self.run_source(source)["결과"],[2,3,4])

    def test_star_sequence_pattern_does_not_require_slice_support(self):
        from collections.abc import Sequence
        class IntegerIndexed(Sequence):
            def __init__(self,values): self.values=values
            def __len__(self): return len(self.values)
            def __getitem__(self,index):
                if isinstance(index,slice): raise TypeError("슬라이스 미지원")
                return self.values[index]
        vm=VM(); vm.globals["자료"]=IntegerIndexed([1,2,3,4])
        vm.run(compile_source('match 자료:\n case [첫째,*가운데,마지막]: 결과=(첫째,가운데,마지막)\n'))
        self.assertEqual(vm.globals["결과"],(1,[2,3],4))

    def test_mapping_pattern_and_rest(self):
        source='값 = {"이름": "하이썬", "버전": 2, "상태": "개발"}\n매치 값:\n    케이스 {"이름": 이름, "버전": 2, **나머지}:\n        결과 = (이름, 나머지)\n    케이스 _:\n        결과 = 넌\n'
        self.assertEqual(self.run_source(source)["결과"],("하이썬",{"상태":"개발"}))

    def test_mapping_pattern_supports_dotted_value_and_signed_complex_keys(self):
        class Keys: 이름="name"
        source='매치 자료:\n    케이스 {키.이름: 이름, -1: 음수, 1+2j: 복소수}:\n        결과=(이름, 음수, 복소수)\n    케이스 _:\n        결과=넌\n'
        vm=VM(); vm.globals.update({"키":Keys,"자료":{"name":40,-1:1,1+2j:1}}); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(40,1,1))

    def test_mapping_pattern_dynamic_duplicate_key_raises_value_error(self):
        class Keys: 가="x"; 나="x"
        source='매치 자료:\n    케이스 {키.가: 첫째, 키.나: 둘째}:\n        패스\n    케이스 _:\n        패스\n'
        vm=VM(); vm.globals.update({"키":Keys,"자료":{"x":1,"y":2}})
        with self.assertRaises(ValueError): vm.run(compile_source(source))

    def test_mapping_pattern_uses_get_without_triggering_missing(self):
        class MissingDict(dict):
            def __missing__(self,key): self[key]=42; return 42
        subject=MissingDict()
        vm=VM(); vm.globals["자료"]=subject
        vm.run(compile_source('매치 자료:\n    케이스 {"없음": 값}: 결과=트루\n    케이스 _: 결과=폴스\n'))
        self.assertFalse(vm.globals["결과"]); self.assertEqual(subject,{})

    def test_class_pattern_keywords(self):
        source='클래스 점:\n    데프 __init__(셀프, 엑스, 와이):\n        셀프.엑스 = 엑스\n        셀프.와이 = 와이\n값 = 점(20, 22)\n매치 값:\n    케이스 점(엑스=가, 와이=나):\n        결과 = 가 + 나\n    케이스 _:\n        결과 = 0\n'
        self.assertEqual(self.run_source(source)["결과"],42)

    def test_dotted_class_pattern(self):
        from types import SimpleNamespace
        class Point:
            __match_args__=("x","y")
            def __init__(self,x,y): self.x=x; self.y=y
        vm=VM(); vm.globals.update({"모듈":SimpleNamespace(점=Point),"값":Point(20,22)})
        vm.run(compile_source('매치 값:\n    케이스 모듈.점(가, 나): 결과=가+나\n    케이스 _: 결과=0\n'))
        self.assertEqual(vm.globals["결과"],42)

    def test_class_pattern_runtime_shape_errors_match_python(self):
        class Point:
            __match_args__=("x",)
            def __init__(self): self.x=1
        cases=[
            ('매치 값:\n    케이스 대상(): 패스\n',{"값":object(),"대상":42}),
            ('매치 값:\n    케이스 점(가, 나): 패스\n',{"값":Point(),"점":Point}),
            ('매치 값:\n    케이스 점(가, x=나): 패스\n',{"값":Point(),"점":Point}),
        ]
        for source,values in cases:
            vm=VM(); vm.globals.update(values)
            with self.subTest(source=source),self.assertRaises(TypeError): vm.run(compile_source(source))

    def test_builtin_class_patterns_match_the_subject_itself(self):
        source='''
결과=[]
for 값 in (42, "한글", [1,2]):
    match 값:
        case int(전체): 결과.append(("정수",전체))
        case str(전체): 결과.append(("문자",전체))
        case list(전체): 결과.append(("목록",전체))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[('정수',42),('문자','한글'),('목록',[1,2])])

    def test_class_pattern_only_validates_used_match_args(self):
        class Target:
            __match_args__=("value",42)
            value=7
        vm=VM(); vm.globals.update({"값":Target(),"대상":Target})
        vm.run(compile_source('match 값:\n case 대상(첫째): 결과=첫째\n'))
        self.assertEqual(vm.globals["결과"],7)
        with self.assertRaises(TypeError):
            vm.run(compile_source('match 값:\n case 대상(첫째,둘째): pass\n'))

    def test_keyword_only_class_pattern_does_not_read_match_args(self):
        reads=[]
        class Meta(type):
            @property
            def __match_args__(cls): reads.append(cls); raise RuntimeError("읽으면 안 됨")
        class Target(metaclass=Meta): value=42
        vm=VM(); vm.globals.update({"값":Target(),"대상":Target})
        vm.run(compile_source('매치 값:\n    케이스 대상(value=결과): 패스\n'))
        self.assertEqual(vm.globals["결과"],42); self.assertEqual(reads,[])

    def test_duplicate_positional_match_args_raise_type_error(self):
        class Target:
            __match_args__=("value","value")
            value=42
        vm=VM(); vm.globals.update({"값":Target(),"대상":Target})
        with self.assertRaisesRegex(TypeError,"value"):
            vm.run(compile_source('매치 값:\n    케이스 대상(첫째, 둘째): 패스\n'))
