import annotationlib
import unittest
from hython.compiler import compile_source
from hython.vm import VM

class AnnotationTests(unittest.TestCase):
    def test_type_parameter_list_cannot_be_empty(self):
        for source in ('def 함수[](): pass\n','class 대상[]: pass\n','type 별칭[] = int\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)

    def test_variadic_type_parameters_reject_bounds_but_accept_defaults(self):
        for source in ('def 함수[*종류들: int](): pass\n','class 대상[**매개변수: int]: pass\n','type 별칭[*종류들: int] = tuple\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
        compile_source('def 함수[*종류들=tuple, **매개변수=()](): pass\n')

    def test_type_var_tuple_unpack_default_and_forward_reference(self):
        source='클래스 대상[*Ts = *Us, *Us = *튜플[인트, 스트링]]: 패스\n첫째,둘째=대상.__type_params__\n결과=(첫째.__default__.__args__[0] 이즈 둘째,둘째.__default__)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"][0],True)
        self.assertEqual(str(vm.globals["결과"][1]),"*tuple[int, str]")
    def test_named_expression_restrictions_respect_nested_lambda_scope(self):
        for source in (
            'type 별칭 = (값 := int)\n',
            'def 함수[T: (값 := int)](): pass\n',
            'class 대상[T = (값 := int)]: pass\n',
        ):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
        compile_source('주석: (lambda: (값 := int))\n')
        compile_source('type 별칭 = lambda: (값 := int)\n')
    def test_type_alias_value_is_lazy_and_supports_forward_reference(self):
        source='기록=[]\n데프 평가(값): 기록.append(값); 리턴 나중\n타입 별칭 = 평가("평가")\n정의후=튜플(기록)\n클래스 나중: 패스\n첫째=별칭.__value__\n둘째=별칭.__value__\n결과=(정의후, 기록, 첫째 이즈 나중, 둘째 이즈 첫째)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((),["평가"],True,True))
        self.assertIsInstance(vm.globals["별칭"],__import__("typing").TypeAliasType)

    def test_generic_alias_bound_default_and_value_are_lazy(self):
        source='기록=[]\n데프 표식(이름, 값): 기록.append(이름); 리턴 값\n타입 별칭[T: 표식("경계", 인트) = 표식("기본", 불)] = 표식("값", 리스트[T])\n정의후=튜플(기록)\n변수=별칭.__type_params__[0]\n경계=변수.__bound__\n기본=변수.__default__\n값=별칭.__value__\n결과=(정의후, 기록, 경계 이즈 인트, 기본 이즈 불, 값)\n'
        vm=VM(); vm.run(compile_source(source))
        result=vm.globals["결과"]
        self.assertEqual(result[:4],((),["경계","기본","값"],True,True))
        self.assertEqual(result[4],list[vm.globals["별칭"].__type_params__[0]])

    def test_function_and_class_type_parameter_metadata_is_lazy(self):
        source='기록=[]\n데프 표식(이름, 값): 기록.append(이름); 리턴 값\n데프 함수[T: 표식("함수경계", 인트) = 표식("함수기본", 불)](): 패스\n클래스 종류[U: 표식("클래스경계", 스트링) = 표식("클래스기본", 바이츠)]: 패스\n정의후=튜플(기록)\n함수변수=함수.__type_params__[0]\n종류변수=종류.__type_params__[0]\n결과=(정의후, 함수변수.__bound__, 함수변수.__default__, 종류변수.__bound__, 종류변수.__default__, 기록)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((),int,bool,str,bytes,["함수경계","함수기본","클래스경계","클래스기본"]))

    def test_generic_definitions_restore_existing_type_parameter_names(self):
        source='T="바깥"\n데프 함수[T](값=T): 리턴 값\n함수후=T\n클래스 상자[T]: 패스\n결과=(함수후,T,함수.__defaults__[0] 이즈 함수.__type_params__[0])\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("바깥","바깥",False))
        self.assertEqual(vm.globals["함수"].__defaults__,('바깥',))

    def test_failed_generic_definition_restores_type_parameter_names(self):
        source='''
T="바깥"
데프 실패(): 레이즈 밸류에러("기본값")
트라이:
    데프 함수[T](값=실패()): 패스
익셉트 밸류에러: 패스
결과=(T,"함수" 인 글로벌스())
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("바깥",False))
        self.assertNotIn("$saved_names",vm.globals)

    def test_generic_class_header_uses_type_parameter_and_rolls_back_on_failure(self):
        source='''
T="바깥"
클래스 기반:
    @클래스메서드
    데프 __class_getitem__(클래스값, 값): 레이즈 밸류에러(값)
트라이:
    클래스 실패[T](기반[T]): 패스
익셉트 밸류에러 애즈 오류: 잡힘=오류.args[0]
결과=(T, 잡힘)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"][0],"바깥")
        self.assertEqual(vm.globals["결과"][1].__name__,"T")
        self.assertNotIn("실패",vm.globals); self.assertNotIn("$saved_names",vm.globals)

    def test_generic_class_type_parameter_does_not_leak_as_attribute(self):
        vm=VM(); vm.run(compile_source('클래스 상자[T]:\n    값: T\n결과=(해즈애트리뷰트(상자,"T"),상자.__annotations__["값"] 이즈 상자.__type_params__[0])\n'))
        self.assertEqual(vm.globals["결과"],(False,True))

    def test_class_decorator_annotation_access_sees_previous_global_binding(self):
        source='''
기록=[]
데프 장식(종류): 기록.append(종류.__annotations__["값"]); 리턴 종류
대상="이전"
@장식
클래스 대상:
    값: 대상
결과=기록
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["이전"])

    def test_later_type_parameter_bound_captures_earlier_parameter(self):
        source='데프 함수[T, U: T](): 패스\n변수들=함수.__type_params__\n결과=(변수들[1].__bound__ 이즈 변수들[0], "T" 인 글로벌스())\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,False))

    def test_type_parameter_default_can_forward_reference_later_parameter(self):
        vm=VM(); vm.run(compile_source('클래스 대상[T=U,U=인트]: 패스\n첫째,둘째=대상.__type_params__\n결과=(첫째.__default__ 이즈 둘째,둘째.__default__ 이즈 인트)\n'))
        self.assertEqual(vm.globals["결과"],(True,True)); self.assertNotIn("$type_parameter_scope",vm.globals)

    def test_nested_type_scopes_resolve_closure_and_global_names_lazily(self):
        source='''
클래스 전역표식: 패스
데프 바깥():
    클래스 지역표식: 패스
    데프 중간():
        데프 함수[T: 튜플[지역표식,전역표식]](): 패스
        타입 별칭 = 딕트[지역표식,전역표식]
        리턴 함수,별칭
    리턴 (*중간(),지역표식)
함수,별칭,지역표식=바깥()
결과=(함수.__type_params__[0].__bound__ == 튜플[지역표식,전역표식],별칭.__value__ == 딕트[지역표식,전역표식])
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True))

    def test_type_scope_observes_later_local_cell_value(self):
        source='''
클래스 표식: 패스
데프 바깥():
    데프 함수[T: 표식](): 패스
    클래스 표식: 패스
    리턴 함수,표식
함수,지역표식=바깥()
결과=함수.__type_params__[0].__bound__ 이즈 지역표식
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertIs(vm.globals["결과"],True)

    def test_type_alias_evaluator_preserves_string_and_forwardref_formats(self):
        vm=VM(); vm.run(compile_source('타입 별칭[T] = 리스트[T] | 없는타입\n'))
        alias=vm.globals["별칭"]
        string=annotationlib.call_evaluate_function(alias.evaluate_value,annotationlib.Format.STRING)
        forward=annotationlib.call_evaluate_function(alias.evaluate_value,annotationlib.Format.FORWARDREF)
        self.assertEqual(string,"list[T] | 없는타입")
        self.assertIsInstance(forward,annotationlib.ForwardRef)
        self.assertIn("없는타입",forward.__forward_arg__)

    def test_type_parameter_evaluators_preserve_string_format(self):
        vm=VM(); vm.run(compile_source('데프 함수[T: 리스트[없는타입] = 딕트[스트링, 없는타입]](): 패스\n'))
        parameter=vm.globals["함수"].__type_params__[0]
        bound=annotationlib.call_evaluate_function(parameter.evaluate_bound,annotationlib.Format.STRING)
        default=annotationlib.call_evaluate_function(parameter.evaluate_default,annotationlib.Format.STRING)
        self.assertEqual(bound,"list[없는타입]")
        self.assertEqual(default,"dict[str, 없는타입]")

    def test_type_alias_parameter_bound_and_default(self):
        vm=VM(); vm.run(compile_source("타입 별칭[티: 인트 = 인트] = 리스트[티]\n결과 = (별칭.__type_params__[0].__bound__, 별칭.__type_params__[0].__default__)\n"))
        self.assertEqual(vm.globals["결과"],(int,int))

    def test_duplicate_type_parameter_is_rejected(self):
        for source in ("데프 함수[티, 티](): 패스\n","클래스 대상[티, 티]: 패스\n","타입 별칭[티, 티] = 티\n"):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)

    def test_local_variable_annotation_is_not_evaluated(self):
        source='기록=[]\n데프 표식(): 기록.append("실행"); 리턴 인트\n데프 함수():\n    값: 표식() = 42\n    트라이:\n        다른값: 표식()\n    파이널리: 패스\n    리턴 값\n결과=(함수(), 기록)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,[]))

    def test_python_314_function_annotations_are_lazily_evaluated(self):
        source='기록=[]\n데프 표식(): 기록.append("평가"); 리턴 인트\n데프 함수(값: 나중) -> 표식(): 리턴 값\n정의후=튜플(기록)\n클래스 나중: 패스\n주석=함수.__annotations__\n결과=(정의후, 기록, 주석["값"] 이즈 나중, 주석["return"] 이즈 인트, 함수.__annotate__() 이즈 주석)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((),["평가"],True,True,True))

    def test_method_lazy_annotations_see_live_class_namespace_and_private_names(self):
        source='클래스 대상:\n    별칭=인트\n    __비공개=스트링\n    데프 메서드(셀프, 값: 별칭) -> __비공개: 리턴 값\n대상.별칭=플로트\n결과=(대상.메서드.__annotations__["값"] 이즈 플로트,대상.메서드.__annotations__["return"] 이즈 스트링)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True))

    def test_generic_method_annotation_scope_prioritizes_method_then_class_parameters(self):
        source='클래스 대상[T]:\n    데프 다른[U](셀프, 가: T, 나: U) -> 튜플[T,U]: 리턴 (가,나)\n    데프 가림[T](셀프, 값: T) -> T: 리턴 값\n결과=(대상.다른.__annotations__["가"] 이즈 대상.__type_params__[0],대상.다른.__annotations__["나"] 이즈 대상.다른.__type_params__[0],대상.가림.__annotations__["값"] 이즈 대상.가림.__type_params__[0])\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True,True))

    def test_private_method_annotations_are_mangled_in_string_and_forwardref_formats(self):
        source='클래스 대상:\n    데프 메서드(셀프, 값: __없는타입, 문자: "__그대로"): 패스\n'
        vm=VM(); vm.run(compile_source(source)); method=vm.globals["대상"].메서드
        strings=annotationlib.get_annotations(method,format=annotationlib.Format.STRING)
        refs=annotationlib.get_annotations(method,format=annotationlib.Format.FORWARDREF)
        self.assertEqual(strings,{"값":"_대상__없는타입","문자":"\"__그대로\""})
        self.assertEqual(refs["값"].__forward_arg__,"_대상__없는타입")
        self.assertIs(refs["값"].__owner__,method)
        self.assertEqual(refs["문자"],"__그대로")

    def test_decorated_away_method_retains_class_annotation_scope(self):
        source='클래스 대상:\n    별칭=인트\n    데프 감싸기(함수): 리턴 [함수]\n    @감싸기\n    데프 메서드(값: 별칭): 패스\n대상.별칭=플로트\n결과=대상.메서드[0].__annotations__["값"]\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertIs(vm.globals["결과"],float)

    def test_generic_class_type_parameters_are_hidden_from_locals_until_shadowed(self):
        source='클래스 숨김[T]:\n    로컬=로컬스().copy()\n    디렉터리=디어()\n클래스 가림[T]:\n    T=스트링\n    로컬=로컬스().copy()\n결과=("T" 인 숨김.로컬,"T" 인 숨김.디렉터리,가림.로컬["T"] 이즈 스트링,가림.T 이즈 스트링)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(False,False,True,True))

    def test_generic_method_body_captures_class_and_method_type_parameters(self):
        source='클래스 대상[T]:\n    T=스트링\n    데프 메서드[U](셀프):\n        리턴 ("T" 인 로컬스(),"U" 인 로컬스(),T,U)\n    데프 미사용(셀프): 리턴 "T" 인 로컬스()\n    데프 중첩(셀프):\n        데프 내부(): 리턴 T\n        리턴 ("T" 인 로컬스(),내부())\n결과=(대상().메서드(),대상().미사용(),대상().중첩())\n'
        vm=VM(); vm.run(compile_source(source)); result=vm.globals["결과"]
        method,unused,nested=result
        self.assertEqual(method[:2],(True,True))
        self.assertIs(method[2],vm.globals["대상"].__type_params__[0])
        self.assertIs(method[3],vm.globals["대상"].메서드.__type_params__[0])
        self.assertIs(unused,False)
        self.assertEqual(nested[0],True); self.assertIs(nested[1],method[2])

    def test_python_314_module_annotations_are_lazily_evaluated(self):
        source='기록=[]\n데프 표식(): 기록.append("모듈"); 리턴 인트\n값: 나중\n다른값: 표식()\n정의후=튜플(기록)\n클래스 나중: 패스\n주석=__annotations__\n결과=(정의후, 기록, 주석["값"] 이즈 나중, 주석["다른값"] 이즈 인트, __annotate__() 이즈 주석)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((),["모듈"],True,True,True))

    def test_python_314_class_annotations_are_lazily_evaluated(self):
        source='기록=[]\n데프 표식(): 기록.append("클래스"); 리턴 인트\n클래스 대상:\n    값: 나중\n    다른값: 표식()\n정의후=튜플(기록)\n클래스 나중: 패스\n주석=대상.__annotations__\n결과=(정의후, 기록, 주석["값"] 이즈 나중, 주석["다른값"] 이즈 인트, 대상.__annotate__() 이즈 주석)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((),["클래스"],True,True,True))

    def test_class_lazy_annotations_see_live_class_namespace(self):
        source='클래스 대상:\n    값: 나중\n대상.나중=인트\n결과=대상.__annotations__["값"] 이즈 인트\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertIs(vm.globals["결과"],True)

    def test_class_lazy_annotation_live_namespace_falls_back_and_shadows_type_parameter(self):
        source='나중=스트링\n클래스 일반:\n    나중=인트\n    값: 나중\n델 일반.나중\n클래스 제네릭[T]:\n    T=스트링\n    값: T\n결과=(일반.__annotations__["값"] 이즈 스트링,제네릭.__annotations__["값"] 이즈 스트링,해즈애트리뷰트(제네릭,"T"))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True,True))

    def test_annotationlib_string_and_forwardref_formats(self):
        vm=VM(); vm.run(compile_source('데프 함수(값: 없는타입) -> 리스트[없는타입]: 리턴 값\n클래스 대상:\n    값: 없는타입\n'))
        function_strings=annotationlib.get_annotations(vm.globals["함수"],format=annotationlib.Format.STRING)
        class_strings=annotationlib.get_annotations(vm.globals["대상"],format=annotationlib.Format.STRING)
        self.assertEqual(function_strings,{"값":"없는타입","return":"list[없는타입]"}); self.assertEqual(class_strings,{"값":"없는타입"})
        function_refs=annotationlib.get_annotations(vm.globals["함수"],format=annotationlib.Format.FORWARDREF)
        class_refs=annotationlib.get_annotations(vm.globals["대상"],format=annotationlib.Format.FORWARDREF)
        self.assertIsInstance(function_refs["값"],annotationlib.ForwardRef)
        self.assertIsInstance(function_refs["return"].__args__[0],annotationlib.ForwardRef)
        self.assertIsInstance(class_refs["값"],annotationlib.ForwardRef)

    def test_function_annotation_formats_preserve_cpython_side_effect_order(self):
        source='기록=[]\n데프 표식(): 기록.append("평가"); 리턴 인트\n데프 함수(값: 표식(), 전방: 없는타입): 패스\n'
        vm=VM(); vm.run(compile_source(source)); function=vm.globals["함수"]
        strings=annotationlib.get_annotations(function,format=annotationlib.Format.STRING)
        self.assertEqual(strings,{"값":"표식()","전방":"없는타입"}); self.assertEqual(vm.globals["기록"],["평가"])
        refs=annotationlib.get_annotations(function,format=annotationlib.Format.FORWARDREF)
        self.assertIs(refs["전방"].__owner__,function); self.assertEqual(vm.globals["기록"],["평가","평가","평가"])
        vm.globals["없는타입"]=str
        values=annotationlib.get_annotations(function,format=annotationlib.Format.VALUE)
        self.assertIs(values["값"],int); self.assertIs(values["전방"],str)
        self.assertEqual(vm.globals["기록"],["평가","평가","평가","평가"])
    def test_name_attribute_and_subscript_annotations(self):
        source='\n'.join([
            '이름: 스트링 = "하이썬"',
            '클래스 상자:',
            '    패스',
            '상자값 = 상자()',
            '상자값.수: 인트 = 3',
            '자료 = [0]',
            '자료[0]: 인트 = 7',
            '결과 = (이름, __annotations__["이름"], 상자값.수, 자료[0])',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("하이썬",str,3,7))

    def test_function_annotations_are_exposed(self):
        source='데프 변환(값: 인트, 이름: 스트링 = "x") -> 스트링:\n    리턴 이름 * 값\n결과 = 변환.__annotations__\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],{"값":int,"이름":str,"return":str})

    def test_python_314_type_aliases(self):
        source='\n'.join([
            '타입 점 = 튜플[플로트, 플로트]',
            '타입 모음[T] = 리스트[T] | 셋[T]',
            '결과 = (점.__value__, 모음.__type_params__[0].__name__)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(tuple[float,float],"T"))

    def test_python_314_function_and_class_type_parameters(self):
        source='\n'.join([
            '데프 항등[T](값: T) -> T:',
            '    리턴 값',
            '클래스 상자[T]:',
            '    형식: T',
            '결과 = (항등(42), 항등.__type_params__[0].__name__, 항등.__annotations__["값"], 상자.__type_params__[0].__name__)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"][0:2],(42,"T"))
        self.assertIs(vm.globals["결과"][2],vm.globals["항등"].__type_params__[0])
        self.assertEqual(vm.globals["결과"][3],"T"); self.assertNotIn("T",vm.globals)

    def test_type_parameter_bound_and_default(self):
        source='데프 선택[T: 인트 = 불](값: T) -> T:\n    리턴 값\n변수 = 선택.__type_params__[0]\n결과 = (변수.__bound__, 변수.__default__)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(int,bool))
    def test_variable_parameter_and_return_annotations(self):
        source='값: 인트 = 40\n미정: 스트링\n데프 더하기(가: 인트, 나: 인트 = 2) -> 인트:\n    리턴 가 + 나\n결과 = 더하기(값)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],42); self.assertNotIn("미정",vm.globals)
