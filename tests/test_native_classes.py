import unittest
from hython.compiler import compile_source
from hython.vm import VM

class NativeClassTests(unittest.TestCase):
    def test_class_header_trailing_comma_and_source_evaluation_order(self):
        source='''
기록=[]
def 표시(이름,값):
    기록.append(이름)
    return 값
class 대상(metaclass=표시("메타",type), *표시("기반",()), **표시("키워드",{}),):
    pass
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["기록"],["메타","기반","키워드"])

    def test_class_header_rejects_invalid_argument_order(self):
        for source in ('class 대상(metaclass=type, object): pass\n','class 대상(**키워드, *기반): pass\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_nested_definitions_have_python_qualified_names(self):
        source='데프 바깥():\n    데프 안쪽(): 패스\n    클래스 지역:\n        데프 메서드(셀프): 패스\n    리턴 (안쪽,지역)\n안쪽,지역=바깥()\n클래스 외부:\n    클래스 내부:\n        데프 메서드(셀프): 패스\n결과=(바깥.__qualname__,안쪽.__qualname__,지역.__qualname__,지역.메서드.__qualname__,외부.내부.__qualname__,외부.내부.메서드.__qualname__)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("바깥","바깥.<locals>.안쪽","바깥.<locals>.지역","바깥.<locals>.지역.메서드","외부.내부","외부.내부.메서드"))

    def test_qualname_prefix_is_hidden_from_locals(self):
        source='데프 바깥():\n    데프 안쪽(): 리턴 "$qualname_prefix" 인 로컬스()\n    리턴 안쪽()\n결과=바깥()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertFalse(vm.globals["결과"])

    def test_decorator_returned_external_function_keeps_original_qualname(self):
        source='데프 대체(셀프): 리턴 42\n데프 장식(함수): 리턴 대체\n클래스 종류:\n    @장식\n    데프 원본(셀프): 리턴 0\n결과=(종류.원본.__qualname__,종류().원본())\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("대체",42))

    def test_zero_argument_super_is_runtime_error_outside_method(self):
        for source in ('결과=수퍼()\n','데프 함수(): 리턴 수퍼()\n결과=함수()\n'):
            with self.subTest(source=source):
                code=compile_source(source)
                with self.assertRaisesRegex(RuntimeError,r"super\(\): no arguments"): VM().run(code)

    def test_zero_argument_super_reports_missing_class_cell_at_runtime(self):
        vm=VM(); vm.run(compile_source('데프 함수(값): 리턴 수퍼()\n'))
        with self.assertRaisesRegex(RuntimeError,"__class__ cell not found"): vm.globals["함수"](object())

    def test_zero_argument_super_reports_deleted_first_argument(self):
        source='클래스 기반: 패스\n클래스 자식(기반):\n    데프 함수(셀프):\n        델 셀프\n        리턴 수퍼()\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaisesRegex(RuntimeError,r"arg\[0\] deleted"): vm.globals["자식"]().함수()

    def test_zero_argument_super_runtime_validation_in_suspended_functions(self):
        import asyncio
        source='데프 생성(): 일드 수퍼()\n어싱크 데프 비동기(): 리턴 수퍼()\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaisesRegex(RuntimeError,r"super\(\): no arguments"): next(vm.globals["생성"]())
        with self.assertRaisesRegex(RuntimeError,r"super\(\): no arguments"): asyncio.run(vm.globals["비동기"]())

    def test_class_local_binding_blocks_enclosing_function_lookup(self):
        source='값="전역"\n데프 생성():\n    값="바깥"\n    클래스 결과:\n        읽음=값\n        값="클래스"\n    리턴 결과\n종류=생성()\n결과=(종류.읽음, 종류.값)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("전역","클래스"))

    def test_property_setter_receives_class_cell_for_zero_argument_super(self):
        source='클래스 기반:\n    데프 저장(셀프, 값): 셀프.저장값=값\n클래스 자식(기반):\n    @프로퍼티\n    데프 값(셀프): 리턴 셀프.저장값\n    @값.setter\n    데프 값(셀프, 새값): 수퍼().저장(새값)\n객체=자식()\n객체.값=42\n결과=객체.값\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)

    def test_class_comprehension_skips_class_namespace(self):
        source='값="전역"\n클래스 첫째:\n    값="클래스"\n    결과=[값 포 _ 인 레인지(1)]\n데프 생성():\n    값="바깥"\n    클래스 둘째:\n        값="클래스"\n        결과=[값 포 _ 인 레인지(1)]\n    리턴 둘째\n둘째=생성()\n결과=(첫째.결과, 둘째.결과)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(["전역"],["바깥"]))

    def test_bound_method_exposes_python_introspection_contract(self):
        source='클래스 종류:\n    데프 메서드(셀프): 리턴 1\n객체=종류()\n첫째=객체.메서드\n둘째=객체.메서드\n결과=(첫째.__self__ 이즈 객체, 첫째.__func__ 이즈 종류.메서드, 첫째 == 둘째, 검사해시(첫째)==검사해시(둘째))\n'
        vm=VM(); vm.globals["검사해시"]=hash; vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True,True,True))

    def test_function_descriptor_get_allows_omitted_owner(self):
        source='클래스 종류:\n    데프 메서드(셀프, 값): 리턴 값\n객체=종류()\n묶임=종류.메서드.__get__(객체)\n결과=(묶임.__self__ 이즈 객체, 묶임.__func__ 이즈 종류.메서드, 묶임(42))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True,42))

    def test_descriptor_precedence_and_attribute_hooks(self):
        source='''
기록=[]
클래스 데이터:
    데프 __get__(셀프, 객체, 소유자): 기록.append("data-get"); 리턴 10
    데프 __set__(셀프, 객체, 값): 기록.append(("data-set",값)); 객체.__dict__["저장"]=값
    데프 __delete__(셀프, 객체): 기록.append("data-del")
클래스 비데이터:
    데프 __get__(셀프, 객체, 소유자): 기록.append("nondata-get"); 리턴 20
클래스 대상:
    가=데이터()
    나=비데이터()
    데프 __getattribute__(셀프, 이름):
        기록.append(("getattribute",이름))
        리턴 수퍼().__getattribute__(이름)
    데프 __getattr__(셀프, 이름): 기록.append(("getattr",이름)); 리턴 99
객체=대상()
객체.__dict__["가"]=1
객체.__dict__["나"]=2
첫째=(객체.가,객체.나,객체.없음)
객체.가=42
델 객체.가
결과=(첫째,객체.__dict__["저장"],"data-get" 인 기록,"nondata-get" 인 기록,"data-del" 인 기록)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((10,2,99),42,True,False,True))

    def test_descriptor_attribute_error_falls_back_to_getattr_after_set_name(self):
        source='''
기록=[]
클래스 설명자:
    데프 __set_name__(셀프, 소유자, 이름): 기록.append(("set-name",이름))
    데프 __get__(셀프, 객체, 소유자):
        기록.append(("get",객체 이즈 넌,소유자.__name__))
        레이즈 애트리뷰트에러("없음")
클래스 대상:
    값=설명자()
    데프 __getattr__(셀프, 이름): 기록.append(("fallback",이름)); 리턴 42
객체=대상()
결과=객체.값
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)
        self.assertEqual(vm.globals["기록"],[('set-name','값'),('get',False,'대상'),('fallback','값')])

    def test_starred_bases_and_keyword_unpacking(self):
        source='클래스 기반: 패스\n클래스 메타(타입):\n    데프 __new__(메타, 이름, 기반들, 공간, **옵션):\n        공간["표식"] = 옵션["표식"]\n        리턴 수퍼().__new__(메타, 이름, 기반들, 공간)\n기반들 = (기반,)\n옵션 = {"metaclass": 메타, "표식": 42}\n클래스 자식(*기반들, **옵션): 패스\n결과 = (이즈서브클래스(자식, 기반), 자식.표식)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,42))

    def test_function_class_and_bound_method_metadata(self):
        source='데프 함수(가=1, *, 나=2):\n    "함수 문서"\n    패스\n클래스 대상:\n    "클래스 문서"\n    데프 메서드(셀프): 패스\n인스턴스=대상()\n결과=(함수.__name__, 함수.__qualname__, 함수.__module__, 함수.__doc__, 함수.__defaults__, 함수.__kwdefaults__, 대상.__module__, 대상.__qualname__, 대상.__doc__, 대상.메서드.__qualname__, 인스턴스.메서드.__self__ 이즈 인스턴스, 인스턴스.메서드.__func__ 이즈 대상.메서드)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("함수","함수","__main__","함수 문서",(1,),{"나":2},"__main__","대상","클래스 문서","대상.메서드",True,True))

    def test_mro_entries_orig_bases_and_descriptor_hooks(self):
        source='기록=[]\n클래스 기반:\n    @클래스메서드\n    데프 __init_subclass__(클래스값, **옵션): 기록.append(("하위", 옵션["표식"]))\n클래스 프록시:\n    데프 __mro_entries__(셀프, 원본): 리턴 (기반,)\n클래스 설명자:\n    데프 __set_name__(셀프, 소유자, 이름): 기록.append(("이름", 이름))\n프록시값=프록시()\n클래스 자식(프록시값, 표식=42):\n    속성=설명자()\n결과=(이즈서브클래스(자식, 기반), 자식.__orig_bases__[0] 이즈 프록시값, 기록)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True,[("이름","속성"),("하위",42)]))

    def test_set_name_can_call_new_class_method_using_zero_argument_super(self):
        source='결과=[]\n클래스 기반:\n    @클래스메서드\n    데프 값(클래스값): 리턴 42\n클래스 설명자:\n    데프 __set_name__(셀프, 소유자, 이름): 결과.append(소유자.값())\n클래스 자식(기반):\n    @클래스메서드\n    데프 값(클래스값): 리턴 수퍼().값()\n    속성=설명자()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[42])

    def test_arbitrary_descriptor_decorator_preserves_zero_argument_super_cell(self):
        source='''
클래스 감싸개:
    데프 __init__(셀프, 함수): 셀프.함수=함수
    데프 __get__(셀프, 객체, 소유자): 리턴 셀프.함수.__get__(객체,소유자)
데프 감싸기(함수): 리턴 감싸개(함수)
클래스 기반:
    데프 값(셀프): 리턴 42
클래스 자식(기반):
    @감싸기
    데프 값(셀프): 리턴 수퍼().값()
결과=자식().값()
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)

    def test_set_name_can_call_new_class_method_reading_dunder_class(self):
        source='결과=[]\n클래스 설명자:\n    데프 __set_name__(셀프, 소유자, 이름): 결과.append(소유자.자기() 이즈 소유자)\n클래스 대상:\n    @클래스메서드\n    데프 자기(클래스값): 리턴 __class__\n    속성=설명자()\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[True])

    def test_local_dunder_class_assignment_disables_implicit_class_cell(self):
        assigned='클래스 기반: 패스\n클래스 대상(기반):\n    데프 함수(셀프):\n        __class__=기반\n        리턴 수퍼()\n결과=대상().함수()\n'
        deleted='클래스 기반: 패스\n클래스 대상(기반):\n    데프 함수(셀프):\n        델 __class__\n        리턴 수퍼()\n결과=대상().함수()\n'
        with self.assertRaisesRegex(RuntimeError,"__class__ cell not found"): VM().run(compile_source(assigned))
        with self.assertRaises(UnboundLocalError): VM().run(compile_source(deleted))
    def test_descriptor_decorators_and_bound_keyword_arguments(self):
        source='\n'.join([
            '클래스 도구:',
            '    데프 __init__(셀프, 값):',
            '        셀프.값 = 값',
            '    @프로퍼티',
            '    데프 두배(셀프):',
            '        리턴 셀프.값 * 2',
            '    @스태틱메서드',
            '    데프 더하기(가, 나=0):',
            '        리턴 가 + 나',
            '    @클래스메서드',
            '    데프 이름(클래스):',
            '        리턴 클래스.__name__',
            '    데프 계산(셀프, 배수=1):',
            '        리턴 셀프.값 * 배수',
            '객체 = 도구(21)',
            '결과 = (객체.두배, 도구.더하기(20, 나=22), 도구.이름(), 객체.계산(배수=2))',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,42,"도구",42))

    def test_metaclass_keyword_and_prepare_namespace(self):
        events=[]
        class Meta(type):
            @classmethod
            def __prepare__(meta,name,bases,**kwargs): events.append(("prepare",name)); return {"준비됨":True}
            def __new__(meta,name,bases,namespace,**kwargs): events.append(("new",namespace["준비됨"])); return super().__new__(meta,name,bases,namespace)
        vm=VM(); vm.globals["메타"]=Meta
        vm.run(compile_source('클래스 결과(메타클래스=메타):\n    값 = 42\n생성 = (결과.준비됨, 결과.값)\n'))
        self.assertEqual(vm.globals["생성"],(True,42)); self.assertEqual(events,[("prepare","결과"),("new",True)])

    def test_metaclass_may_return_non_type_object(self):
        sentinel=object()
        class Meta(type):
            def __new__(meta,name,bases,namespace,**kwargs): return sentinel
        vm=VM(); vm.globals["메타"]=Meta
        vm.run(compile_source('클래스 결과(메타클래스=메타):\n    데프 메서드(셀프): 리턴 42\n'))
        self.assertIs(vm.globals["결과"],sentinel)

    def test_prepare_accepts_minimal_mapping_without_dict_helpers(self):
        from collections.abc import MutableMapping
        observed=[]
        class Namespace(MutableMapping):
            def __init__(self): self.data={}
            def __getitem__(self,key): return self.data[key]
            def __setitem__(self,key,value): self.data[key]=value
            def __delitem__(self,key): del self.data[key]
            def __iter__(self): return iter(self.data)
            def __len__(self): return len(self.data)
            update=None; pop=None; values=None
        class Meta(type):
            @classmethod
            def __prepare__(meta,name,bases,**kwargs): return Namespace()
            def __new__(meta,name,bases,namespace,**kwargs):
                observed.append(tuple(namespace))
                return super().__new__(meta,name,bases,dict(namespace))
        vm=VM(); vm.globals["메타"]=Meta
        vm.run(compile_source('클래스 결과(메타클래스=메타):\n    값=40\n    데프 더하기(셀프, 수): 리턴 셀프.값+수\n생성=결과().더하기(2)\n'))
        self.assertEqual(vm.globals["생성"],42)
        self.assertFalse(any(key.startswith("$") for key in observed[0]))
    def test_class_constructor_attributes_and_bound_method(self):
        source='클래스 카운터:\n    데프 __init__(셀프, 시작):\n        셀프.값 = 시작\n    데프 증가(셀프):\n        셀프.값 = 셀프.값 + 1\n        리턴 셀프.값\n객체 = 카운터(40)\n객체.증가()\n결과 = 객체.증가()\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],42)

    def test_inheritance_and_method_resolution(self):
        source='클래스 부모:\n    데프 값(셀프):\n        리턴 40\n클래스 자식(부모):\n    데프 더하기(셀프):\n        리턴 셀프.값() + 2\n결과 = 자식().더하기()\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],42)

    def test_function_and_class_decorators(self):
        source='순서 = []\n데프 데코(이름):\n    데프 적용(대상):\n        순서.append(이름)\n        리턴 대상\n    리턴 적용\n@데코("위")\n@데코("아래")\n데프 함수():\n    리턴 42\n@데코("클래스")\n클래스 상자:\n    패스\n결과 = (함수(), 순서)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(42,["아래","위","클래스"]))

    def test_decorated_definition_binds_name_only_after_success(self):
        source='''
기록=[]
함수="이전 함수"
상자="이전 클래스"
데프 함수장식(대상): 기록.append(함수); 리턴 대상
데프 클래스장식(대상): 기록.append(상자); 리턴 대상
@함수장식
데프 함수(): 리턴 42
@클래스장식
클래스 상자: 패스
보존="이전"
데프 실패(대상): 레이즈 밸류에러()
트라이:
    @실패
    데프 보존(): 패스
익셉트 밸류에러: 패스
결과=(기록,함수(),이즈인스턴스(상자,타입),보존)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(["이전 함수","이전 클래스"],42,True,"이전"))

    def test_decorator_evaluation_definition_and_application_order(self):
        source='''
기록=[]
데프 표시(이름,값): 기록.append(이름); 리턴 값
데프 장식생성(이름):
    기록.append("평가-"+이름)
    데프 적용(대상): 기록.append("적용-"+이름); 리턴 대상
    리턴 적용
@장식생성("위")
@장식생성("아래")
데프 함수(값=표시("기본값",42)): 패스
@장식생성("클래스")
클래스 상자(표시("기반",오브젝트)):
    표시("본문",넌)
결과=기록
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["평가-위","평가-아래","기본값","적용-아래","적용-위","평가-클래스","기반","본문","적용-클래스"])

    def test_class_keyword_unpack_accepts_mapping_protocol(self):
        source='''
기록=[]
클래스 매핑:
    데프 keys(셀프): 리턴 ["표식"]
    데프 __getitem__(셀프,키): 기록.append(키); 리턴 42
클래스 메타(타입):
    데프 __new__(메타,이름,기반들,공간,**옵션):
        기록.append(옵션)
        리턴 수퍼().__new__(메타,이름,기반들,공간)
클래스 대상(메타클래스=메타,**매핑()): 패스
결과=기록
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["표식",{"표식":42}])

        with self.assertRaisesRegex(TypeError,"keywords must be strings"):
            VM().run(compile_source('클래스 매핑:\n    데프 keys(셀프): 리턴 [1]\n    데프 __getitem__(셀프,키): 리턴 42\n클래스 대상(**매핑()): 패스\n'))

    def test_class_argument_merge_failure_stops_later_evaluation(self):
        source='기록=[]\n데프 표시(): 기록.append("나중"); 리턴 타입\n트라이:\n    클래스 대상(**{"중복":1},**{"중복":2},메타클래스=표시()): 패스\n익셉트 타입에러: 패스\n결과=기록\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[])
