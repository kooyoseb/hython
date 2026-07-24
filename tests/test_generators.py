import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.vm import HythonGenerator,VM

class GeneratorTests(unittest.TestCase):
    def test_stop_iteration_escaping_generator_becomes_runtime_error(self):
        source='''
def 직접():
    if False: yield
    raise StopIteration("끝")
def 중단(): raise StopIteration("간접")
def 간접():
    if False: yield
    중단()
결과=[]
for 생성 in (직접,간접):
    try: next(생성())
    except BaseException as 오류: 결과.append((type(오류).__name__,type(오류.__cause__).__name__))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[('RuntimeError','StopIteration'),('RuntimeError','StopIteration')])
    def test_yield_from_requires_one_expression_but_accepts_parenthesized_tuple(self):
        with self.assertRaises(SyntaxError): compile_source('def 생성(): yield from 첫째,둘째\n')
        with self.assertRaises(SyntaxError): compile_source('def 생성(): yield from\n')
        with self.assertRaises(SyntaxError): compile_source('def 생성(): 결과=(yield from)\n')
        vm=VM(); vm.run(compile_source('def 생성(): yield from (1,2)\n결과=list(생성())\n'))
        self.assertEqual(vm.globals["결과"],[1,2])
    def test_generator_introspection_attributes(self):
        values=self.run_source('데프 생성():\n    일드 42\n반복=생성()\n')
        generator=values["반복"]
        self.assertEqual(generator.__name__,"생성"); self.assertEqual(generator.__qualname__,"생성")
        self.assertEqual(generator.gi_code.name,"생성"); self.assertIs(generator.gi_frame.f_locals,generator.local)
        self.assertFalse(generator.gi_running); self.assertFalse(generator.gi_suspended); self.assertIsNone(generator.gi_yieldfrom)
        self.assertEqual(next(generator),42)
        self.assertTrue(generator.gi_suspended)
        with self.assertRaises(StopIteration): next(generator)
        self.assertIsNone(generator.gi_frame); self.assertFalse(generator.gi_suspended)
    def run_source(self,source):
        vm=VM(); vm.run(loads(dumps(compile_source(source)))); return vm.globals

    def test_generator_is_lazy_and_resumable(self):
        source='기록 = []\n데프 생성():\n    기록.append("시작")\n    일드 1\n    기록.append("중간")\n    일드 2\n생성기 = 생성()\n호출전 = 렌(기록)\n첫째 = 넥스트(생성기)\n호출후 = 렌(기록)\n둘째 = 넥스트(생성기)\n결과 = (호출전, 첫째, 호출후, 둘째, 기록)\n'
        values=self.run_source(source)
        self.assertIsInstance(values["생성기"],HythonGenerator)
        self.assertEqual(values["결과"],(0,1,1,2,["시작","중간"]))

    def test_yield_from_and_loop(self):
        source='데프 생성(끝):\n    일드 -1\n    일드 프롬 레인지(끝)\n    포 값 인 레인지(끝, 끝 + 2):\n        일드 값\n결과 = 리스트(생성(3))\n'
        self.assertEqual(self.run_source(source)["결과"],[-1,0,1,2,3,4])

    def test_yield_from_forwards_send_and_captures_return_value(self):
        source='데프 안쪽():\n    받은값=(일드 "준비")\n    일드 받은값 * 2\n    리턴 42\n데프 바깥():\n    반환값=(일드 프롬 안쪽())\n    일드 반환값\n생성기=바깥()\n'
        generator=self.run_source(source)["생성기"]
        self.assertEqual(next(generator),"준비")
        self.assertEqual(generator.send(21),42)
        self.assertEqual(next(generator),42)
        with self.assertRaises(StopIteration): next(generator)

    def test_yield_from_rejects_send_to_plain_iterator(self):
        generator=self.run_source('데프 생성():\n    일드 프롬 [1, 2]\n결과=생성()\n')["결과"]
        self.assertEqual(next(generator),1)
        with self.assertRaises(AttributeError): generator.send(42)

    def test_yield_from_close_closes_delegate(self):
        events=[]
        def delegate():
            try: yield 1
            finally: events.append("closed")
        function=self.run_source('데프 생성(대상):\n    일드 프롬 대상\n')["생성"]
        generator=function(delegate()); self.assertEqual(next(generator),1); generator.close()
        self.assertEqual(events,["closed"])

    def test_yield_from_close_uses_delegate_close_not_throw(self):
        events=[]
        class Delegate:
            def __iter__(self): return self
            def __next__(self): return 1
            def close(self): events.append("close")
            def throw(self,*args): events.append("throw"); return 2
        function=self.run_source('데프 생성(대상):\n 일드 프롬 대상\n')["생성"]
        generator=function(Delegate()); self.assertEqual(next(generator),1)
        self.assertIsNone(generator.close()); self.assertEqual(events,["close"])

    def test_send_value_back_into_yield_expression(self):
        source='데프 생성():\n    받은값 = (일드 "준비")\n    일드 받은값 * 2\n생성기 = 생성()\n첫째 = 넥스트(생성기)\n둘째 = 생성기.send(21)\n결과 = (첫째, 둘째)\n'
        self.assertEqual(self.run_source(source)["결과"],("준비",42))

    def test_yield_expression_alone_marks_function_as_generator(self):
        values=self.run_source('데프 생성():\n    받은값=(일드 1)\n    리턴 받은값\n결과=생성()\n')
        generator=values["결과"]
        self.assertEqual(next(generator),1)
        with self.assertRaises(StopIteration) as stopped: generator.send(42)
        self.assertEqual(stopped.exception.value,42)

    def test_send_before_start_is_rejected(self):
        generator=self.run_source('데프 생성():\n    일드 1\n결과 = 생성()\n')["결과"]
        with self.assertRaises(TypeError): generator.send(1)

    def test_close_marks_generator_exhausted(self):
        generator=self.run_source('데프 생성():\n    일드 1\n    일드 2\n결과 = 생성()\n')["결과"]
        generator.close()
        with self.assertRaises(StopIteration): next(generator)

    def test_close_injects_generator_exit_and_runs_finally(self):
        values=self.run_source('기록=[]\n데프 생성():\n 트라이: 일드 1\n 파이널리: 기록.append("정리")\n결과=생성()\n')
        generator=values["결과"]; self.assertEqual(next(generator),1)
        self.assertIsNone(generator.close())
        self.assertEqual(values["기록"],["정리"])
        with self.assertRaises(StopIteration): next(generator)

    def test_close_returns_generator_return_value(self):
        caught=self.run_source('데프 생성():\n    트라이: 일드 1\n    익셉트 제너레이터엑시트: 리턴 42\n결과=생성()\n')["결과"]
        self.assertEqual(next(caught),1); self.assertEqual(caught.close(),42)
        finalized=self.run_source('데프 생성():\n    트라이: 일드 1\n    파이널리: 리턴 43\n결과=생성()\n')["결과"]
        self.assertEqual(next(finalized),1); self.assertEqual(finalized.close(),43)

    def test_close_rejects_generator_that_yields_during_generator_exit(self):
        generator=self.run_source('데프 생성():\n 트라이: 일드 1\n 파이널리: 일드 2\n결과=생성()\n')["결과"]
        self.assertEqual(next(generator),1)
        with self.assertRaisesRegex(RuntimeError,"ignored GeneratorExit"): generator.close()
        with self.assertRaises(StopIteration): next(generator)

    def test_throw_is_forwarded_to_yield_from_delegate(self):
        def delegate():
            try:
                yield 1
            except ValueError:
                yield 99
        values=self.run_source('데프 생성(대상):\n    일드 프롬 대상\n')
        generator=values["생성"](delegate())
        self.assertEqual(next(generator),1)
        self.assertEqual(generator.throw(ValueError),99)

    def test_try_except_inside_generator_catches_throw(self):
        source='\n'.join([
            '데프 생성():',
            '    트라이:',
            '        일드 1',
            '    익셉트 밸류에러:',
            '        일드 99',
            '결과 = 생성()',
            ''
        ])
        generator=self.run_source(source)["결과"]
        self.assertEqual(next(generator),1)
        self.assertEqual(generator.throw(ValueError),99)
        with self.assertRaises(StopIteration): next(generator)

    def test_generator_try_else_finally_preserves_yields(self):
        source='\n'.join([
            '데프 생성():',
            '    트라이:',
            '        일드 1',
            '    익셉트 익셉션:',
            '        일드 99',
            '    엘스:',
            '        일드 2',
            '    파이널리:',
            '        일드 3',
            '결과 = 리스트(생성())',
            ''
        ])
        self.assertEqual(self.run_source(source)["결과"],[1,2,3])

    def test_return_in_try_runs_finally_and_preserves_value(self):
        source='\n'.join([
            '기록 = []',
            '데프 생성():',
            '    트라이:',
            '        일드 1',
            '        리턴 42',
            '    파이널리:',
            '        기록.append("종료")',
            '생성기 = 생성()',
            '첫째 = 넥스트(생성기)',
            ''
        ])
        values=self.run_source(source); generator=values["생성기"]
        with self.assertRaises(StopIteration) as stopped: next(generator)
        self.assertEqual(stopped.exception.value,42)
        self.assertEqual(values["기록"],["종료"])

    def test_break_and_continue_cross_generator_finally(self):
        source='\n'.join([
            '데프 생성():',
            '    포 값 인 레인지(4):',
            '        트라이:',
            '            이프 값 == 1:',
            '                컨티뉴',
            '            이프 값 == 3:',
            '                브레이크',
            '            일드 값',
            '        파이널리:',
            '            일드 값 + 10',
            '결과 = 리스트(생성())',
            ''
        ])
        self.assertEqual(self.run_source(source)["결과"],[0,10,11,2,12,13])

    def test_rich_expressions_and_unpacking_inside_generator(self):
        source='\n'.join([
            '데프 생성():',
            '    첫째, *나머지 = [1, 2, 3]',
            '    자료 = {"값": 첫째 | 4, "나머지": 나머지[0:2]}',
            '    일드 f"{\uc790\ub8cc[\'\uac12\']}:{\uc790\ub8cc[\'\ub098\uba38\uc9c0\']}"',
            '결과 = 넥스트(생성())',
            ''
        ])
        self.assertEqual(self.run_source(source)["결과"],"5:[2, 3]")

    def test_with_inside_generator_spans_yield(self):
        events=[]
        class Manager:
            def __enter__(self): events.append("enter"); return 7
            def __exit__(self,*exc): events.append("exit")
        values=self.run_source('데프 생성(관리자):\n    위드 관리자 애즈 값:\n        일드 값\n')
        generator=values["생성"](Manager())
        self.assertEqual(next(generator),7); self.assertEqual(events,["enter"])
        with self.assertRaises(StopIteration): next(generator)
        self.assertEqual(events,["enter","exit"])

    def test_with_can_suppress_throw_inside_generator(self):
        events=[]
        class Manager:
            def __enter__(self): return self
            def __exit__(self,kind,error,traceback): events.append(kind); return kind is ValueError
        values=self.run_source('데프 생성(관리자):\n    위드 관리자:\n        일드 1\n    일드 2\n')
        generator=values["생성"](Manager()); self.assertEqual(next(generator),1)
        self.assertEqual(generator.throw(ValueError),2)
        self.assertEqual(events,[ValueError])

    def test_nested_definition_extended_call_and_comprehension(self):
        source='\n'.join([
            '데프 생성(기준):',
            '    데프 합계(*값들, 배수=1):',
            '        리턴 썸(값들) * 배수 + 기준',
            '    자료 = [값 * 2 포 값 인 레인지(5) 이프 값 % 2 == 0]',
            '    일드 합계(*자료, **{"배수": 3})',
            '결과 = 넥스트(생성(1))',
            ''
        ])
        self.assertEqual(self.run_source(source)["결과"],37)
