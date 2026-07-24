import ast
import unittest

from hython.compiler import compile_source
from hython.translator import to_hython


class Python314SyntaxMatrixTests(unittest.TestCase):
    CASES={
        "semicolon":"x=1; y=2",
        "continued_line":"x=1+\\\n 2",
        "parenthesized_with":"with (open('x') as a, open('y') as b):\n pass",
        "bare_raise":"try:\n raise ValueError()\nexcept:\n raise",
        "annotation_without_value":"x: int",
        "extended_delete":"del a, b[0]",
        "positional_only_lambda":"f=lambda x,/,y=1,*a,z=2,**k:x",
        "debug_fstring":"x=1; y=f'{x=}'",
        "nested_format_spec":"w=3; x=1; y=f'{x:{w}}'",
        "except_star":"try:\n pass\nexcept* ValueError as e:\n pass",
        "async_comprehension":"async def f(xs):\n return [x async for x in xs if x]",
        "mixed_call_unpacking":"f(*a, x=1, **k)",
        "collection_unpacking":"x={**a,'b':2}; y={*a,2}",
        "extended_slice":"x=a[1:2:3, ..., None]",
        "named_expression":"if (x := 1):\n pass",
        "guarded_or_pattern":"match x:\n case 1|2 as y if y:\n  pass",
        "class_unpacking":"class C(*bases, metaclass=M, **kw):\n pass",
        "type_parameter_default":"class C[T=int]:\n pass",
        "template_string":"name='Hython'; value=t'hello {name}'",
        "decorated_def":"@decorator\ndef f(x: int=1,*,y: str='a') -> int:\n return x",
        "decorated_async_def":"@decorator()\nasync def f():\n return await task()",
        "decorated_class":"@decorator\nclass C(Base):\n value=1",
        "global_statement":"x=0\ndef f():\n global x\n x=1",
        "nonlocal_statement":"def outer():\n x=0\n def inner():\n  nonlocal x\n  x=1",
        "try_else_finally":"try:\n value=f()\nexcept ValueError as error:\n value=error\nelse:\n value=1\nfinally:\n cleanup()",
        "raise_from":"raise RuntimeError() from cause",
        "assert_message":"assert condition, 'message'",
        "while_else":"while condition:\n break\nelse:\n pass",
        "for_else":"for x in values:\n continue\nelse:\n pass",
        "async_for_else":"async def f():\n async for x in values:\n  continue\n else:\n  pass",
        "async_with":"async def f():\n async with manager() as value:\n  return value",
        "yield_expression":"def f():\n received=(yield 1)\n return received",
        "yield_from_expression":"def f():\n return (yield from values)",
        "conditional_expression":"value=yes if condition else no",
        "boolean_and_unary":"value=(a and b) or not -c",
        "matrix_and_bitwise_ops":"value=(a @ b) | (c ^ d) & (e << 2)",
        "augmented_assignments":"x+=1; y//=2; z@=matrix",
        "attribute_and_item_assign":"obj.attr=value; data[index]=value",
        "starred_assignment":"first,*middle,last=values",
        "list_set_dict_comprehensions":"a=[x for x in xs]; b={x for x in xs}; c={x:x*x for x in xs}",
        "generator_expression":"items=(x for x in xs if x)",
        "lambda_conditional":"f=lambda x: x if x else 0",
        "import_forms":"import package.module as module\nfrom package.module import value as alias",
        "relative_import":"from .module import value",
        "match_mapping_sequence_class":"match value:\n case {'x': x, **rest}: pass\n case [first, *tail]: pass\n case Point(x, y=other): pass",
        "bytes_ellipsis_complex":"values=[b'data', ..., 1j]; ordered=1<2",
        "raw_and_concatenated_strings":"value=r'raw\\n' 'joined'",
        "multidimensional_slice":"value=data[1:2, :, ...]",
        "call_all_argument_kinds":"value=f(1, *args, key=2, **kwargs)",
        "type_alias_parameters":"type Pair[T, U=int] = tuple[T, U]",
        "function_type_parameters":"def identity[T](value: T) -> T:\n return value",
        "async_function_type_parameters":"async def identity[T](value: T) -> T:\n return value",
        "class_type_parameters":"class Box[T](Base):\n value: T",
        "match_singleton":"match value:\n case None: result=0\n case True: result=1\n case False: result=2",
        "variadic_type_parameters":"def variadic[*Ts, **P]():\n pass",
    }

    def test_native_python_and_hbc_frontends_accept_same_syntax_families(self):
        for name,source in self.CASES.items():
            with self.subTest(name=name):
                compile(source,"<python-3.14-matrix>","exec")
                compile_source(to_hython(source+"\n"))

    def test_matrix_covers_every_python314_statement_expression_pattern_and_type_parameter_node(self):
        seen={type(node) for source in self.CASES.values() for node in ast.walk(ast.parse(source))}
        for base in (ast.stmt,ast.expr,ast.pattern,ast.type_param):
            with self.subTest(base=base.__name__):
                self.assertEqual(set(base.__subclasses__())-seen,set())
