import unittest
from hython.bytecode import dumps,loads
from hython.compiler import compile_source
from hython.vm import HythonAsyncGenerator,HythonCoroutine,VM

class AsyncTests(unittest.TestCase):
    def test_stop_async_iteration_escaping_async_generator_becomes_runtime_error(self):
        source='''
async def 생성():
    if False: yield
    raise StopAsyncIteration("끝")
async def 실행():
    try: await 생성().__anext__()
    except BaseException as 오류: return type(오류).__name__,type(오류.__cause__).__name__
결과=asyncio_run(실행())
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],('RuntimeError','StopAsyncIteration'))
    def test_await_primary_binds_before_power_arithmetic_and_comparison(self):
        source='''
async def 값(): return 3
async def 계산():
    return (await 값() + 2, await 값() ** 2, await 값() < 4)
결과=asyncio_run(계산())
'''
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],(5,9,True))

    def test_await_rejects_unparenthesized_non_primary_operands(self):
        invalid=('async def 함수(): return await -값()\n','async def 함수(): return await not 값()\n','async def 함수(): return await lambda: 1\n','async def 함수(): return await await 값()\n')
        for source in invalid:
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
        compile_source('async def 함수(): return await (-값())\n')
    def test_coroutine_and_async_generator_introspection_protocols(self):
        values=self.run_source('어싱크 데프 코루틴(): 리턴 42\n어싱크 데프 생성(): 일드 1\n코루틴값=코루틴()\n생성값=생성()\n')
        coroutine=values["코루틴값"]; generator=values["생성값"]
        self.assertEqual((coroutine.__name__,coroutine.cr_code.name),("코루틴","코루틴"))
        self.assertIsNotNone(coroutine.cr_frame); self.assertFalse(coroutine.cr_running); self.assertFalse(coroutine.cr_suspended); self.assertIsNone(coroutine.cr_await)
        with self.assertRaises(StopIteration) as stopped: coroutine.send(None)
        self.assertEqual(stopped.exception.value,42); self.assertIsNone(coroutine.cr_frame); self.assertFalse(coroutine.cr_suspended)
        self.assertEqual((generator.__name__,generator.ag_code.name),("생성","생성"))
        self.assertIsNotNone(generator.ag_frame); self.assertFalse(generator.ag_running); self.assertFalse(generator.ag_suspended); self.assertIsNone(generator.ag_await)
        self.assertTrue(all(hasattr(generator,name) for name in ("asend","athrow","aclose")))

    def test_nested_generator_coroutine_and_async_generator_qualnames(self):
        values=self.run_source('데프 바깥():\n    데프 생성기(): 일드 1\n    어싱크 데프 코루틴(): 리턴 1\n    어싱크 데프 비동기생성기(): 일드 1\n    리턴 (생성기(),코루틴(),비동기생성기())\n결과=바깥()\n')
        generator,coroutine,async_generator=values["결과"]
        self.assertEqual((generator.__name__,generator.__qualname__),("생성기","바깥.<locals>.생성기"))
        self.assertEqual((coroutine.__name__,coroutine.__qualname__),("코루틴","바깥.<locals>.코루틴"))
        self.assertEqual((async_generator.__name__,async_generator.__qualname__),("비동기생성기","바깥.<locals>.비동기생성기"))
        generator.close(); coroutine.close(); __import__('asyncio').run(async_generator.aclose())

    def test_coroutine_cannot_be_reused_after_exception(self):
        coroutine=self.run_source('어싱크 데프 실패():\n    레이즈 밸류에러("실패")\n결과=실패()\n')["결과"]
        with self.assertRaises(ValueError): coroutine.send(None)
        self.assertIsNone(coroutine.cr_frame)
        for operation in (lambda:coroutine.send(None),lambda:coroutine.throw(TypeError)):
            with self.subTest(operation=operation),self.assertRaisesRegex(RuntimeError,"cannot reuse"): operation()

    def test_coroutine_cr_await_tracks_and_clears_current_awaitable(self):
        class Pause:
            def __await__(self):
                yield "paused"
                return 42
        pause=Pause()
        vm=VM(); vm.globals["대기값"]=pause
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대기):\n    리턴 어웨이트 대기\n결과=작업(대기값)\n'))))
        coroutine=vm.globals["결과"]
        self.assertEqual(coroutine.send(None),"paused")
        self.assertIs(coroutine.cr_await,pause); self.assertTrue(coroutine.cr_suspended)
        with self.assertRaises(StopIteration) as stopped: coroutine.send(None)
        self.assertEqual(stopped.exception.value,42)
        self.assertIsNone(coroutine.cr_await); self.assertFalse(coroutine.cr_suspended)

    def test_async_generator_suspended_lifecycle(self):
        generator=self.run_source('어싱크 데프 생성():\n    일드 42\n결과=생성()\n')["결과"]
        self.assertFalse(generator.ag_suspended)
        request=generator.__anext__()
        with self.assertRaises(StopIteration) as yielded: request.send(None)
        self.assertEqual(yielded.exception.value,42); self.assertTrue(generator.ag_suspended)
        request=generator.__anext__()
        with self.assertRaises(StopAsyncIteration): request.send(None)
        self.assertFalse(generator.ag_suspended); self.assertIsNone(generator.ag_frame)

    def test_await_rejects_non_iterator_and_clears_introspection(self):
        class BadAwaitable:
            def __await__(self): return 42
        vm=VM(); vm.globals["대기값"]=BadAwaitable()
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대기):\n    리턴 어웨이트 대기\n결과=작업(대기값)\n'))))
        coroutine=vm.globals["결과"]
        with self.assertRaisesRegex(TypeError,"__await__.*non-iterator"): coroutine.send(None)
        self.assertIsNone(coroutine.cr_await)

    def test_coroutine_close_while_awaiting_clears_cr_await(self):
        class Pause:
            def __await__(self):
                yield "paused"
        pause=Pause(); vm=VM(); vm.globals["대기값"]=pause
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대기):\n    어웨이트 대기\n결과=작업(대기값)\n'))))
        coroutine=vm.globals["결과"]
        self.assertEqual(coroutine.send(None),"paused"); self.assertIs(coroutine.cr_await,pause)
        coroutine.close()
        self.assertIsNone(coroutine.cr_await); self.assertIsNone(coroutine.cr_frame)

    def test_async_generator_ag_await_preserves_falsey_awaitable(self):
        class FalsePause:
            def __bool__(self): return False
            def __await__(self):
                yield "paused"
                return 7
        pause=FalsePause(); vm=VM(); vm.globals["대기값"]=pause
        vm.run(loads(dumps(compile_source('어싱크 데프 생성(대기):\n    값=어웨이트 대기\n    일드 값\n결과=생성(대기값)\n'))))
        generator=vm.globals["결과"]; request=generator.__anext__()
        self.assertEqual(request.send(None),"paused")
        self.assertIs(generator.ag_await,pause)
        with self.assertRaises(StopIteration) as stopped: request.send(None)
        self.assertEqual(stopped.exception.value,7); self.assertIsNone(generator.ag_await)

    def test_coroutine_cr_await_tracks_implicit_async_for_await(self):
        class Pause:
            def __await__(self):
                yield "next-paused"
                raise StopAsyncIteration
        pause=Pause()
        class Stream:
            def __aiter__(self): return self
            def __anext__(self): return pause
        vm=VM(); vm.globals["흐름"]=Stream()
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대상):\n    어싱크 포 값 인 대상:\n        패스\n결과=작업(흐름)\n'))))
        coroutine=vm.globals["결과"]
        self.assertEqual(coroutine.send(None),"next-paused"); self.assertIs(coroutine.cr_await,pause)
        with self.assertRaises(StopIteration): coroutine.send(None)
        self.assertIsNone(coroutine.cr_await)

    def test_coroutine_cr_await_tracks_implicit_async_with_enter_and_exit(self):
        class Pause:
            def __init__(self,label,result=None): self.label=label; self.result=result
            def __await__(self):
                yield self.label
                return self.result
        entered=Pause("enter-paused",42); exited=Pause("exit-paused",False)
        class Manager:
            def __aenter__(self): return entered
            def __aexit__(self,*exc): return exited
        vm=VM(); vm.globals["문맥"]=Manager()
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대상):\n    어싱크 위드 대상 애즈 값:\n        패스\n    리턴 값\n결과=작업(문맥)\n'))))
        coroutine=vm.globals["결과"]
        self.assertEqual(coroutine.send(None),"enter-paused"); self.assertIs(coroutine.cr_await,entered)
        self.assertEqual(coroutine.send(None),"exit-paused"); self.assertIs(coroutine.cr_await,exited)
        with self.assertRaises(StopIteration) as stopped: coroutine.send(None)
        self.assertEqual(stopped.exception.value,42); self.assertIsNone(coroutine.cr_await)

    def test_coroutine_cr_await_tracks_async_comprehension_iteration(self):
        class Pause:
            def __await__(self):
                yield "comprehension-paused"
                return 42
        pause=Pause()
        class Stream:
            def __init__(self): self.done=False
            def __aiter__(self): return self
            def __anext__(self):
                if self.done: raise StopAsyncIteration
                self.done=True; return pause
        vm=VM(); vm.globals["흐름"]=Stream()
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대상):\n    리턴 [값 어싱크 포 값 인 대상]\n결과=작업(흐름)\n'))))
        coroutine=vm.globals["결과"]
        self.assertEqual(coroutine.send(None),"comprehension-paused")
        self.assertIs(coroutine.cr_await,pause)
        with self.assertRaises(StopIteration) as stopped: coroutine.send(None)
        self.assertEqual(stopped.exception.value,[42]); self.assertIsNone(coroutine.cr_await)

    def test_coroutine_cr_await_tracks_await_inside_comprehension_filter(self):
        class Pause:
            def __await__(self):
                yield "filter-paused"
                return True
        pause=Pause()
        class Stream:
            def __init__(self): self.done=False
            def __aiter__(self): return self
            async def __anext__(self):
                if self.done: raise StopAsyncIteration
                self.done=True; return 42
        def predicate(_): return pause
        vm=VM(); vm.globals.update({"흐름":Stream(),"검사":predicate})
        vm.run(loads(dumps(compile_source('어싱크 데프 작업(대상, 조건):\n    리턴 [값 어싱크 포 값 인 대상 이프 어웨이트 조건(값)]\n결과=작업(흐름, 검사)\n'))))
        coroutine=vm.globals["결과"]
        self.assertEqual(coroutine.send(None),"filter-paused")
        self.assertIs(coroutine.cr_await,pause)
        with self.assertRaises(StopIteration) as stopped: coroutine.send(None)
        self.assertEqual(stopped.exception.value,[42]); self.assertIsNone(coroutine.cr_await)

    def test_coroutine_throw_and_close_reject_running_reentry(self):
        coroutine=self.run_source('어싱크 데프 작업():\n    리턴 1\n결과=작업()\n')["결과"]
        coroutine._running=True
        try:
            with self.assertRaisesRegex(ValueError,"already executing"): coroutine.throw(ValueError)
            with self.assertRaisesRegex(ValueError,"already executing"): coroutine.close()
        finally: coroutine._running=False; coroutine.close()

    def test_coroutine_await_iterator_close_updates_wrapper_state(self):
        coroutine=self.run_source('어싱크 데프 작업():\n    리턴 42\n결과=작업()\n')["결과"]
        iterator=coroutine.__await__()
        self.assertIs(iter(iterator),iterator); self.assertFalse(coroutine.cr_suspended)
        iterator.close()
        self.assertIsNone(coroutine.cr_frame); self.assertFalse(coroutine.cr_suspended)
        with self.assertRaisesRegex(RuntimeError,"cannot reuse"): coroutine.send(None)
    def run_source(self,source):
        vm=VM(); vm.run(loads(dumps(compile_source(source)))); return vm.globals

    def test_async_function_returns_real_awaitable(self):
        source='어싱크 데프 더하기(가, 나):\n    리턴 가 + 나\n코루틴 = 더하기(20, 22)\n결과 = 어싱크실행(코루틴)\n'
        values=self.run_source(source)
        self.assertIsInstance(values["코루틴"],HythonCoroutine)
        self.assertEqual(values["결과"],42)
        self.assertIsNone(values["코루틴"].cr_frame); self.assertFalse(values["코루틴"].cr_suspended)
        with self.assertRaisesRegex(RuntimeError,"cannot reuse"): values["코루틴"].send(None)

    def test_await_nested_coroutine_resumes_frame(self):
        source='기록 = []\n어싱크 데프 내부(값):\n    기록.append("내부")\n    리턴 값 * 2\n어싱크 데프 외부():\n    기록.append("전")\n    값 = 어웨이트 내부(21)\n    기록.append("후")\n    리턴 값\n결과 = 어싱크실행(외부())\n'
        values=self.run_source(source)
        self.assertEqual(values["결과"],42)
        self.assertEqual(values["기록"],["전","내부","후"])

    def test_async_for_protocol(self):
        source='클래스 비동기범위:\n    데프 __init__(셀프, 끝):\n        셀프.현재 = 0\n        셀프.끝 = 끝\n    데프 __aiter__(셀프):\n        리턴 셀프\n    어싱크 데프 __anext__(셀프):\n        이프 셀프.현재 >= 셀프.끝:\n            레이즈 스톱어싱크이터레이션()\n        값 = 셀프.현재\n        셀프.현재 = 셀프.현재 + 1\n        리턴 값\n어싱크 데프 메인():\n    결과 = []\n    어싱크 포 값 인 비동기범위(4):\n        결과.append(값 * 2)\n    리턴 결과\n결과 = 어싱크실행(메인())\n'
        self.assertEqual(self.run_source(source)["결과"],[0,2,4,6])

    def test_async_for_break_continue_and_else(self):
        source='클래스 비동기범위:\n    데프 __init__(셀프, 끝): 셀프.현재 = 0; 셀프.끝 = 끝\n    데프 __aiter__(셀프): 리턴 셀프\n    어싱크 데프 __anext__(셀프):\n        이프 셀프.현재 >= 셀프.끝: 레이즈 스톱어싱크이터레이션()\n        값 = 셀프.현재; 셀프.현재 += 1; 리턴 값\n어싱크 데프 정상():\n    결과=[]\n    어싱크 포 값 인 비동기범위(4):\n        이프 값 == 1: 컨티뉴\n        결과.append(값)\n    엘스: 결과.append("완료")\n    리턴 결과\n어싱크 데프 중단():\n    결과=[]\n    어싱크 포 값 인 비동기범위(4):\n        이프 값 == 2: 브레이크\n        결과.append(값)\n    엘스: 결과.append("실행안됨")\n    리턴 결과\n결과 = (어싱크실행(정상()), 어싱크실행(중단()))\n'
        self.assertEqual(self.run_source(source)["결과"],([0,2,3,"완료"],[0,1]))

    def test_async_context_manager(self):
        source='기록 = []\n클래스 비동기문맥:\n    어싱크 데프 __aenter__(셀프):\n        기록.append("입장")\n        리턴 21\n    어싱크 데프 __aexit__(셀프, 형식, 값, 추적):\n        기록.append("퇴장")\n        리턴 폴스\n어싱크 데프 메인():\n    어싱크 위드 비동기문맥() 애즈 값:\n        기록.append(값 * 2)\n    리턴 기록\n결과 = 어싱크실행(메인())\n'
        self.assertEqual(self.run_source(source)["결과"],["입장",42,"퇴장"])

    def test_async_generator_consumed_by_async_for(self):
        source='어싱크 데프 생성(끝):\n    포 값 인 레인지(끝):\n        일드 값 * 2\n어싱크 데프 메인():\n    결과 = []\n    어싱크 포 값 인 생성(4):\n        결과.append(값)\n    리턴 결과\n생성기 = 생성(1)\n결과 = 어싱크실행(메인())\n'
        values=self.run_source(source)
        self.assertIsInstance(values["생성기"],HythonAsyncGenerator)
        self.assertEqual(values["결과"],[0,2,4,6])

    def test_async_generator_asend_and_athrow(self):
        import asyncio
        values=self.run_source('어싱크 데프 전송():\n    받은값=(일드 "준비")\n    일드 받은값 * 2\n어싱크 데프 예외():\n    트라이:\n        일드 1\n    익셉트 밸류에러:\n        일드 99\n')
        async def exercise():
            sent=values["전송"](); first=await sent.__anext__(); second=await sent.asend(21)
            thrown=values["예외"](); initial=await thrown.__anext__(); recovered=await thrown.athrow(ValueError)
            return first,second,initial,recovered
        self.assertEqual(asyncio.run(exercise()),("준비",42,1,99))

    def test_async_generator_aclose_awaits_finally(self):
        import asyncio
        events=[]
        async def cleanup(): events.append("정리")
        values=self.run_source('어싱크 데프 생성(정리함수):\n    트라이:\n        일드 1\n    파이널리:\n        어웨이트 정리함수()\n')
        async def exercise():
            generator=values["생성"](cleanup); self.assertEqual(await generator.__anext__(),1); await generator.aclose()
        asyncio.run(exercise()); self.assertEqual(events,["정리"])

    def test_async_generator_aclose_rejects_yield_after_generator_exit(self):
        import asyncio
        generator=self.run_source('어싱크 데프 생성():\n    트라이:\n        일드 1\n    파이널리:\n        일드 2\n결과=생성()\n')["결과"]
        async def exercise():
            self.assertEqual(await generator.__anext__(),1)
            with self.assertRaises(RuntimeError): await generator.aclose()
        asyncio.run(exercise())

    def test_async_generator_asend_reaches_async_for_body_delegate(self):
        import asyncio
        class Stream:
            def __init__(self): self.done=False
            def __aiter__(self): return self
            async def __anext__(self):
                if self.done: raise StopAsyncIteration
                self.done=True; return 1
        values=self.run_source('어싱크 데프 생성(흐름):\n    어싱크 포 값 인 흐름:\n        받은값=(일드 값)\n        일드 받은값\n')
        async def exercise():
            generator=values["생성"](Stream()); return await generator.__anext__(),await generator.asend(42)
        self.assertEqual(asyncio.run(exercise()),(1,42))

    def test_async_generator_athrow_reaches_async_for_body_delegate(self):
        import asyncio
        class Stream:
            def __init__(self): self.done=False
            def __aiter__(self): return self
            async def __anext__(self):
                if self.done: raise StopAsyncIteration
                self.done=True; return 1
        values=self.run_source('어싱크 데프 생성(흐름):\n    어싱크 포 값 인 흐름:\n        트라이:\n            일드 값\n        익셉트 밸류에러:\n            일드 99\n')
        async def exercise():
            generator=values["생성"](Stream()); return await generator.__anext__(),await generator.athrow(ValueError)
        self.assertEqual(asyncio.run(exercise()),(1,99))

    def test_async_generator_rejects_non_none_asend_before_start(self):
        import asyncio
        generator=self.run_source('어싱크 데프 생성():\n    일드 1\n결과=생성()\n')["결과"]
        async def exercise():
            with self.assertRaises(TypeError): await generator.asend(42)
        asyncio.run(exercise())

    def test_async_generator_rejects_concurrent_reentry_while_awaiting(self):
        import asyncio
        vm=VM(); vm.run(compile_source('어싱크 데프 생성(대기):\n    어웨이트 대기()\n    일드 1\n'))
        async def exercise():
            entered=asyncio.Event(); release=asyncio.Event()
            async def wait(): entered.set(); await release.wait()
            generator=vm.globals["생성"](wait)
            pending=asyncio.create_task(generator.__anext__()); await entered.wait()
            with self.assertRaisesRegex(RuntimeError,"already running"): await generator.__anext__()
            with self.assertRaisesRegex(RuntimeError,"already running"): await generator.asend(None)
            with self.assertRaisesRegex(RuntimeError,"already running"): await generator.athrow(ValueError)
            with self.assertRaisesRegex(RuntimeError,"already running"): await generator.aclose()
            release.set(); self.assertEqual(await pending,1); await generator.aclose()
        asyncio.run(exercise())

    def test_rich_syntax_try_and_await_inside_sync_with(self):
        events=[]
        class Manager:
            def __enter__(self): events.append("enter")
            def __exit__(self,*exc): events.append("exit")
        async def value(): return 5
        source='\n'.join([
            '어싱크 데프 메인(관리자, 값함수):',
            '    데프 합계(*값들):',
            '        리턴 썸(값들)',
            '    트라이:',
            '        위드 관리자:',
            '            기준 = 어웨이트 값함수()',
            '            자료 = [값 * 2 포 값 인 레인지(4) 이프 값 > 1]',
            '            리턴 합계(*자료) + 기준',
            '    파이널리:',
            '        패스',
            ''
        ])
        values=self.run_source(source); result=__import__('asyncio').run(values["메인"](Manager(),value))
        self.assertEqual(result,15); self.assertEqual(events,["enter","exit"])

    def test_async_generator_awaits_between_yields(self):
        source='\n'.join([
            '어싱크 데프 두배(값):',
            '    리턴 값 * 2',
            '어싱크 데프 생성():',
            '    일드 1',
            '    값 = 어웨이트 두배(21)',
            '    일드 값',
            '어싱크 데프 메인():',
            '    결과 = []',
            '    어싱크 포 값 인 생성():',
            '        결과.append(값)',
            '    리턴 결과',
            '결과 = 어싱크실행(메인())',
            ''
        ])
        self.assertEqual(self.run_source(source)["결과"],[1,42])

    def test_async_generator_yields_inside_async_for_and_with(self):
        source='\n'.join([
            '클래스 비동기범위:',
            '    데프 __init__(셀프):',
            '        셀프.현재 = 0',
            '    데프 __aiter__(셀프):',
            '        리턴 셀프',
            '    어싱크 데프 __anext__(셀프):',
            '        이프 셀프.현재 >= 3:',
            '            레이즈 스톱어싱크이터레이션()',
            '        값 = 셀프.현재',
            '        셀프.현재 = 셀프.현재 + 1',
            '        리턴 값',
            '클래스 문맥:',
            '    어싱크 데프 __aenter__(셀프):',
            '        리턴 10',
            '    어싱크 데프 __aexit__(셀프, 형식, 값, 추적):',
            '        리턴 폴스',
            '어싱크 데프 생성():',
            '    어싱크 위드 문맥() 애즈 기준:',
            '        어싱크 포 값 인 비동기범위():',
            '            일드 기준 + 값',
            '어싱크 데프 메인():',
            '    결과 = []',
            '    어싱크 포 값 인 생성():',
            '        결과.append(값)',
            '    리턴 결과',
            '결과 = 어싱크실행(메인())',
            ''
        ])
        self.assertEqual(self.run_source(source)["결과"],[10,11,12])

    def test_async_comprehension_and_generator_expression(self):
        class Stream:
            def __init__(self): self.value=0
            def __aiter__(self): return self
            async def __anext__(self):
                if self.value>=5: raise StopAsyncIteration
                value=self.value; self.value+=1; return value
        async def transform(value): return value*2
        async def accepted(value): return value%2==0
        source='\n'.join([
            '어싱크 데프 메인(흐름, 변환, 검사):',
            '    목록 = [어웨이트 변환(값) 어싱크 포 값 인 흐름() 이프 어웨이트 검사(값)]',
            '    생성기 = (어웨이트 변환(값) 어싱크 포 값 인 흐름())',
            '    추가 = []',
            '    어싱크 포 값 인 생성기:',
            '        추가.append(값)',
            '    리턴 (목록, 추가)',
            ''
        ])
        values=self.run_source(source)
        result=__import__('asyncio').run(values["메인"](Stream,transform,accepted))
        self.assertEqual(result,([0,4,8],[0,2,4,6,8]))

    def test_async_function_can_define_generic_function(self):
        source='어싱크 데프 생성():\n    데프 항등[T](값: T) -> T:\n        리턴 값\n    리턴 항등\n'
        values=self.run_source(source)
        function=__import__('asyncio').run(values["생성"]())
        self.assertEqual(function(42),42)
        self.assertEqual(len(function.__type_params__),1)

    def test_async_generator_expression_prepares_outer_iterator_immediately(self):
        events=[]
        class Stream:
            def __init__(self): self.value=0
            def __aiter__(self): events.append("aiter"); return self
            async def __anext__(self):
                if self.value: raise StopAsyncIteration
                self.value=1; return 42
        vm=VM(); vm.globals["흐름"]=Stream()
        vm.run(compile_source('생성기=(값 어싱크 포 값 인 흐름)\n'))
        self.assertEqual(events,["aiter"])
        async def collect(generator): return [item async for item in generator]
        self.assertEqual(__import__('asyncio').run(collect(vm.globals["생성기"])),[42])

    def test_async_comprehension_filters_short_circuit(self):
        class Stream:
            def __init__(self): self.done=False
            def __aiter__(self): return self
            async def __anext__(self):
                if self.done: raise StopAsyncIteration
                self.done=True; return 1
        async def reject(_): return False
        async def explode(_): raise AssertionError("두 번째 필터가 실행됨")
        source='어싱크 데프 실행(흐름, 거절, 폭발):\n    리턴 [값 어싱크 포 값 인 흐름() 이프 어웨이트 거절(값) 이프 어웨이트 폭발(값)]\n'
        values=self.run_source(source)
        result=__import__('asyncio').run(values["실행"](Stream,reject,explode))
        self.assertEqual(result,[])

    def test_async_iteration_special_methods_are_looked_up_on_type(self):
        events=[]
        class Stream:
            def __init__(self): self.done=False
            def __getattribute__(self,name):
                if name in {"__aiter__","__anext__"}: raise AssertionError("instance lookup")
                return object.__getattribute__(self,name)
            def __aiter__(self): events.append("aiter"); return self
            async def __anext__(self):
                if self.done: raise StopAsyncIteration
                self.done=True; events.append("anext"); return 42
        first=Stream(); first.__dict__["__aiter__"]=lambda: None; first.__dict__["__anext__"]=lambda: None
        second=Stream(); second.__dict__["__aiter__"]=lambda: None; second.__dict__["__anext__"]=lambda: None
        source='어싱크 데프 반복(흐름):\n    결과=[]\n    어싱크 포 값 인 흐름: 결과.append(값)\n    리턴 결과\n어싱크 데프 모음(흐름): 리턴 [값 어싱크 포 값 인 흐름]\n'
        values=self.run_source(source); asyncio=__import__('asyncio')
        self.assertEqual((asyncio.run(values["반복"](first)),asyncio.run(values["모음"](second))),([42],[42]))
        self.assertEqual(events,["aiter","anext","aiter","anext"])

    def test_async_iterator_requires_type_level_anext(self):
        class Iterator: pass
        iterator=Iterator()
        async def fake(): raise StopAsyncIteration
        iterator.__anext__=fake
        class Iterable:
            def __aiter__(self): return iterator
        values=self.run_source('어싱크 데프 실행(흐름):\n    어싱크 포 값 인 흐름: 패스\n')
        with self.assertRaises(TypeError): __import__('asyncio').run(values["실행"](Iterable()))

    def test_async_with_outer_exit_can_suppress_inner_exit_failure(self):
        events=[]
        class Outer:
            async def __aenter__(self): return self
            async def __aexit__(self,kind,error,trace): events.append(kind); return kind is TypeError
        class Inner:
            async def __aenter__(self): return self
            async def __aexit__(self,*args): raise TypeError("퇴장 실패")
        source='어싱크 데프 실행(바깥, 안쪽):\n    어싱크 위드 바깥, 안쪽:\n        패스\n    리턴 42\n'
        values=self.run_source(source)
        result=__import__('asyncio').run(values["실행"](Outer(),Inner()))
        self.assertEqual(result,42); self.assertEqual(events,[TypeError])

    def test_async_exit_reraising_same_exception_has_no_self_context(self):
        import asyncio
        error=ValueError("동일")
        class Manager:
            async def __aenter__(self): return self
            async def __aexit__(self,*exc): raise error
        values=self.run_source('어싱크 데프 실행(문맥, 오류):\n    어싱크 위드 문맥:\n        레이즈 오류\n')
        with self.assertRaises(ValueError) as raised: asyncio.run(values["실행"](Manager(),error))
        self.assertIs(raised.exception,error); self.assertIsNone(error.__context__)

    def test_async_with_special_methods_are_looked_up_on_type(self):
        events=[]
        class Manager:
            def __getattribute__(self,name):
                if name in {"__aenter__","__aexit__"}: raise AssertionError("instance lookup")
                return object.__getattribute__(self,name)
            async def __aenter__(self): events.append("type-enter"); return 42
            async def __aexit__(self,*exc): events.append("type-exit")
        manager=Manager()
        manager.__dict__["__aenter__"]=lambda: None
        manager.__dict__["__aexit__"]=lambda *exc: None
        values=self.run_source('어싱크 데프 실행(문맥):\n    어싱크 위드 문맥 애즈 값:\n        리턴 값\n')
        result=__import__('asyncio').run(values["실행"](manager))
        self.assertEqual(result,42)
        self.assertEqual(events,["type-enter","type-exit"])

    def test_sync_with_loop_control_is_not_an_exit_exception_in_coroutine(self):
        seen=[]
        class Manager:
            def __enter__(self): return self
            def __exit__(self,*exc): seen.append(exc)
        source='어싱크 데프 실행(문맥):\n    포 값 인 [1]:\n        위드 문맥:\n            컨티뉴\n    리턴 42\n'
        values=self.run_source(source)
        self.assertEqual(__import__('asyncio').run(values["실행"](Manager())),42)
        self.assertEqual(seen,[(None,None,None)])

    def test_async_with_loop_control_unwinds_normally(self):
        seen=[]
        class Manager:
            async def __aenter__(self): return self
            async def __aexit__(self,*exc): seen.append(exc)
        source='어싱크 데프 실행(문맥):\n    포 값 인 [1]:\n        어싱크 위드 문맥:\n            컨티뉴\n    리턴 42\n'
        values=self.run_source(source)
        self.assertEqual(__import__('asyncio').run(values["실행"](Manager())),42)
        self.assertEqual(seen,[(None,None,None)])
