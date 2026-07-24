import unittest
from hython.frontend import ParseError, parse
from hython.compiler import compile_source
from hython.vm import VM

class FrontendTests(unittest.TestCase):
    def test_soft_keywords_remain_identifiers_outside_their_grammar(self):
        source='매치=20\n케이스=22\n타입: 인트 = 매치 + 케이스\n결과=타입\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],42)
    def test_builds_hython_owned_ast(self):
        tree = parse("이프 값 >= 3:\n    프린트(값)\n엘스:\n    패스\n")
        self.assertEqual(tree.kind, "module")
        self.assertEqual(tree.children[0].kind, "if")
        self.assertEqual(tree.children[0].children[0].value, ">=")

    def test_reports_line_for_bad_assignment(self):
        with self.assertRaisesRegex(ParseError, "줄 1"):
            parse("1 = 2\n")
