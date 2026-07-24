import ast
import unittest

from hython.compiler import compile_source
from hython.translator import to_hython
from hython.vm import VM


class Python314SemanticMatrixTests(unittest.TestCase):
    CASES={
        "numeric_and_comparison": "value=1\nresult=((7+5)*3//2, 2**8, 17%5, 1<2<3, value is not None)",
        "boolean_short_circuit": "events=[]\ndef mark(x): events.append(x); return x\nresult=(mark(0) and mark(1), mark(2) or mark(3), events)",
        "extended_unpacking": "first,*middle,last=range(6)\nresult=(first,middle,last)",
        "comprehensions": "result=([x*x for x in range(6) if x%2], {x for x in range(4)}, {x:x+1 for x in range(3)})",
        "walrus_comprehension_scope": "last=-1\nvalues=[(last:=x) for x in range(4)]\nresult=(values,last)",
        "closure_and_nonlocal": "def outer():\n value=1\n def inner(step):\n  nonlocal value\n  value+=step\n  return value\n return inner\nf=outer()\nresult=(f(2),f(3))",
        "decorators": "def decorate(fn):\n def wrapped(*args,**kwargs): return fn(*args,**kwargs)+1\n return wrapped\n@decorate\ndef value(x): return x*2\nresult=value(20)",
        "class_inheritance_super": "class Base:\n def value(self): return 40\nclass Child(Base):\n def value(self): return super().value()+2\nresult=Child().value()",
        "property_descriptor": "class C:\n def __init__(self): self._x=20\n @property\n def x(self): return self._x+22\nresult=C().x",
        "private_name_mangling": "class C:\n __hidden=42\n def value(self): return self.__hidden\nresult=(C().value(),hasattr(C,'_C__hidden'),hasattr(C,'__hidden'))",
        "private_parameter_signature": "import inspect\nclass C:\n def value(self,__item=1): return __item\nresult=(C().value(_C__item=42),str(inspect.signature(C.value)))",
        "nested_class_private_names": "class Outer:\n __value=20\n class Inner:\n  __value=22\n  def value(self): return self.__value\nresult=(Outer._Outer__value,Outer.Inner._Inner__value,Outer.Inner().value())",
        "inherited_private_names": "class Base:\n __value=20\n def base(self): return self.__value\nclass Child(Base):\n __value=22\n def child(self): return self.__value\nresult=(Child().base(),Child().child(),hasattr(Child,'_Child__value'))",
        "private_annotation_and_descriptor_name": "events=[]\nclass Descriptor:\n def __set_name__(self,owner,name): events.append(name)\n def __get__(self,obj,owner): return 42\nclass C:\n __field:int=Descriptor()\n def value(self): return self.__field\nresult=(events,C().value(),tuple(C.__annotations__))",
        "private_global_declaration": "class C:\n global __value\n __value=42\nresult=(globals().get('_C__value'),globals().get('__value'),hasattr(C,'_C__value'))",
        "private_leading_class_underscores": "class __C:\n __value=42\n __magic__=7\nresult=(__C._C__value,__C.__magic__)",
        "private_nested_nonlocal": "class C:\n def value(self):\n  __item=20\n  def add():\n   nonlocal __item\n   __item+=22\n   return __item\n  return add()\nresult=C().value()",
        "private_pattern_capture": "class C:\n match [42]:\n  case [__item]: pass\n result=__item\nresult=(C.result,C._C__item,hasattr(C,'__item'))",
        "private_generic_bindings": "class C[__T]:\n type __Alias=__T\n def value[__U](self,item:__U)->__U: return item\nresult=([x.__name__ for x in C.__type_params__],C._C__Alias.__name__,C.value.__type_params__[0].__name__,C().value(42))",
        "class_static_attributes": "class C:\n def first(self): self.z=1; self.__private=2; self.a=3\n @staticmethod\n def second(self): self.static=4\n def nested(self):\n  def inner(): self.closed=5\nresult=C.__static_attributes__",
        "static_attributes_exclusions": "class C:\n def other(instance): instance.x=1\n def annotations(self): self.only_annotation:int\n def deletion(self): del self.deleted\n class Nested:\n  def value(self): self.nested=1\nresult=C.__static_attributes__",
        "metaclass_observes_static_attributes": "seen=[]\nclass Meta(type):\n def __new__(meta,name,bases,namespace):\n  seen.append(namespace.get('__static_attributes__'))\n  return super().__new__(meta,name,bases,namespace)\nclass C(metaclass=Meta):\n def value(self): self.answer=42\nresult=(seen,C.__static_attributes__)",
        "class_firstlineno_metadata": "seen=[]\nclass Meta(type):\n def __new__(meta,name,bases,namespace):\n  seen.append(namespace.get('__firstlineno__'))\n  return super().__new__(meta,name,bases,namespace)\ndef decorate(value): return value\n@decorate\nclass C(metaclass=Meta):\n body_seen=__firstlineno__\n class Nested:\n  pass\nresult=(C.__firstlineno__,C.body_seen,C.Nested.__firstlineno__,seen)",
        "class_firstlineno_override": "class C:\n __firstlineno__=999\nresult=C.__firstlineno__",
        "class_firstlineno_module_assignment": "class Plain: pass\nplain_before=Plain.__firstlineno__\nPlain.__module__='changed'\nclass Meta(type): pass\nclass Custom(metaclass=Meta): pass\ncustom_before=Custom.__firstlineno__\nCustom.__module__='changed'\nresult=(plain_before,hasattr(Plain,'__firstlineno__'),custom_before,hasattr(Custom,'__firstlineno__'))",
        "try_else_finally": "events=[]\ntry:\n events.append('try')\nexcept ValueError:\n events.append('except')\nelse:\n events.append('else')\nfinally:\n events.append('finally')\nresult=events",
        "exception_group": "seen=[]\ntry:\n raise ExceptionGroup('group',[ValueError('a'),TypeError('b')])\nexcept* ValueError as errors:\n seen.append(('value',len(errors.exceptions)))\nexcept* TypeError as errors:\n seen.append(('type',len(errors.exceptions)))\nresult=seen",
        "pattern_matching": "value={'kind':'point','coords':[20,22],'extra':1}\nmatch value:\n case {'kind':'point','coords':[x,y],**rest} if x+y==42: result=(x,y,rest)\n case _: result=None",
        "generator_yield_from": "def inner():\n yield 20\n return 22\ndef outer():\n value=yield from inner()\n yield value\nresult=list(outer())",
        "with_suppression": "events=[]\nclass Manager:\n def __enter__(self): events.append('enter'); return 42\n def __exit__(self,*exc): events.append(exc[0].__name__); return True\nwith Manager() as value:\n raise ValueError('handled')\nresult=(value,events)",
        "async_await_and_comprehension": "import asyncio\nasync def twice(x): return x*2\nasync def main(): return [await twice(x) for x in range(4)]\nresult=asyncio.run(main())",
        "await_in_all_sync_comprehension_clauses": "import asyncio\nasync def twice(x): return x*2\nasync def main():\n a={await twice(x) for x in range(3)}\n b={x:await twice(x) for x in range(3)}\n c=(await twice(x) for x in range(3))\n return (a,b,[x async for x in c])\nresult=asyncio.run(main())",
        "generic_function": "def identity[T](value:T)->T: return value\nresult=(identity(42),len(identity.__type_params__),identity.__type_params__[0].__name__)",
        "variadic_type_parameters": "def variadic[*Ts, **P](): pass\nresult=tuple(type(item).__name__ for item in variadic.__type_params__)",
        "function_user_attribute_dict": "def function(): pass\ninitial=function.__dict__.copy()\nfunction.answer=42\nafter=function.__dict__.copy()\nvalue=function.answer\ndel function.answer\nafter_delete=function.__dict__.copy()\nfunction.__dict__={'replacement':20}\nresult=(initial,after,value,after_delete,function.replacement,function.__dict__.copy())",
        "function_builtins_snapshot_and_readonly_attributes": "def function(): return 1\noriginal=function.__builtins__\nglobals()['__builtins__']={'changed':True}\nerrors=[]\nfor name in ('__globals__','__closure__','__builtins__'):\n try: setattr(function,name,None)\n except BaseException as error: errors.append((name,type(error).__name__))\nresult=(function.__builtins__ is original,errors,function.__dict__)",
        "function_code_replacement": "def first(): return 1\ndef second(): return 42\nfirst.__code__=second.__code__\nresult=(first(),first.__dict__)",
        "while_if_break_continue_assert": "events=[]\ni=0\nwhile i<6:\n i+=1\n if i%2: continue\n events.append(i)\n if i==4: break\nassert events==[2,4]\nresult=events",
        "from_import_lambda_conditional_strings_set_and_slice": "from math import sqrt\nvalue=3\nformatted=f'{value}'\nchoice=(lambda x:x+1)(value) if value else 0\nitems={1,2}\ndata=[0,1,2,3]\nportion=data[1:3]\ntemplate=t'v={value}'\nresult=(sqrt(1764),formatted,choice,items,portion,template.strings,tuple((item.value,item.expression) for item in template.interpolations))",
        "class_or_singleton_and_star_patterns": "class Point:\n __match_args__=('x','y')\n def __init__(self,x,y): self.x=x; self.y=y\nresults=[]\nfor value in (None,Point(20,22),[1,2,3],2):\n match value:\n  case None: results.append('none')\n  case Point(x,y): results.append(x+y)\n  case [head,*tail]: results.append((head,tail))\n  case 1|2: results.append('small')\nresult=results",
        "async_for_and_async_with": "import asyncio\nevents=[]\nclass Manager:\n async def __aenter__(self): events.append('enter'); return 2\n async def __aexit__(self,*exc): events.append('exit')\nasync def stream():\n yield 20\n yield 22\nasync def main():\n values=[]\n async with Manager() as factor:\n  async for value in stream(): values.append(value*factor)\n return values\nresult=(asyncio.run(main()),events)",
    }

    def test_hbc_results_match_cpython_314(self):
        for name,source in self.CASES.items():
            with self.subTest(name=name):
                python_globals={}
                exec(compile(source,"<python-3.14-semantics>","exec"),python_globals)
                vm=VM(); vm.run(compile_source(to_hython(source+"\n")))
                self.assertEqual(vm.globals["result"],python_globals["result"])

    def test_semantic_matrix_covers_every_python314_concrete_ast_node(self):
        seen={type(node) for source in self.CASES.values() for node in ast.walk(ast.parse(source))}
        for base in (ast.stmt,ast.expr,ast.pattern,ast.type_param):
            with self.subTest(base=base.__name__):
                self.assertEqual(set(base.__subclasses__())-seen,set())
