import unittest
from string.templatelib import Template
from hython.compiler import compile_source
from hython.vm import VM

class FStringTests(unittest.TestCase):
    def test_python_314_template_string(self):
        source='값=42\n너비=5\n결과=t"안녕 {값!r:>{너비}} / {값=}"\n'
        vm=VM(); vm.run(compile_source(source)); template=vm.globals["결과"]
        self.assertIsInstance(template,Template)
        self.assertEqual(template.strings,("안녕 "," / 값=",""))
        self.assertEqual([(item.value,item.expression,item.conversion,item.format_spec) for item in template.interpolations],[(42,"값","r",">5"),(42,"값","r","")])
    def test_template_expression_preserves_original_source_spacing(self):
        source='값=1\n결과=(t"{ 값 + 1 }", t"{ 값 + 1 = }", t"{값 + 1!r:>5}")\n'
        vm=VM(); vm.run(compile_source(source)); plain,debug,formatted=vm.globals["결과"]
        self.assertEqual((plain.interpolations[0].expression,debug.interpolations[0].expression,formatted.interpolations[0].expression),(" 값 + 1"," 값 + 1","값 + 1"))
        self.assertEqual(debug.strings,(" 값 + 1 = ",""))
    def test_fstring_debug_prefix_preserves_original_source_spacing(self):
        vm=VM(); vm.run(compile_source('값=1\n결과=f"{ 값 + 1 = }"\n'))
        self.assertEqual(vm.globals["결과"]," 값 + 1 = 2")
    def test_debug_expression_with_conversion_and_format(self):
        source='값 = "가"\n숫자 = 41\n결과 = (f"{값=}", f"{값=!s:>4}", f"{숫자+1=}")\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("값='가'","값=   가","숫자+1=42"))
    def test_conversion_static_and_nested_format_specs(self):
        source='\n'.join([
            '값 = "한\\n글"',
            '숫자 = 42',
            '너비 = 5',
            '결과 = (f"{값!r}", f"{숫자:04d}", f"{숫자:{너비}d}")',
            ''
        ])
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("'한\\n글'","0042","   42"))
    def test_nested_format_spec_conversion(self):
        vm=VM(); vm.run(compile_source('결과=(f"{1:{2!r}}", t"{1:{2!r}}")\n'))
        formatted,template=vm.globals["결과"]
        self.assertEqual(formatted," 1")
        self.assertEqual(template.interpolations[0].format_spec,"2")
    def test_nested_debug_and_nested_format_spec(self):
        vm=VM(); vm.run(compile_source('결과=(f"{1:{2=}}", t"{1:{2=}}", f"{1:{2:03}}", t"{1:{2:03}}")\n'))
        debug,debug_template,formatted,formatted_template=vm.globals["결과"]
        self.assertEqual((debug,formatted),("21","01"))
        self.assertEqual((debug_template.interpolations[0].format_spec,formatted_template.interpolations[0].format_spec),("2=2","002"))

    def test_python314_second_level_nested_format_spec(self):
        vm=VM(); vm.run(compile_source('결과=t"{1:{2:{3}}}"\n'))
        template=vm.globals["결과"]
        self.assertEqual(template.interpolations[0].format_spec,"  2")
        with self.assertRaises(ValueError): format(1,"  2")
        with self.assertRaises(ValueError): vm.run(compile_source('결과=f"{1:{2:{3}}}"\n'))

    def test_format_spec_rejects_nesting_deeper_than_python314(self):
        with self.assertRaises(SyntaxError): compile_source('결과=f"{1:{2:{3:{4}}}}"\n')
    def test_debug_field_with_format_spec_does_not_imply_repr(self):
        vm=VM(); vm.run(compile_source('값="가"\n결과=(f"{값=:>5}",t"{값=:>5}")\n'))
        formatted,template=vm.globals["결과"]
        self.assertEqual(formatted,"값=    가")
        self.assertIsNone(template.interpolations[0].conversion)
        self.assertEqual(template.interpolations[0].format_spec,">5")
    def test_invalid_conversion_is_rejected_at_compile_time(self):
        for prefix in ("f","t"):
            with self.subTest(prefix=prefix):
                with self.assertRaises(SyntaxError): compile_source(f'결과={prefix}"{{1!z}}"\n')
    def test_native_fstring(self):
        vm=VM(); vm.run(compile_source('이름 = "하이썬"\n결과 = f"안녕, {이름}!"\n'))
        self.assertEqual(vm.globals["결과"],"안녕, 하이썬!")
    def test_adjacent_plain_and_fstring_literals(self):
        source='값=1\n결과=("앞" f"{값}", f"{값}" "뒤", f"{값}" f"{값+1}", ("a" "b").upper())\n'
        vm=VM(); vm.run(compile_source(source))
        self.assertEqual(vm.globals["결과"],("앞1","1뒤","12","AB"))

    def test_adjacent_template_literals_merge(self):
        vm=VM(); vm.run(compile_source('값=1\n결과=t"{값}" t"{값+1}"\n'))
        template=vm.globals["결과"]
        self.assertEqual(template.strings,("","",""))
        self.assertEqual([item.value for item in template.interpolations],[1,2])

    def test_template_literal_cannot_mix_with_other_string_kinds(self):
        for source in ('결과="앞" t"{1}"\n','결과=t"{1}" "뒤"\n','결과=f"{1}" t"{1}"\n'):
            with self.subTest(source=source),self.assertRaises(SyntaxError): compile_source(source)
