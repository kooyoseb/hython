import unittest

from hython.diagnostics import exception_name,format_exception,translated_message


class DiagnosticsTests(unittest.TestCase):
    def test_common_runtime_messages_are_korean(self):
        cases=[
            (NameError("name '값' is not defined"),"이름 '값'이 정의되지 않았습니다."),
            (AttributeError("'str' object has no attribute '없음'"),"'str' 객체에 '없음' 속성이 없습니다."),
            (TypeError("'int' object is not callable"),"'int' 객체는 호출할 수 없습니다."),
            (IndexError("list index out of range"),"리스트 인덱스가 범위를 벗어났습니다."),
            (ZeroDivisionError("division by zero"),"0으로 나눌 수 없습니다."),
        ]
        for error,expected in cases:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(translated_message(error),expected)

    def test_user_message_is_preserved_when_no_safe_translation_exists(self):
        error=ValueError("사용자가 만든 설명")
        self.assertEqual(translated_message(error),"사용자가 만든 설명")
        self.assertEqual(exception_name(error),"값 오류")

    def test_traceback_uses_korean_labels_and_source_location(self):
        try:
            compile("1 / 0","프로그램.hy","exec") and exec(compile("1 / 0","프로그램.hy","exec"))
        except Exception as error:
            rendered=format_exception(error)
        self.assertIn("하이썬 추적",rendered)
        self.assertIn('파일 "프로그램.hy", 줄 1',rendered)
        self.assertIn("0 나누기 오류: 0으로 나눌 수 없습니다.",rendered)

    def test_exception_chain_and_group_are_structured_in_korean(self):
        try:
            try:
                raise KeyError("항목")
            except KeyError as original:
                raise ValueError("변환 실패") from original
        except Exception as chained:
            rendered=format_exception(chained,traceback_enabled=False)
        self.assertIn("직접 원인",rendered)
        self.assertIn("키를 찾을 수 없습니다",rendered)
        group=format_exception(ExceptionGroup("묶음",[NameError("name 'x' is not defined")]),traceback_enabled=False)
        self.assertIn("하위 오류 1",group)
        self.assertIn("이름 'x'이 정의되지 않았습니다",group)

    def test_syntax_error_keeps_caret_data_and_translates_message(self):
        try:
            compile("if True print(1)","문법.hy","exec")
        except SyntaxError as error:
            self.assertEqual(exception_name(error),"문법 오류")
            self.assertEqual(translated_message(error),"잘못된 문법입니다.")
