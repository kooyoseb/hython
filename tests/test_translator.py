import unittest

from hython.translator import (
    audit_english, compile_hython, koreanize, to_hython, to_python,
)


class TranslatorTests(unittest.TestCase):
    def test_executes_hython(self):
        namespace = {}
        exec(compile_hython("결과 = [수 * 2 포 수 인 레인지(3)]"), namespace)
        self.assertEqual(namespace["결과"], [0, 2, 4])

    def test_preserves_strings_and_comments(self):
        source = '프린트("프린트 인폴트")  # 프린트\n'
        translated = to_python(source)
        self.assertIn('"프린트 인폴트"', translated)
        self.assertIn("# 프린트", translated)
        self.assertTrue(translated.startswith("print"))

    def test_round_trip(self):
        source = "for n in range(2):\n    print(n)\n"
        self.assertEqual(to_python(to_hython(source)), source)

    def test_tkinter_can_be_written_without_english_api_names(self):
        source = "인폴트 티킨터 애즈 티케이\n창 = 티케이.티케이()\n창.타이틀('하이썬')\n창.메인루프()\n"
        translated = to_python(source)
        self.assertIn("import tkinter as 티케이", translated)
        self.assertIn("티케이.Tk()", translated)
        self.assertIn("창.title", translated)
        self.assertIn("창.mainloop", translated)

    def test_audit_ignores_text_and_reports_code_names(self):
        issues=audit_english('result = print("English text")  # comment\n')
        self.assertEqual([item.name for item in issues],["result","print"])
        self.assertEqual(issues[1].suggestion,"프린트")

    def test_complete_koreanize_renames_unknown_user_identifiers(self):
        result=koreanize('user_value = len([1])\nprint(f"{user_value}")\n')
        self.assertNotIn("user_value",result)
        self.assertIn("렌",result)
        self.assertIn("프린트",result)
        self.assertIn('에프"',result)
        self.assertEqual(audit_english(result),[])
        namespace={}
        exec(compile_hython(result),namespace)

    def test_hangul_string_prefixes(self):
        namespace={}
        exec(compile_hython('값 = 7\n결과 = 에프"값={값}"\n원문 = 알"\\n"\n'),namespace)
        self.assertEqual(namespace["결과"],"값=7")
        self.assertEqual(namespace["원문"],r"\n")
        issues=audit_english('값=f"{값}"\n')
        self.assertEqual([(item.name,item.suggestion) for item in issues],[("f","에프")])

    def test_python_special_names_have_hangul_spellings(self):
        source='이프 __네임__ == "__main__":\n    프린트(__파일__)\n'
        translated=to_python(source)
        self.assertIn("__name__",translated)
        self.assertIn("__file__",translated)
        self.assertNotIn("__네임__",translated)


if __name__ == "__main__":
    unittest.main()
