import unittest
from hython.compiler import compile_source
from hython.vm import VM

class AssignmentSemanticsTests(unittest.TestCase):
    def test_rhs_expression_lists_preserve_single_trailing_comma(self):
        source='''
일반=1,
첫째=둘째=2,
누적=()
누적 += 3,
def 반환(): return 4,
def 생성(): yield 5,
결과=(일반,첫째,둘째,누적,반환(),list(생성()))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],((1,),(2,),(2,),(3,),(4,),[(5,)]))

    def test_augmented_assignment_accepts_unparenthesized_tuple_rhs(self):
        vm=VM(); vm.run(compile_source('값=()\n값 += 1,2\n'))
        self.assertEqual(vm.globals["값"],(1,2))
    def test_recursive_and_empty_delete_targets_with_trailing_comma(self):
        source='''
class 대상: pass
객체=대상(); 객체.속성=1
자료=[10,20]
첫째=1
둘째=2
del (첫째, [둘째, 객체.속성], 자료[0]),
del (), []
결과=("첫째" in globals(),"둘째" in globals(),hasattr(객체,"속성"),자료)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(False,False,False,[20]))
    def test_empty_semicolon_and_inline_compound_suite_are_rejected(self):
        for source in (';\n','if True: ;\n','if True: if True: pass\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_rhs_precedes_attribute_and_subscript_target_evaluation(self):
        source='기록=[]\n클래스 상자: 패스\n상자값=상자()\n자료=[0]\n데프 오른쪽(값): 기록.append("오른쪽"); 리턴 값\n데프 객체(): 기록.append("객체"); 리턴 상자값\n데프 목록(): 기록.append("목록"); 리턴 자료\n데프 인덱스(): 기록.append("인덱스"); 리턴 0\n객체().값 = 오른쪽(20)\n목록()[인덱스()] = 오른쪽(22)\n결과=(기록, 상자값.값 + 자료[0])\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(["오른쪽","객체","오른쪽","목록","인덱스"],42))

    def test_attribute_annotation_expression_is_not_evaluated(self):
        source='기록=[]\n데프 표식(): 기록.append("실행"); 리턴 인트\n클래스 상자: 패스\n대상=상자()\n대상.값: 표식() = 42\n결과=(대상.값, 기록)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(42,[]))

    def test_valueless_attribute_and_subscript_annotations_evaluate_targets_only(self):
        source='''
기록=[]
클래스 상자: 패스
대상=상자()
자료=[0]
데프 객체(): 기록.append("객체"); 리턴 대상
데프 목록(): 기록.append("목록"); 리턴 자료
데프 키(): 기록.append("키"); 리턴 0
데프 표식(): 기록.append("주석"); 리턴 인트
객체().값: 표식()
목록()[키()]: 표식()
결과=(기록, 해즈애트리뷰트(대상,"값"), 자료)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(["객체","목록","키"],False,[0]))

    def test_valueless_attribute_annotation_still_raises_target_name_error(self):
        with self.assertRaises(NameError): VM().run(compile_source('없는대상.값: 인트\n'))
    def test_chained_assignment_shares_single_value(self):
        source='가 = 나 = []\n가.append(42)\n결과 = (가 이즈 나, 나)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(True,[42]))

    def test_attribute_and_subscript_augmented_assignment(self):
        source='클래스 상자:\n    패스\n상자값 = 상자()\n상자값.수 = 4\n상자값.수 += 3\n자료 = [10]\n자료[0] *= 2\n결과 = (상자값.수, 자료[0])\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(7,20))

    def test_augmented_assignment_uses_in_place_protocol(self):
        source='가=[]\n나=가\n가 += [42]\n클래스 값:\n    데프 __init__(셀프): 셀프.기록=[]\n    데프 __iadd__(셀프, 다른값): 셀프.기록.append(다른값); 리턴 셀프\n객체=값()\n별칭=객체\n객체 += 7\n결과=(가 이즈 나,나,객체 이즈 별칭,별칭.기록)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,[42],True,[7]))

    def test_augmented_attribute_and_subscript_targets_evaluate_once(self):
        source='''
기록=[]
클래스 상자: 패스
상자값=상자(); 상자값.값=10
자료=[20]
데프 객체(): 기록.append("객체"); 리턴 상자값
데프 목록(): 기록.append("목록"); 리턴 자료
데프 인덱스(): 기록.append("인덱스"); 리턴 0
데프 오른쪽(값): 기록.append("오른쪽"); 리턴 값
객체().값 += 오른쪽(1)
목록()[인덱스()] += 오른쪽(2)
결과=(기록,상자값.값,자료[0])
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(["객체","오른쪽","목록","인덱스","오른쪽"],11,22))

    def test_bitwise_augmented_assignments(self):
        source='값 = 3\n값 |= 4\n값 <<= 1\n자료 = [15]\n자료[0] &= 6\n결과 = (값, 자료[0])\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(14,6))

    def test_unparenthesized_tuple_expressions_and_multiple_delete(self):
        source='\n'.join([
            '쌍 = 1, 2',
            '데프 반환():',
            '    리턴 3, 4',
            '데프 생성():',
            '    일드 5, 6',
            '가 = 10',
            '자료 = [20, 30]',
            '델 가, 자료[0]',
            '결과 = (쌍, 반환(), 넥스트(생성()), 자료)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],((1,2),(3,4),(5,6),[30]))

    def test_semicolon_statement_lists_and_inline_suite(self):
        source='가 = 1; 나 = 2\n이프 가 < 나: 가 += 10; 나 += 20\n결과 = (가, 나)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(11,22))
