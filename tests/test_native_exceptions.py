import unittest
from hython.bytecode import VERSION, dumps, loads
from hython.compiler import compile_source
from hython.vm import VM

class NativeExceptionTests(unittest.TestCase):
    def test_descriptor_implicit_hython_call_inherits_active_exception(self):
        source='''
클래스 설명자:
    데프 __get__(셀프,객체,소유자): 레이즈
클래스 대상: 값=설명자()
트라이: 레이즈 밸류에러("active")
익셉트 밸류에러:
    트라이: 대상().값
    익셉트 밸류에러 애즈 오류: 결과=스트링(오류)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],"active")

    def test_operator_implicit_hython_call_inherits_active_exception(self):
        source='''
클래스 조건:
    데프 __bool__(셀프): 레이즈
트라이: 레이즈 밸류에러("operator-active")
익셉트 밸류에러:
    트라이:
        이프 조건(): 패스
    익셉트 밸류에러 애즈 오류: 결과=스트링(오류)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],"operator-active")

    def test_python314_unparenthesized_multiple_exception_types(self):
        source='''
결과=[]
for 오류 in (ValueError("값"), TypeError("타입")):
    try: raise 오류
    except ValueError, TypeError: 결과.append(type(오류).__name__)
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],["ValueError","TypeError"])

    def test_unparenthesized_multiple_except_star_types_compile(self):
        compile_source('try: pass\nexcept* ValueError, TypeError: pass\n')

    def test_orphaned_or_misordered_exception_clauses_are_rejected(self):
        invalid=(
            'try: pass\nelse: pass\nfinally: pass\n',
            'try: pass\nfinally: pass\nelse: pass\n',
            'try: pass\nexcept: pass\nelse: pass\nexcept: pass\n',
            'try: pass\nfinally: pass\nfinally: pass\n',
        )
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_sys_exception_and_exc_info_observe_hbc_handler_exception(self):
        source='인폴트 sys\n트라이: 레이즈 밸류에러("값")\n익셉트 밸류에러 애즈 오류:\n    결과=(sys.exception() 이즈 오류, sys.exc_info()[0] 이즈 밸류에러, sys.exc_info()[1] 이즈 오류)\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True,True))

    def test_sys_exception_observes_matched_except_star_subgroup(self):
        source='인폴트 sys\n결과=[]\n트라이:\n    레이즈 익셉션그룹("묶음",[밸류에러("값"),타입에러("형식")])\n익셉트* 밸류에러 애즈 일부:\n    결과.append((sys.exception() 이즈 일부,sys.exc_info()[1] 이즈 일부,렌(일부.exceptions)))\n익셉트* 타입에러:\n    패스\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[(True,True,1)])

    def test_native_callback_observes_matched_except_star_subgroup(self):
        import sys
        def observe(): return sys.exception()
        source='결과=[]\n트라이:\n    레이즈 익셉션그룹("묶음",[밸류에러(),타입에러()])\n익셉트* 밸류에러 애즈 일부:\n    결과.append(관찰() 이즈 일부)\n익셉트* 타입에러: 패스\n'
        vm=VM(); vm.globals["관찰"]=observe; vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[True])

    def test_sys_exception_is_cleared_after_handler(self):
        source='인폴트 sys\n트라이: 레이즈 밸류에러()\n익셉트 밸류에러: 패스\n결과=(sys.exception(),sys.exc_info())\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(None,(None,None,None)))

    def test_sys_exception_state_survives_generator_suspension(self):
        source='인폴트 sys\n데프 생성():\n    트라이: 레이즈 밸류에러("값")\n    익셉트 밸류에러 애즈 오류:\n        일드 sys.exception() 이즈 오류\n        일드 sys.exc_info()[1] 이즈 오류\n흐름=생성()\n결과=(넥스트(흐름),넥스트(흐름))\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(True,True))

    def test_interleaved_generators_keep_independent_active_exceptions(self):
        source='데프 생성(이름):\n    트라이:\n        레이즈 밸류에러(이름)\n    익셉트 밸류에러:\n        일드 이름\n        레이즈\n첫째=생성("첫째")\n둘째=생성("둘째")\n'
        vm=VM(); vm.run(compile_source(source)); first=vm.globals["첫째"]; second=vm.globals["둘째"]
        self.assertEqual((next(first),next(second)),("첫째","둘째"))
        with self.assertRaisesRegex(ValueError,"첫째"): next(first)
        with self.assertRaisesRegex(ValueError,"둘째"): next(second)

    def test_called_function_inherits_callers_active_exception(self):
        source='데프 안쪽(): 레이즈\n데프 바깥():\n    트라이: 레이즈 밸류에러("바깥")\n    익셉트 밸류에러: 안쪽()\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaisesRegex(ValueError,"바깥"): vm.globals["바깥"]()

    def test_immediately_awaited_coroutine_inherits_active_exception(self):
        import asyncio
        source='어싱크 데프 안쪽(): 레이즈\n어싱크 데프 바깥():\n    트라이: 레이즈 밸류에러("바깥")\n    익셉트 밸류에러: 어웨이트 안쪽()\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaisesRegex(ValueError,"바깥"): asyncio.run(vm.globals["바깥"]())

    def test_coroutine_executed_later_does_not_capture_creation_exception(self):
        import asyncio
        source='어싱크 데프 안쪽(): 레이즈\n어싱크 데프 생성():\n    트라이: 레이즈 밸류에러("생성")\n    익셉트 밸류에러: 리턴 안쪽()\n'
        vm=VM(); vm.run(compile_source(source)); coroutine=asyncio.run(vm.globals["생성"]())
        with self.assertRaises(RuntimeError): asyncio.run(coroutine)

    def test_generator_resumed_in_handler_inherits_active_exception(self):
        source='데프 생성():\n    일드 넌\n    레이즈\n데프 실행():\n    흐름=생성()\n    넥스트(흐름)\n    트라이: 레이즈 밸류에러("호출자")\n    익셉트 밸류에러: 넥스트(흐름)\n'
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaisesRegex(ValueError,"호출자"): vm.globals["실행"]()

    def test_external_generator_resume_temporarily_inherits_python_exception(self):
        vm=VM(); vm.run(compile_source('데프 즉시():\n    이프 폴스: 일드 넌\n    레이즈\n데프 지연():\n    일드 1\n    레이즈\n'))
        try:
            raise ValueError("external")
        except ValueError:
            with self.assertRaisesRegex(ValueError,"external"): next(vm.globals["즉시"]())
            delayed=vm.globals["지연"](); self.assertEqual(next(delayed),1)
        with self.assertRaisesRegex(RuntimeError,"No active exception"): next(delayed)

    def test_yield_from_delegate_inherits_external_python_exception(self):
        vm=VM(); vm.run(compile_source('데프 안쪽():\n    이프 폴스: 일드 넌\n    레이즈\n데프 바깥():\n    일드 프롬 안쪽()\n'))
        try:
            raise ValueError("delegated")
        except ValueError:
            with self.assertRaisesRegex(ValueError,"delegated"): next(vm.globals["바깥"]())

    def test_async_generator_external_exception_is_temporary_across_yield(self):
        import asyncio
        vm=VM(); vm.run(compile_source('어싱크 데프 즉시():\n    이프 폴스: 일드 넌\n    레이즈\n어싱크 데프 지연():\n    일드 1\n    레이즈\n'))
        async def exercise():
            try:
                raise ValueError("async-active")
            except ValueError:
                with self.assertRaisesRegex(ValueError,"async-active"):
                    await anext(vm.globals["즉시"]())
                delayed=vm.globals["지연"](); self.assertEqual(await anext(delayed),1)
            with self.assertRaisesRegex(RuntimeError,"No active exception"):
                await anext(delayed)
        asyncio.run(exercise())

    def test_interleaved_coroutines_keep_independent_active_exceptions(self):
        import asyncio
        async def yield_control(): await asyncio.sleep(0)
        source='어싱크 데프 작업(이름):\n    트라이:\n        레이즈 밸류에러(이름)\n    익셉트 밸류에러:\n        어웨이트 양보()\n        레이즈\n'
        vm=VM(); vm.globals["양보"]=yield_control; vm.run(compile_source(source)); work=vm.globals["작업"]
        async def exercise(): return await asyncio.gather(work("첫째"),work("둘째"),return_exceptions=True)
        failures=asyncio.run(exercise())
        self.assertEqual([str(error) for error in failures],["첫째","둘째"])

    def test_rejects_invalid_bare_and_star_exception_handlers(self):
        invalid=[
            "트라이:\n    패스\n익셉트:\n    패스\n익셉트 익셉션:\n    패스\n",
            "트라이:\n    패스\n익셉트*:\n    패스\n",
            "데프 함수():\n    트라이:\n        패스\n    익셉트* 익셉션:\n        리턴 1\n",
        ]
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
    def test_bare_raise_reraises_active_exception(self):
        source='\n'.join([
            '결과 = ""',
            '트라이:',
            '    트라이:',
            '        레이즈 밸류에러("원본")',
            '    익셉트 밸류에러:',
            '        레이즈',
            '익셉트 밸류에러 애즈 오류:',
            '    결과 = 스트링(오류)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],"원본")

    def test_raise_from_preserves_explicit_cause(self):
        source='\n'.join([
            '결과 = ""',
            '트라이:',
            '    레이즈 타입에러("바깥") 프롬 밸류에러("원인")',
            '익셉트 타입에러 애즈 오류:',
            '    결과 = 스트링(오류.__cause__)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],"원인")

    def test_exception_chaining_attributes_match_python(self):
        source='''
결과=[]
트라이:
    레이즈 밸류에러("원본")
익셉트 밸류에러 애즈 원본:
    트라이: 레이즈 타입에러("암시")
    익셉트 타입에러 애즈 오류:
        결과.append((오류.__context__ 이즈 원본, 오류.__cause__, 오류.__suppress_context__))
    트라이: 레이즈 타입에러("명시") 프롬 키에러("원인")
    익셉트 타입에러 애즈 오류:
        결과.append((오류.__context__ 이즈 원본, 이즈인스턴스(오류.__cause__, 키에러), 오류.__suppress_context__))
    트라이: 레이즈 타입에러("억제") 프롬 넌
    익셉트 타입에러 애즈 오류:
        결과.append((오류.__context__ 이즈 원본, 오류.__cause__, 오류.__suppress_context__))
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],[(True,None,False),(True,True,True),(True,None,True)])

    def test_bare_raise_in_finally_preserves_propagating_exception(self):
        source='''
데프 동기():
    트라이: 레이즈 밸류에러("동기")
    파이널리:
        데프 다시(): 레이즈
        다시()
데프 생성기():
    트라이: 레이즈 밸류에러("생성기")
    파이널리:
        일드 1
        레이즈
어싱크 데프 비동기():
    트라이: 레이즈 밸류에러("비동기")
    파이널리: 레이즈
'''
        vm=VM(); vm.run(compile_source(source))
        with self.assertRaisesRegex(ValueError,"동기"): vm.globals["동기"]()
        stream=vm.globals["생성기"](); self.assertEqual(next(stream),1)
        with self.assertRaisesRegex(ValueError,"생성기"): next(stream)
        import asyncio
        with self.assertRaisesRegex(ValueError,"비동기"): asyncio.run(vm.globals["비동기"]())

    def test_tuple_exception_handler(self):
        source='\n'.join([
            '결과 = ""',
            '트라이:',
            '    레이즈 타입에러("형식")',
            '익셉트 (밸류에러, 타입에러) 애즈 오류:',
            '    결과 = 스트링(오류)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],"형식")

    def test_bare_except_catches_base_exception(self):
        class StopSignal(BaseException): pass
        source='결과 = 폴스\n트라이:\n    레이즈 중단신호()\n익셉트:\n    결과 = 트루\n'
        vm=VM(); vm.globals["중단신호"]=StopSignal; vm.run(compile_source(source))
        self.assertTrue(vm.globals["결과"])

    def test_invalid_exception_handler_type_raises_type_error(self):
        source='트라이:\n    레이즈 밸류에러("원본")\n익셉트 42:\n    패스\n'
        vm=VM()
        with self.assertRaises(TypeError): vm.run(compile_source(source))

    def test_except_star_wraps_naked_base_exception(self):
        class StopSignal(BaseException): pass
        source='결과 = 0\n트라이:\n    레이즈 중단신호()\n익셉트* 중단신호 애즈 묶음:\n    결과 = 렌(묶음.exceptions)\n'
        vm=VM(); vm.globals["중단신호"]=StopSignal; vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],1)

    def test_except_star_splits_exception_group(self):
        source='\n'.join([
            '기록 = []',
            '트라이:',
            '    레이즈 익셉션그룹("묶음", [밸류에러("가"), 타입에러("나"), 밸류에러("다")])',
            '익셉트* 밸류에러 애즈 오류들:',
            '    기록.append(("값", 렌(오류들.exceptions)))',
            '익셉트* 타입에러 애즈 오류들:',
            '    기록.append(("형식", 렌(오류들.exceptions)))',
            '결과 = 기록',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],[("값",2),("형식",1)])

    def test_except_star_rethrows_unmatched_subgroup(self):
        source='\n'.join([
            '결과 = 0',
            '트라이:',
            '    트라이:',
            '        레이즈 익셉션그룹("묶음", [밸류에러(), 타입에러()])',
            '    익셉트* 밸류에러:',
            '        패스',
            '익셉트 익셉션그룹 애즈 나머지:',
            '    결과 = 렌(나머지.exceptions)',
            ''
        ])
        vm=VM(); vm.run(compile_source(source)); self.assertEqual(vm.globals["결과"],1)

    def test_except_star_bare_raise_reconstructs_original_group(self):
        original=ExceptionGroup("원본",[ValueError("가"),TypeError("나")])
        vm=VM(); vm.globals["원본"]=original
        with self.assertRaises(ExceptionGroup) as caught:
            vm.run(compile_source('트라이:\n 레이즈 원본\n익셉트* 밸류에러:\n 레이즈\n'))
        self.assertIs(caught.exception,original)
        self.assertEqual([type(item) for item in caught.exception.exceptions],[ValueError,TypeError])

    def test_except_star_new_failure_keeps_unmatched_original_subgroup(self):
        original=ExceptionGroup("원본",[ValueError("가"),TypeError("나")])
        vm=VM(); vm.globals["원본"]=original
        with self.assertRaises(ExceptionGroup) as caught:
            vm.run(compile_source('트라이:\n 레이즈 원본\n익셉트* 밸류에러:\n 레이즈 런타임에러("새 오류")\n'))
        outer=caught.exception
        self.assertEqual(outer.message,"")
        self.assertIsInstance(outer.exceptions[0],RuntimeError)
        self.assertEqual(outer.exceptions[1].message,"원본")
        self.assertIsInstance(outer.exceptions[1].exceptions[0],TypeError)
    def run_source(self,source):
        vm=VM(); vm.run(loads(dumps(compile_source(source)))); return vm.globals

    def test_elif(self):
        source='값 = 2\n이프 값 == 1:\n    결과 = "하나"\n엘리프 값 == 2:\n    결과 = "둘"\n엘스:\n    결과 = "기타"\n'
        self.assertEqual(self.run_source(source)["결과"],"둘")

    def test_try_except_else_finally(self):
        source='기록 = []\n트라이:\n    기록.append("시작")\n    레이즈 밸류에러("실패")\n익셉트 밸류에러 애즈 오류:\n    기록.append(스트링(오류))\n엘스:\n    기록.append("성공")\n파이널리:\n    기록.append("정리")\n결과 = 기록\n'
        self.assertEqual(self.run_source(source)["결과"],["시작","실패","정리"])

    def test_try_else_runs_only_without_failure(self):
        source='결과 = []\n트라이:\n    결과.append("본문")\n익셉트 익셉션:\n    결과.append("예외")\n엘스:\n    결과.append("성공")\n파이널리:\n    결과.append("정리")\n'
        self.assertEqual(self.run_source(source)["결과"],["본문","성공","정리"])

    def test_hbc_v6_and_rejects_previous_instruction_set_version(self):
        self.assertEqual(VERSION,6)
        artifact=bytearray(dumps(compile_source("값=1\n"))); artifact[4]=5
        with self.assertRaisesRegex(ValueError,"지원하지 않는 HBC 버전: 5"): loads(bytes(artifact))

    def test_return_inside_try_runs_finally(self):
        source='기록 = []\n데프 함수():\n    트라이:\n        리턴 42\n    파이널리:\n        기록.append("정리")\n결과 = 함수()\n'
        values=self.run_source(source); self.assertEqual(values["결과"],42); self.assertEqual(values["기록"],["정리"])

    def test_return_inside_except(self):
        source='데프 함수():\n    트라이:\n        레이즈 밸류에러("오류")\n    익셉트 밸류에러:\n        리턴 42\n결과 = 함수()\n'
        self.assertEqual(self.run_source(source)["결과"],42)

    def test_break_and_continue_cross_try_finally(self):
        source='기록 = []\n포 값 인 레인지(6):\n    트라이:\n        이프 값 == 1:\n            컨티뉴\n        이프 값 == 4:\n            브레이크\n        기록.append(값)\n    파이널리:\n        기록.append("정리")\n결과 = 기록\n'
        self.assertEqual(self.run_source(source)["결과"],[0,"정리","정리",2,"정리",3,"정리","정리"])
