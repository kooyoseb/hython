import unittest
from hython.compiler import compile_source
from hython.vm import VM

class UnpackingTests(unittest.TestCase):
    def test_single_starred_for_target_with_trailing_comma(self):
        vm=VM(); vm.run(compile_source('결과=[]\nfor *묶음, in [(1,2),(3,)]: 결과.append(묶음)\n'))
        self.assertEqual(vm.globals["결과"],[[1,2],[3]])

    def test_comprehension_and_with_reject_multiple_starred_targets(self):
        for source in ('결과=[첫째 for 첫째,*중간,*끝 in 자료]\n','with 문맥() as (첫째,*중간,*끝): pass\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_starred_collection_literals(self):
        source='기본 = [2, 3]\n목록 = [1, *기본, 4]\n튜플 = (0, *기본)\n집합 = {1, *기본, 4}\n결과 = (목록, 튜플, 집합)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],([1,2,3,4],(0,2,3),{1,2,3,4}))

    def test_collection_unpack_fails_before_later_expression_evaluation(self):
        source='''
기록=[]
데프 표시(이름,값): 기록.append(이름); 리턴 값
데프 검사(함수):
    트라이: 함수()
    익셉트 타입에러: 패스
검사(람다: [*표시("목록",42),표시("후",1)])
검사(람다: (*표시("튜플",42),표시("후",1)))
검사(람다: {*표시("집합",42),표시("후",1)})
검사(람다: {**표시("딕트",42),"키":표시("후",1)})
결과=기록
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["목록","튜플","집합","딕트"])

    def test_dictionary_unpack_requires_mapping_not_pair_iterable(self):
        with self.assertRaisesRegex(TypeError,"not a mapping"):
            VM().run(compile_source('결과={**[("키",42)]}\n'))

    def test_set_and_dict_insert_each_item_before_later_expressions(self):
        events=[]
        class HashBomb:
            def __hash__(self): events.append("해시"); raise TypeError("해시 실패")
        source='''
데프 표시(이름,값): 기록.append(이름); 리턴 값
트라이: {표시("집합항목",폭탄), 표시("집합후",1)}
익셉트 타입에러: 패스
기록.append("구분")
트라이: {표시("딕트키",폭탄): 표시("딕트값",1), 표시("딕트후",2): 3}
익셉트 타입에러: 패스
'''
        vm=VM(); vm.globals.update({"기록":events,"폭탄":HashBomb()}); vm.run(compile_source(source))
        self.assertEqual(events,["집합항목","해시","구분","딕트키","딕트값","해시"])

    def test_dictionary_unpacking_respects_source_order(self):
        source='기본 = {"a": 1, "b": 2}\n추가 = {"b": 3, "c": 4}\n결과 = {**기본, "a": 9, **추가}\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],{"a":9,"b":3,"c":4})
    def test_tuple_list_and_nested_unpacking(self):
        source='가, [나, (다, 라)] = [1, [2, [3, 4]]]\n결과 = (가, 나, 다, 라)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(1,2,3,4))

    def test_unpack_length_error(self):
        with self.assertRaisesRegex(ValueError,"not enough values to unpack"):
            VM().run(compile_source('가, 나 = [1]\n'))

    def test_exact_unpack_stops_after_one_surplus_item(self):
        class Tracking:
            def __init__(self): self.value=0; self.calls=0
            def __iter__(self): return self
            def __next__(self):
                self.calls+=1
                if self.value>=10: raise StopIteration
                result=self.value; self.value+=1; return result
        source=Tracking(); vm=VM(); vm.globals["자료"]=source
        with self.assertRaisesRegex(ValueError,"too many values to unpack"):
            vm.run(compile_source('가, 나 = 자료\n'))
        self.assertEqual(source.calls,3)

    def test_for_target_unpack_uses_same_value_errors_and_consumption(self):
        class Tracking:
            def __init__(self): self.value=0; self.calls=0
            def __iter__(self): return self
            def __next__(self): self.calls+=1; self.value+=1; return self.value
        item=Tracking(); vm=VM(); vm.globals["자료"]=[item]
        with self.assertRaisesRegex(ValueError,"too many values to unpack"):
            vm.run(compile_source('포 (가, 나) 인 자료: 패스\n'))
        self.assertEqual(item.calls,3)

    def test_starred_unpacking(self):
        source='첫째, *가운데, 마지막 = 레인지(6)\n결과 = (첫째, 가운데, 마지막)\n'
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(0,[1,2,3,4],5))
