import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.translator import compile_hython
from hython.vm import VM

class ComprehensionTests(unittest.TestCase):
    def test_named_expression_is_rejected_inside_nested_scope_in_iterable(self):
        with self.assertRaises(SyntaxError):
            compile_source('결과=[값 for 값 in (lambda: (다른값 := 1))()]\n')

    def test_named_expression_inside_element_lambda_remains_valid(self):
        compile_source('결과=[(lambda: (다른값 := 값)) for 값 in 자료]\n')
    def test_rejects_illegal_named_expression_and_yield_contexts(self):
        invalid=[
            "결과=[(값 := 값) 포 값 인 레인지(3)]\n",
            "결과=[값 포 값 인 (자료 := 레인지(3))]\n",
            "클래스 대상:\n    결과=[(바깥 := 값) 포 값 인 레인지(3)]\n",
            "데프 생성():\n    리턴 [(일드 값) 포 값 인 레인지(3)]\n",
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_generator_expression_is_lazy(self):
        source='\n'.join([
            '기록 = []',
            '데프 기록하기(값):',
            '    기록.append(값)',
            '    리턴 값 * 2',
            '생성기 = (기록하기(값) 포 값 인 레인지(3))',
            '전 = 렌(기록)',
            '첫째 = 넥스트(생성기)',
            '후 = 렌(기록)',
            '결과 = (전, 첫째, 후)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(0,0,1))

    def test_generator_expression_reads_live_outer_bindings(self):
        source='값=1\n생성기=(값 포 _ 인 [0,1])\n값=2\n첫째=넥스트(생성기)\n값=3\n둘째=넥스트(생성기)\n결과=(첫째,둘째)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(2,3)); self.assertNotIn("_",vm.globals)

    def test_generator_expression_eagerly_evaluates_outer_iterable_only(self):
        source='기록=[]\n데프 바깥():\n    기록.append("바깥")\n    리턴 [1, 2]\n데프 안쪽(값):\n    기록.append(("안쪽", 값))\n    리턴 [값]\n생성기=(쌍 포 값 인 바깥() 포 쌍 인 안쪽(값))\n생성직후=리스트(기록)\n첫째=넥스트(생성기)\n결과=(생성직후, 첫째, 기록)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(["바깥"],1,["바깥",("안쪽",1)]))

    def test_generator_expression_outer_iter_error_is_immediate(self):
        vm=VM()
        with self.assertRaises(TypeError):
            vm.run(compile_source('생성기=(값 포 값 인 42)\n'))

    def test_destructuring_targets_in_for_and_comprehension(self):
        source='\n'.join([
            '합계 = 0',
            '포 (가, 나) 인 [(1, 2), (3, 4)]:',
            '    합계 += 가 + 나',
            '자료 = [가 * 나 포 가, 나 인 [(2, 3), (4, 5)]]',
            '별표 = [(첫째, 나머지) 포 첫째, *나머지 인 [(1, 2, 3)]]',
            '결과 = (합계, 자료, 별표)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],(10,[6,20],[(1,[2,3])]))

    def test_named_expression_binds_containing_scope(self):
        source='목록 = [(바깥 := 값 * 2) 포 값 인 레인지(3)]\n마지막 = 바깥\n생성기 = ((지연 := 값) 포 값 인 레인지(2))\n첫째 = 넥스트(생성기)\n결과 = (목록, 마지막, 첫째, 지연)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],([0,2,4],4,0,0)); self.assertNotIn("값",vm.globals)

    def test_generator_filter_named_expression_publishes_without_yield(self):
        source='생성기=(값 포 값 인 [0] 이프 (마지막 := 값) > 0)\n자료=리스트(생성기)\n결과=(자료, 마지막)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],([],0))

    def test_comprehension_named_expression_is_visible_during_evaluation(self):
        source='현재=-1\n데프 읽기():\n    리턴 현재\n결과=[읽기() 포 값 인 [42] 이프 (현재 := 값) > 0]\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[42])
    def compare(self,source,name="결과"):
        vm=VM(); vm.run(loads(dumps(compile_source(source))))
        compatible={}; exec(compile_hython(source),compatible)
        self.assertEqual(vm.globals[name],compatible[name])
        return vm.globals

    def test_list_comprehension_with_filters(self):
        values=self.compare('바깥 = 99\n결과 = [수 * 수 포 수 인 레인지(20) 이프 수 % 2 == 0 이프 수 > 5]\n')
        self.assertNotIn("수",values)

    def test_set_comprehension(self):
        self.compare('결과 = {수 % 3 포 수 인 레인지(10)}\n')

    def test_dict_comprehension(self):
        self.compare('결과 = {수: 수 ** 2 포 수 인 레인지(6) 이프 수 != 3}\n')

    def test_tuple_and_set_literals(self):
        self.compare('결과 = ((1, 2, 3), {1, 2, 2})\n')

    def test_nested_for_clauses_and_scoped_iterable(self):
        self.compare('결과 = [(행, 열) 포 행 인 레인지(3) 이프 행 > 0 포 열 인 레인지(행 + 1) 이프 열 % 2 == 0]\n')
