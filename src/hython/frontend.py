"""Hython-owned AST and parser for the native compiler path."""
from __future__ import annotations
from dataclasses import dataclass, field
import io
import token as token_types
import tokenize
from .package_manager import load_dictionaries
from .translator import normalize_literal_prefixes
from .vocabulary import HYTHON_TO_PYTHON

@dataclass
class Node:
    kind: str
    value: object = None
    children: list["Node"] = field(default_factory=list)
    line: int = 0
    grouped: bool = False

class ParseError(SyntaxError): pass

def lex(source: str) -> list[tuple[int,str,int,int,int]]:
    source = normalize_literal_prefixes(source)
    names = load_dictionaries() | HYTHON_TO_PYTHON
    result=[]; line_offsets=[]; offset=0
    for source_line in source.splitlines(keepends=True): line_offsets.append(offset); offset+=len(source_line)
    line_offsets.append(offset)
    def absolute(position):
        row,column=position
        return line_offsets[min(row-1,len(line_offsets)-1)]+column
    try: stream=list(tokenize.generate_tokens(io.StringIO(source).readline))
    except Exception as exc: raise ParseError(str(exc)) from exc
    aliases={stream[index+1].string for index,item in enumerate(stream[:-1]) if item.type==tokenize.NAME and item.string in ("as","애즈") and stream[index+1].type==tokenize.NAME}
    try:
        for index,item in enumerate(stream):
            if item.type in (tokenize.ENCODING, tokenize.COMMENT, tokenize.NL): continue
            alias_reference=item.string in aliases and (index==0 or stream[index-1].string!=".")
            text=names.get(item.string,item.string) if item.type==tokenize.NAME and not alias_reference else item.string
            result.append((item.type,text,item.start[0],absolute(item.start),absolute(item.end)))
    except (tokenize.TokenError,IndentationError) as exc: raise ParseError(str(exc)) from exc
    return result

class Parser:
    def __init__(self, source: str, filename: str = "<하이썬>"):
        self.source=source; self.filename=filename; self.tokens=lex(source); self.pos=0; self.future_features=set()
        for index,token in enumerate(self.tokens):
            if token[1]=="barry_as_FLUFL" and index>0 and self.tokens[index-1][1] in ("import","(",","):
                statement_start=max((i for i in range(index) if self.tokens[i][0]==tokenize.NEWLINE),default=-1)+1
                words=[item[1] for item in self.tokens[statement_start:index]]
                if len(words)>=3 and words[0:3]==["from","__future__","import"]: self.future_features.add("barry_as_FLUFL")
    def current(self): return self.tokens[self.pos] if self.pos<len(self.tokens) else (tokenize.ENDMARKER,"",0,len(self.source),len(self.source))
    def text(self): return self.current()[1]
    def take(self, text=None):
        token=self.current()
        if text is not None and token[1]!=text: raise ParseError(f"'{text}' 필요 (줄 {token[2]})")
        self.pos+=1; return token
    @staticmethod
    def require_grouped_namedexpr(node:Node,line:int,context:str):
        items=node.children if node.kind=="tuple" else [node]
        if any(item.kind=="namedexpr" and not item.grouped for item in items): raise ParseError(f"{context}의 명명식에는 괄호가 필요합니다 (줄 {line})")
    @staticmethod
    def reject_namedexpr(node:Node,line:int,context:str):
        if Parser._contains_kind(node,"namedexpr"): raise ParseError(f"{context}에는 명명식을 사용할 수 없습니다 (줄 {line})")
    @staticmethod
    def validate_unpack_target(node:Node,line:int,star_allowed:bool=False):
        if node.kind=="starred":
            if not star_allowed: raise ParseError(f"별표 대입 대상은 튜플이나 리스트 안에 있어야 합니다 (줄 {line})")
            Parser.validate_unpack_target(node.children[0],line,False); return
        if node.kind in ("tuple","list"):
            if sum(child.kind=="starred" for child in node.children)>1: raise ParseError(f"구조 분해 별표 대상은 한 수준에 하나만 허용됩니다 (줄 {line})")
            for child in node.children: Parser.validate_unpack_target(child,line,True)
            return
        if node.kind not in ("name","attribute","subscript"): raise ParseError(f"잘못된 대입 대상 (줄 {line})")
    @staticmethod
    def validate_delete_target(node:Node,line:int):
        if node.kind in ("tuple","list"):
            for child in node.children: Parser.validate_delete_target(child,line)
            return
        if node.kind not in ("name","attribute","subscript"): raise ParseError(f"잘못된 델 대상 (줄 {line})")
    @staticmethod
    def _contains_kind(node:Node,kind:str) -> bool:
        if node.kind in ("lambda","def","class"): return False
        return node.kind==kind or any(Parser._contains_kind(child,kind) for child in node.children)
    def skip_newlines(self):
        while self.current()[0] in (tokenize.NEWLINE,): self.pos+=1
    def parse(self):
        body=[]; self.skip_newlines()
        while self.current()[0]!=tokenize.ENDMARKER:
            body.append(self.statement()); self.skip_newlines()
        return Node("module",children=body)
    def suite(self):
        self.take(":")
        if self.current()[0]!=tokenize.NEWLINE:
            if self.text() in (";","@","def","async","class","if","while","try","for","with","match"):
                raise ParseError(f"한 줄 suite에는 단순 문장만 사용할 수 있습니다 (줄 {self.current()[2]})")
            line=self.current()[2]; body=[self.statement()]
            while self.current()[0] not in (tokenize.NEWLINE,tokenize.ENDMARKER) and self.current()[2]==line: body.append(self.statement())
            return body
        self.take_newline(); self.expect_type(tokenize.INDENT)
        body=[]; self.skip_newlines()
        while self.current()[0] not in (tokenize.DEDENT,tokenize.ENDMARKER):
            body.append(self.statement()); self.skip_newlines()
        self.expect_type(tokenize.DEDENT); return body
    def take_newline(self):
        if self.text()==";": self.pos+=1; return
        if self.current()[0]!=tokenize.NEWLINE: raise ParseError(f"줄 끝 필요 (줄 {self.current()[2]})")
        self.pos+=1
    def expect_type(self, kind):
        if self.current()[0]!=kind: raise ParseError(f"잘못된 들여쓰기 (줄 {self.current()[2]})")
        self.pos+=1
    def has_suite_colon(self):
        depth=0
        for token in self.tokens[self.pos:]:
            if token[0] in (tokenize.NEWLINE,tokenize.ENDMARKER): return False
            if token[1] in ("(","[","{"): depth+=1
            elif token[1] in (")","]","}"): depth=max(0,depth-1)
            elif token[1]==":" and depth==0: return True
        return False
    def dotted_name(self,allow_relative=False):
        dots=0
        if allow_relative:
            while self.text() in (".","..."):
                marker=self.take()[1]; dots+=len(marker)
        if dots and self.text()=="import": return "."*dots
        parts=[self.take()[1]]
        while self.text()==".": self.take("."); parts.append(self.take()[1])
        return "."*dots+".".join(parts)
    def statement(self):
        line=self.current()[2]; word=self.text()
        if word==";": raise ParseError(f"세미콜론 앞에는 단순 문장이 필요합니다 (줄 {line})")
        if word in ("elif","else","except","finally"):
            raise ParseError(f"앞선 복합문에 연결되지 않은 {word} 절입니다 (줄 {line})")
        if word=="@":
            decorators=[]
            while self.text()=="@":
                self.take("@"); decorators.append(self.expression()); self.take_newline()
            target=self.statement()
            if target.kind not in ("def","class"): raise ParseError(f"데코레이터 뒤에는 함수나 클래스가 필요합니다 (줄 {line})")
            return Node("decorated",target.value,[*decorators,target],line)
        if word=="import":
            self.take(); imports=[]
            while True:
                if self.current()[0]!=tokenize.NAME: raise ParseError(f"import에는 모듈 이름이 필요합니다 (줄 {line})")
                module=self.dotted_name(); alias=module.split(".")[0]
                if self.text()=="as": self.take(); alias=self.take()[1]
                imports.append((module,alias))
                if self.text()!=",": break
                self.take(",")
            self.take_newline(); return Node("imports",imports,line=line)
        if word=="from":
            self.take(); module=self.dotted_name(True); self.take("import"); names=[]
            parenthesized=self.text()=="("
            if parenthesized: self.take("(")
            while True:
                if self.text()=="*":
                    if parenthesized: raise ParseError(f"별표 import는 괄호 안에 둘 수 없습니다 (줄 {line})")
                    self.take("*"); names.append(("*","*"))
                    if self.current()[0]!=tokenize.NEWLINE: raise ParseError(f"별표 import는 별칭이나 다른 이름과 섞을 수 없습니다 (줄 {line})")
                    break
                name=self.take()[1]; alias=name
                if self.text()=="as": self.take(); alias=self.take()[1]
                names.append((name,alias))
                if self.text()!=",": break
                self.take(",")
                if parenthesized and self.text()==")": break
            if parenthesized: self.take(")")
            self.take_newline(); return Node("fromimport",(module,names),line=line)
        if word=="global":
            self.take(); names=[]
            while True:
                names.append(self.take()[1])
                if self.text()!=",": break
                self.take(",")
            self.take_newline(); return Node("global",names,line=line)
        if word=="nonlocal":
            self.take(); names=[]
            while True:
                names.append(self.take()[1])
                if self.text()!=",": break
                self.take(",")
            self.take_newline(); return Node("nonlocal",names,line=line)
        if word=="del":
            self.take(); targets=[]
            while True:
                target=self.expression()
                self.validate_delete_target(target,line)
                targets.append(target)
                if self.text()!=",": break
                self.take(",")
                if self.current()[0]==tokenize.NEWLINE: break
            self.take_newline(); return Node("dels",children=targets,line=line)
        if word=="assert":
            self.take(); condition=self.expression(); message=Node("constant",None,line=line)
            self.require_grouped_namedexpr(condition,line,"assert")
            if self.text()==",": self.take(","); message=self.expression()
            self.take_newline(); return Node("assert",children=[condition,message],line=line)
        if word=="type" and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][0]==tokenize.NAME:
            self.take(); name=self.take()[1]; parameters=self.parse_type_parameters()
            self.take("="); start=self.pos; value=self.expression(); self.reject_namedexpr(value,line,"타입 별칭"); value_text="".join(token[1] for token in self.tokens[start:self.pos]); self.take_newline()
            return Node("type_alias",(name,parameters,value_text),[value],line)
        if word=="def": self.take(); return self.function_statement(line,False)
        if word=="async":
            self.take()
            if self.text()=="def": self.take("def"); return self.function_statement(line,True)
            if self.text()=="for":
                self.take("for"); target=self.loop_target(); self.take("in"); iterable=self.for_iterable_list()
                self.require_grouped_namedexpr(iterable,line,"async for iterable")
                body=self.suite(); other=[]
                if self.text()=="else": self.take(); other=self.suite()
                return Node("async_for",target,[iterable,Node("body",children=body),Node("body",children=other)],line)
            if self.text()=="with":
                self.take("with"); managers=self.parse_managers(line)
                return Node("async_with",None,[Node("managers",children=managers),Node("body",children=self.suite())],line)
            raise ParseError(f"어싱크 뒤에는 데프, 포 또는 위드가 필요합니다 (줄 {line})")
        if word=="class":
            self.take(); name=self.take()[1]; type_parameters=self.parse_type_parameters(); bases=[]; keywords=[]; arguments=[]; saw_keyword=False; saw_kwstar=False
            if self.text()=="(":
                self.take("(")
                if self.text()!=")":
                    while True:
                        if self.text()=="*":
                            if saw_kwstar: raise ParseError(f"클래스 ** 키워드 unpack 뒤에는 * base를 둘 수 없습니다 (줄 {line})")
                            self.take("*"); value=self.expression(); bases.append(Node("starred",children=[value],line=line)); arguments.append(("star",None,value))
                        elif self.text()=="**":
                            self.take("**"); value=self.expression(); keywords.append((None,value)); arguments.append(("kwstar",None,value)); saw_keyword=True; saw_kwstar=True
                        elif self.current()[0]==tokenize.NAME and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][1]=="=":
                            keyword=self.take()[1]
                            if any(existing==keyword for existing,_ in keywords): raise ParseError(f"클래스 키워드 인자 중복: {keyword} (줄 {line})")
                            self.take("="); value=self.expression(); keywords.append((keyword,value)); arguments.append(("keyword",keyword,value)); saw_keyword=True
                        else:
                            if saw_keyword: raise ParseError(f"클래스 키워드 인자 뒤에는 일반 base를 둘 수 없습니다 (줄 {line})")
                            value=self.expression(); bases.append(value); arguments.append(("base",None,value))
                        if self.text()!=",": break
                        self.take(",")
                        if self.text()==")": break
                self.take(")")
            return Node("class",(name,bases,type_parameters,keywords,arguments),self.suite(),line)
        if word=="if":
            self.take(); return self._if_statement(line)
        if word=="while":
            self.take(); test=self.expression(); body=self.suite(); other=[]
            if self.text()=="else": self.take(); other=self.suite()
            return Node("while",None,[test,Node("body",children=body),Node("body",children=other)],line)
        if word=="try":
            self.take(); body=self.suite(); handlers=[]; otherwise=[]; final=[]
            while self.text()=="except":
                handler_line=self.current()[2]; self.take(); is_star=False
                if self.text()=="*": self.take("*"); is_star=True
                type_expression=None; alias=None
                if self.text()!=":":
                    types=[self.expression()]
                    while self.text()==",": self.take(","); types.append(self.expression())
                    type_expression=Node("tuple",children=types,line=handler_line) if len(types)>1 else types[0]
                    if self.text()=="as":
                        if len(types)>1: raise ParseError(f"괄호 없는 다중 예외 타입에는 as를 사용할 수 없습니다 (줄 {handler_line})")
                        self.take(); alias=self.take()[1]
                elif is_star: raise ParseError(f"익셉트*에는 예외 타입이 필요합니다 (줄 {handler_line})")
                handlers.append(Node("except",(type_expression,alias,is_star),self.suite(),handler_line))
            if self.text()=="else":
                if not handlers: raise ParseError(f"익셉트 없는 트라이에는 엘스를 사용할 수 없습니다 (줄 {line})")
                self.take(); otherwise=self.suite()
            if self.text()=="finally": self.take(); final=self.suite()
            if not handlers and not final: raise ParseError(f"트라이는 익셉트 또는 파이널리가 필요합니다 (줄 {line})")
            if any(handler.value[0] is None for handler in handlers[:-1]): raise ParseError(f"타입 없는 익셉트는 마지막이어야 합니다 (줄 {line})")
            if handlers and any(item.value[2] for item in handlers) and not all(item.value[2] for item in handlers): raise ParseError(f"익셉트와 익셉트*는 같은 트라이에서 섞을 수 없습니다 (줄 {line})")
            return Node("try",None,[Node("body",children=body),Node("handlers",children=handlers),Node("body",children=otherwise),Node("body",children=final)],line)
        if word=="with":
            self.take(); managers=self.parse_managers(line)
            return Node("with",None,[Node("managers",children=managers),Node("body",children=self.suite())],line)
        if word=="match" and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][1] not in ("=",":",".",":=","+=","-=","*=","/=","|=","&=","^=") and self.has_suite_colon():
            self.take(); subject=self.for_iterable_list(); self.take(":"); self.take_newline(); self.expect_type(tokenize.INDENT)
            cases=[]; self.skip_newlines()
            while self.text()=="case":
                case_line=self.current()[2]; self.take(); pattern=self.pattern(True); guard=None
                if self.text()=="if": self.take(); guard=self.expression()
                body=self.suite(); cases.append(Node("case",guard,[pattern,Node("body",children=body)],case_line)); self.skip_newlines()
            self.expect_type(tokenize.DEDENT)
            if not cases: raise ParseError(f"매치에는 케이스가 필요합니다 (줄 {line})")
            return Node("match",children=[subject,*cases],line=line)
        if word=="for":
            self.take(); target=self.loop_target(); self.take("in"); iterable=self.for_iterable_list()
            self.require_grouped_namedexpr(iterable,line,"for iterable")
            body=self.suite(); other=[]
            if self.text()=="else": self.take(); other=self.suite()
            return Node("for",target,[iterable,Node("body",children=body),Node("body",children=other)],line)
        if word=="return":
            self.take(); has_value=self.current()[0]!=tokenize.NEWLINE
            value=self.expression_list() if has_value else Node("constant",None,line=line)
            if has_value: self.require_grouped_namedexpr(value,line,"return")
            self.take_newline(); return Node("return",has_value,children=[value],line=line)
        if word=="yield":
            self.take(); delegated=False
            if self.text()=="from": self.take(); delegated=True
            if delegated and self.current()[0]==tokenize.NEWLINE: raise ParseError(f"yield from에는 피연산자가 필요합니다 (줄 {line})")
            value=Node("constant",None,line=line) if self.current()[0]==tokenize.NEWLINE else self.expression() if delegated else self.expression_list()
            self.require_grouped_namedexpr(value,line,"yield")
            self.take_newline(); return Node("yield_from" if delegated else "yield",children=[value],line=line)
        if word=="raise":
            self.take()
            if self.current()[0]==tokenize.NEWLINE:
                self.take_newline(); return Node("reraise",line=line)
            value=self.expression(); cause=None
            self.require_grouped_namedexpr(value,line,"raise")
            if self.text()=="from": self.take(); cause=self.expression()
            if cause is not None: self.require_grouped_namedexpr(cause,line,"raise from")
            self.take_newline(); return Node("raise",children=[value,*([cause] if cause else [])],line=line)
        if word in ("break","continue"):
            self.take(); self.take_newline(); return Node(word,line=line)
        if word=="pass": self.take(); self.take_newline(); return Node("pass",line=line)
        expression=self.expression()
        if self.text()==":" and expression.kind in ("name","attribute","subscript"):
            self.take(":"); annotation_start=self.pos; annotation=self.expression(1); annotation_text="".join(token[1] for token in self.tokens[annotation_start:self.pos]); value=None
            self.reject_namedexpr(annotation,line,"주석")
            if self.text()=="=": self.take("="); value=self.expression_list()
            if value is not None: self.require_grouped_namedexpr(value,line,"주석 대입")
            self.take_newline(); return Node("annassign",annotation_text,[expression,annotation,*([value] if value else [])],line)
        if self.text()==",":
            values=[expression]
            while self.text()==",":
                self.take(",")
                if self.text()=="=": break
                values.append(self.expression())
            expression=Node("tuple",children=values,line=line)
        if self.text() in ("+=","-=","*=","/=","//=","%=","**=","|=","&=","^=","<<=",">>=","@="):
            if expression.kind not in ("name","attribute","subscript"): raise ParseError(f"잘못된 복합 대입 대상 (줄 {line})")
            op=self.take()[1][:-1]; value=self.expression_list(); self.take_newline()
            self.require_grouped_namedexpr(value,line,"복합 대입")
            return Node("augassign",op,[expression,value],line)
        if self.text()=="=":
            if expression.kind not in ("name","attribute","subscript","tuple","list"): raise ParseError(f"잘못된 대입 대상 (줄 {line})")
            targets=[expression]; self.take("="); value=self.expression_list()
            self.require_grouped_namedexpr(value,line,"대입")
            while self.text()=="=":
                if value.kind not in ("name","attribute","subscript"): raise ParseError(f"잘못된 연쇄 대입 대상 (줄 {line})")
                targets.append(value); self.take("="); value=self.expression_list()
            self.take_newline()
            return Node("assign_chain",children=[*targets,value],line=line) if len(targets)>1 else Node("assign",children=[expression,value],line=line)
        self.require_grouped_namedexpr(expression,line,"표현식 문장")
        self.take_newline(); return Node("expr",children=[expression],line=line)

    def expression_list(self):
        line=self.current()[2]; values=[self.expression()]; had_comma=False
        while self.text()==",":
            self.take(","); had_comma=True
            if self.current()[0]==tokenize.NEWLINE or self.text() in (")","]","}",":"): break
            values.append(self.expression())
        return Node("tuple",children=values,line=line) if had_comma else values[0]

    def for_iterable_list(self):
        line=self.current()[2]; values=[self.expression()]; had_comma=False
        while self.text()==",":
            self.take(","); had_comma=True
            if self.text()==":": break
            values.append(self.expression())
        return Node("tuple",children=values,line=line) if had_comma else values[0]

    def parse_managers(self,line):
        managers=[]; parenthesized=self.text()=="("
        if parenthesized: self.take("(")
        if parenthesized and self.text()==")": self.take(")"); return managers
        while True:
            expression=self.expression(); target=None
            if not parenthesized: self.require_grouped_namedexpr(expression,line,"with")
            if self.text()=="as": self.take(); target=self.expression(); self.validate_unpack_target(target,line)
            managers.append(Node("manager",None,[expression] if target is None else [expression,target],line))
            if self.text()!=",": break
            self.take(",")
            if parenthesized and self.text()==")": break
        if parenthesized: self.take(")")
        return managers

    def _if_statement(self,line):
        test=self.expression(); body=self.suite(); other=[]
        if self.text()=="elif":
            self.take(); other=[self._if_statement(self.current()[2])]
        elif self.text()=="else":
            self.take(); other=self.suite()
        return Node("if",None,[test,Node("body",children=body),Node("body",children=other)],line)

    def function_statement(self,line,is_async):
        name=self.take()[1]; type_parameters=self.parse_type_parameters(); self.take("("); params=[]; posonly=[]; kwonly=[]; defaults={}; annotations={}; saw_default=False; vararg=None; kwarg=None; keyword_mode=False
        if self.text()!=")":
            while True:
                if self.text()=="*":
                    self.take("*"); keyword_mode=True
                    if self.text() not in (",",")"):
                        vararg=self.take()[1]
                        if self.text()==":":
                            self.take(":"); start=self.pos; annotation=self.expression(1); self.reject_namedexpr(annotation,line,"함수 주석"); annotations[vararg]=(annotation,"".join(token[1] for token in self.tokens[start:self.pos]))
                    if self.text()==",":
                        self.take(",")
                        if self.text()==")": break
                        continue
                    break
                if self.text()=="**":
                    self.take("**"); kwarg=self.take()[1]
                    if self.text()==":":
                        self.take(":"); start=self.pos; annotation=self.expression(1); self.reject_namedexpr(annotation,line,"함수 주석"); annotations[kwarg]=(annotation,"".join(token[1] for token in self.tokens[start:self.pos]))
                    if self.text()==",": self.take(",")
                    break
                if self.text()=="/":
                    if not params or posonly: raise ParseError(f"잘못된 위치 전용 인자 구분자 (줄 {line})")
                    self.take("/"); posonly=list(params)
                    if self.text()==",":
                        self.take(",")
                        if self.text()==")": break
                        continue
                    break
                parameter=self.take()[1]; (kwonly if keyword_mode else params).append(parameter)
                if self.text()==":":
                    self.take(":"); start=self.pos; annotation=self.expression(1); self.reject_namedexpr(annotation,line,"함수 주석"); annotations[parameter]=(annotation,"".join(token[1] for token in self.tokens[start:self.pos]))
                if self.text()=="=":
                    self.take("="); default=self.expression(); self.require_grouped_namedexpr(default,line,"함수 기본값"); defaults[parameter]=default; saw_default=True
                elif saw_default and not keyword_mode: raise ParseError(f"기본값 없는 인자가 기본값 인자 뒤에 있습니다 (줄 {line})")
                if self.text()!=",": break
                self.take(",")
                if self.text()==")": break
        self.take(")")
        all_parameters=[*params,*kwonly,*([vararg] if vararg else []),*([kwarg] if kwarg else [])]
        duplicate=next((name for name in all_parameters if all_parameters.count(name)>1),None)
        if duplicate is not None: raise ParseError(f"매개변수 이름 중복: {duplicate} (줄 {line})")
        if keyword_mode and vararg is None and not kwonly: raise ParseError(f"단독 * 뒤에는 키워드 전용 매개변수가 필요합니다 (줄 {line})")
        if self.text()=="->":
            self.take("->"); start=self.pos; annotation=self.expression(1); self.reject_namedexpr(annotation,line,"반환 주석"); annotations["return"]=(annotation,"".join(token[1] for token in self.tokens[start:self.pos]))
        return Node("def",(name,params,defaults,vararg,kwarg,kwonly,is_async,posonly,annotations,type_parameters),self.suite(),line)

    def parse_type_parameters(self):
        parameters=[]
        if self.text()!="[": return parameters
        self.take("[")
        if self.text()=="]": raise ParseError("타입 매개변수 목록은 비어 있을 수 없습니다")
        while self.text()!="]":
            kind="typevar"
            if self.text()=="*": self.take("*"); kind="typevartuple"
            elif self.text()=="**": self.take("**"); kind="paramspec"
            name=self.take()[1]; bound=None; default=None; bound_text=None; default_text=None
            if self.text()==":":
                if kind!="typevar": raise ParseError(f"{name} 타입 매개변수 종류에는 바운드를 사용할 수 없습니다")
                self.take(":"); start=self.pos; bound=self.expression(1); self.reject_namedexpr(bound,bound.line,"타입 매개변수 바운드"); bound_text="".join(token[1] for token in self.tokens[start:self.pos])
            if self.text()=="=":
                self.take("="); start=self.pos; default=self.expression(1); self.reject_namedexpr(default,default.line,"타입 매개변수 기본값"); default_text="".join(token[1] for token in self.tokens[start:self.pos])
            parameters.append({"kind":kind,"name":name,"bound":bound,"default":default,"bound_text":bound_text,"default_text":default_text})
            if self.text()!=",": break
            self.take(",")
        self.take("]")
        names=[item["name"] for item in parameters]
        duplicate=next((name for name in names if names.count(name)>1),None)
        if duplicate is not None: raise ParseError(f"타입 매개변수 이름 중복: {duplicate}")
        saw_default=False
        for item in parameters:
            if item["default"] is not None: saw_default=True
            elif saw_default: raise ParseError("기본값 없는 타입 매개변수가 기본값 매개변수 뒤에 있습니다")
        return parameters

    def pattern(self,allow_open_sequence=False):
        line=self.current()[2]; patterns=[self.single_pattern()]
        while self.text()=="|": self.take("|"); patterns.append(self.single_pattern())
        result=Node("pattern_or",children=patterns,line=line) if len(patterns)>1 else patterns[0]
        if self.text()=="as": self.take("as"); result=Node("pattern_as",self.take()[1],[result],line)
        if allow_open_sequence and self.text()==",":
            items=[result]
            while self.text()==",":
                self.take(",")
                if self.text() in (":","if"): break
                if self.text()=="*": self.take("*"); items.append(Node("pattern_star",self.take()[1],line=line))
                else: items.append(self.pattern())
            result=Node("pattern_sequence",children=items,line=line)
        return result

    def single_pattern(self):
        line=self.current()[2]; word=self.text()
        if word=="_": self.take(); return Node("pattern_wildcard",line=line)
        if word in ("[","("):
            opening=word; closing="]" if word=="[" else ")"; self.take(); items=[]; had_comma=False
            if self.text()!=closing:
                while True:
                    if self.text()=="*": self.take("*"); items.append(Node("pattern_star",self.take()[1],line=line))
                    else: items.append(self.pattern())
                    if self.text()!=",": break
                    self.take(","); had_comma=True
                    if self.text()==closing: break
            self.take(closing)
            if opening=="(" and len(items)==1 and not had_comma: return items[0]
            return Node("pattern_sequence",children=items,line=line)
        if word=="{":
            self.take("{"); pairs=[]; rest=None
            if self.text()!="}":
                while True:
                    if self.text()=="**":
                        if rest is not None: raise ParseError(f"매핑 패턴의 ** 캡처는 하나만 허용됩니다 (줄 {line})")
                        self.take("**"); rest=self.take()[1]
                        if rest=="_": raise ParseError(f"매핑 패턴의 **_는 허용되지 않습니다 (줄 {line})")
                        if self.text()==",": self.take(",")
                        if self.text()!="}": raise ParseError(f"매핑 패턴의 ** 캡처는 마지막이어야 합니다 (줄 {line})")
                        break
                    else:
                        key=self.expression(7); self.take(":"); pairs.append(Node("pattern_pair",children=[key,self.pattern()],line=line))
                    if self.text()!=",": break
                    self.take(",")
                    if self.text()=="}": break
            self.take("}"); return Node("pattern_mapping",rest,pairs,line)
        if self.current()[0] in (tokenize.NUMBER,tokenize.STRING) or word in ("-","+") or word in ("True","False","None"):
            value=self.expression(7)
            def fold_numeric(node):
                if node.kind=="constant": return node.value
                if node.kind=="unary" and node.value in ("-","+"): return -fold_numeric(node.children[0]) if node.value=="-" else +fold_numeric(node.children[0])
                if node.kind=="binary" and node.value in ("+","-"):
                    left,right=map(fold_numeric,node.children); return left+right if node.value=="+" else left-right
                raise ValueError
            if value.kind!="constant":
                try: value=Node("constant",fold_numeric(value),line=line)
                except (TypeError,ValueError): pass
            return Node("pattern_literal",children=[value],line=line)
        parts=[self.take()[1]]
        while self.text()==".": self.take("."); parts.append(self.take()[1])
        name=".".join(parts)
        if self.text()=="(":
            self.take("("); positional=[]; keywords=[]; saw_keyword=False
            if self.text()!=")":
                while True:
                    if self.current()[0]==tokenize.NAME and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][1]=="=":
                        attribute=self.take()[1]; self.take("="); keywords.append(Node("pattern_keyword",attribute,[self.pattern()],line)); saw_keyword=True
                    else:
                        if saw_keyword: raise ParseError(f"클래스 키워드 패턴 뒤에는 위치 패턴을 둘 수 없습니다 (줄 {line})")
                        positional.append(self.pattern())
                    if self.text()!=",": break
                    self.take(",")
            self.take(")"); return Node("pattern_class",name,[*positional,*keywords],line)
        if len(parts)>1: return Node("pattern_value",name,line=line)
        return Node("pattern_capture",name,line=line)

    PRECEDENCE={"or":1,"and":2,"|":3,"^":4,"&":5,"==":6,"!=":6,"<>":6,"<":6,"<=":6,">":6,">=":6,"in":6,"is":6,"not in":6,"is not":6,
                "<<":7,">>":7,"+":8,"-":8,"*":9,"/":9,"//":9,"%":9,"@":9,"**":10}
    def expression(self, minimum=0, atom_only=False):
        line=self.current()[2]; word=self.text()
        if word=="not":
            self.take(); left=Node("unary",word,[self.expression(3)],line)
        elif word in ("-","+","~"):
            self.take(); left=Node("unary",word,[self.expression(10)],line)
        elif word=="await":
            self.take(); operand=self.expression(11)
            if operand.kind in ("unary","await","yield_expr","yield_from_expr","lambda","starred","binary","compare_chain","conditional","namedexpr") and not operand.grouped:
                raise ParseError(f"await 뒤에는 primary 표현식 또는 괄호식이 필요합니다 (줄 {line})")
            left=Node("await",children=[operand],line=line)
        elif word=="yield":
            self.take(); delegated=False
            if self.text()=="from": self.take(); delegated=True
            if delegated and self.text() in (")","]",",",":"): raise ParseError(f"yield from에는 피연산자가 필요합니다 (줄 {line})")
            value=Node("constant",None,line=line) if self.text() in (")","]",",",":") else self.expression(1)
            left=Node("yield_from_expr" if delegated else "yield_expr",children=[value],line=line)
        elif word=="*":
            self.take("*"); left=Node("starred",children=[self.expression(10)],line=line)
        elif word=="lambda":
            self.take(); params=[]; posonly=[]; kwonly=[]; defaults={}; vararg=None; kwarg=None; keyword_mode=False; saw_default=False
            if self.text()!=":":
                while True:
                    if self.text()=="*":
                        self.take("*"); keyword_mode=True
                        if self.text() not in (",",":"): vararg=self.take()[1]
                        if self.text()==",":
                            self.take(",")
                            if self.text()==":": break
                            continue
                        break
                    if self.text()=="**":
                        self.take("**"); kwarg=self.take()[1]
                        if self.text()==",": self.take(",")
                        break
                    if self.text()=="/":
                        if not params or posonly: raise ParseError(f"잘못된 위치 전용 인자 구분자 (줄 {line})")
                        self.take("/"); posonly=list(params)
                        if self.text()==",":
                            self.take(",")
                            if self.text()==":": break
                            continue
                        break
                    parameter=self.take()[1]; (kwonly if keyword_mode else params).append(parameter)
                    if self.text()=="=":
                        self.take("="); default=self.expression(1); self.require_grouped_namedexpr(default,line,"lambda 기본값"); defaults[parameter]=default; saw_default=True
                    elif saw_default and not keyword_mode: raise ParseError(f"기본값 없는 인자가 기본값 인자 뒤에 있습니다 (줄 {line})")
                    if self.text()!=",": break
                    self.take(",")
                    if self.text()==":": break
            all_parameters=[*params,*kwonly,*([vararg] if vararg else []),*([kwarg] if kwarg else [])]
            duplicate=next((name for name in all_parameters if all_parameters.count(name)>1),None)
            if duplicate is not None: raise ParseError(f"매개변수 이름 중복: {duplicate} (줄 {line})")
            if keyword_mode and vararg is None and not kwonly: raise ParseError(f"단독 * 뒤에는 키워드 전용 매개변수가 필요합니다 (줄 {line})")
            self.take(":"); signature={"params":params,"posonly":posonly,"kwonly":kwonly,"defaults":defaults,"vararg":vararg,"kwarg":kwarg}
            body=self.expression(1); self.require_grouped_namedexpr(body,line,"lambda 본문"); left=Node("lambda",signature,[body],line)
        elif word=="(":
            self.take()
            if self.text()==")": self.take(")"); left=Node("tuple",children=[],line=line)
            else:
                first=self.expression()
                first.grouped=True
                if self.text() in ("for","async"):
                    left=self.comprehension("generatorexpr",first,line,")")
                    return self.postfix_and_binary(left,minimum)
                elif self.text()==",":
                    values=[first]
                    while self.text()==",":
                        self.take(",")
                        if self.text()==")": break
                        values.append(self.expression())
                    self.take(")"); left=Node("tuple",children=values,line=line)
                else: self.take(")"); left=first
        elif self.current()[0] in (getattr(tokenize,"FSTRING_START",-1),getattr(tokenize,"TSTRING_START",-4)):
            template=self.current()[0]==getattr(tokenize,"TSTRING_START",-4)
            middle_type=getattr(tokenize,"TSTRING_MIDDLE",-5) if template else getattr(tokenize,"FSTRING_MIDDLE",-3)
            end_type=getattr(tokenize,"TSTRING_END",-6) if template else getattr(tokenize,"FSTRING_END",-2)
            self.take(); parts=[]
            while self.current()[0] != end_type:
                if self.current()[0] == middle_type:
                    parts.append(Node("constant",self.take()[1],line=line))
                elif self.text()=="{":
                    opening=self.take("{"); expression_start=self.pos; value=self.expression()
                    expression_text=self.source[opening[4]:self.tokens[self.pos-1][4]]
                    conversion=None; spec=[]; debug_prefix=None; has_spec=False
                    if self.text()=="=":
                        self.take("=")
                        debug_prefix=self.source[opening[4]:self.current()[3]]
                    if self.text()=="!":
                        self.take("!"); conversion=self.take()[1]
                        if conversion not in ("s","r","a"): raise ParseError(f"잘못된 문자열 변환 '!{conversion}' (줄 {line})")
                    if self.text()==":":
                        self.take(":"); has_spec=True
                        while self.text()!="}":
                            if self.current()[0] == middle_type: spec.append(Node("constant",self.take()[1],line=line))
                            elif self.text()=="{":
                                nested_opening=self.take("{"); nested=self.expression(); nested_conversion=None; nested_prefix=None; nested_spec=[]; nested_has_spec=False
                                if self.text()=="=":
                                    self.take("="); nested_prefix=self.source[nested_opening[4]:self.current()[3]]
                                if self.text()=="!":
                                    self.take("!"); nested_conversion=self.take()[1]
                                    if nested_conversion not in ("s","r","a"): raise ParseError(f"잘못된 문자열 변환 '!{nested_conversion}' (줄 {line})")
                                if self.text()==":":
                                    self.take(":"); nested_has_spec=True
                                    while self.text()!="}":
                                        if self.current()[0] == middle_type: nested_spec.append(Node("constant",self.take()[1],line=line))
                                        elif self.text()=="{":
                                            deep_opening=self.take("{"); deep=self.expression(); deep_conversion=None; deep_prefix=None; deep_spec=[]; deep_has_spec=False
                                            if self.text()=="=":
                                                self.take("="); deep_prefix=self.source[deep_opening[4]:self.current()[3]]
                                            if self.text()=="!":
                                                self.take("!"); deep_conversion=self.take()[1]
                                                if deep_conversion not in ("s","r","a"): raise ParseError(f"잘못된 문자열 변환 '!{deep_conversion}' (줄 {line})")
                                            if self.text()==":":
                                                self.take(":"); deep_has_spec=True
                                                while self.text()!="}":
                                                    if self.current()[0] == middle_type: deep_spec.append(Node("constant",self.take()[1],line=line))
                                                    else: raise ParseError(f"형식 지정자 표현식이 너무 깊게 중첩되었습니다 (줄 {line})")
                                            if deep_prefix is not None:
                                                nested_spec.append(Node("constant",deep_prefix,line=line))
                                                if deep_conversion is None and not deep_has_spec: deep_conversion="r"
                                            self.take("}")
                                            deep_children=[deep,*([Node("fstring",children=deep_spec,line=line)] if deep_has_spec else [])]
                                            nested_spec.append(Node("format",deep_conversion,deep_children,line))
                                        else: raise ParseError(f"형식 지정자 표현식이 너무 깊게 중첩되었습니다 (줄 {line})")
                                if nested_prefix is not None:
                                    spec.append(Node("constant",nested_prefix,line=line))
                                    if nested_conversion is None and not nested_has_spec: nested_conversion="r"
                                self.take("}")
                                nested_children=[nested,*([Node("fstring",children=nested_spec,line=line)] if nested_has_spec else [])]
                                spec.append(Node("format",nested_conversion,nested_children,line))
                            else: raise ParseError(f"지원하지 않는 f-string 형식 지정자 (줄 {line})")
                    if debug_prefix is not None:
                        parts.append(Node("constant",debug_prefix,line=line))
                        if conversion is None and not has_spec: conversion="r"
                    children=[value,*([Node("fstring",children=spec,line=line)] if has_spec else [])]
                    parts.append(Node("interpolation",{"conversion":conversion,"expression":expression_text},children,line) if template else Node("format",conversion,children,line)); self.take("}")
                else: raise ParseError(f"지원하지 않는 f-string 형식 (줄 {line})")
            self.take(); left=Node("template" if template else "fstring",children=parts,line=line)
        elif word=="...":
            self.take(); left=Node("constant",Ellipsis,line=line)
        elif self.current()[0] in (tokenize.NUMBER,tokenize.STRING):
            raw=self.take()[1]
            import ast
            value=ast.literal_eval(ast.parse(raw,filename=self.filename,mode="eval").body)
            while self.current()[0]==tokenize.STRING:
                adjacent_raw=self.take()[1]
                adjacent=ast.literal_eval(ast.parse(adjacent_raw,filename=self.filename,mode="eval").body)
                if type(value) is not type(adjacent) or not isinstance(value,(str,bytes)): raise ParseError(f"문자열과 바이트 리터럴은 이어 붙일 수 없습니다 (줄 {line})")
                value+=adjacent
            left=Node("constant",value,line=line)
        elif word in ("True","False","None"):
            self.take(); left=Node("constant",{"True":True,"False":False,"None":None}[word],line=line)
        elif word=="[":
            self.take(); values=[]
            if self.text()!="]":
                first=self.expression()
                if self.text() in ("for","async"):
                    left=self.comprehension("listcomp",first,line,"]")
                    return self.postfix_and_binary(left,minimum)
                values.append(first)
                while self.text()==",":
                    self.take(",")
                    if self.text()=="]": break
                    values.append(self.expression())
            self.take("]"); left=Node("list",children=values,line=line)
        elif word=="{":
            self.take(); pairs=[]
            if self.text()!="}":
                if self.text()=="**":
                    while True:
                        if self.text()=="**":
                            self.take("**"); unpack=self.expression(); self.require_grouped_namedexpr(unpack,line,"dict unpack"); pairs.append(Node("dict_unpack",children=[unpack],line=line))
                        else:
                            key=self.expression(); self.take(":"); value=self.expression()
                            self.require_grouped_namedexpr(key,line,"dict key"); self.require_grouped_namedexpr(value,line,"dict value")
                            pairs.append(Node("pair",children=[key,value],line=line))
                        if self.text()!=",": break
                        self.take(",")
                        if self.text()=="}": break
                    self.take("}"); left=Node("dict",children=pairs,line=line)
                    return self.postfix_and_binary(left,minimum)
                first=self.expression()
                if self.text()==":":
                    self.take(":"); value=self.expression()
                    self.require_grouped_namedexpr(first,line,"dict key"); self.require_grouped_namedexpr(value,line,"dict value")
                    if self.text() in ("for","async"):
                        pair=Node("pair",children=[first,value],line=line)
                        left=self.comprehension("dictcomp",pair,line,"}")
                        return self.postfix_and_binary(left,minimum)
                    pairs.append(Node("pair",children=[first,value],line=line))
                    while self.text()==",":
                        self.take(",")
                        if self.text()=="}": break
                        if self.text()=="**":
                            self.take("**"); unpack=self.expression(); self.require_grouped_namedexpr(unpack,line,"dict unpack"); pairs.append(Node("dict_unpack",children=[unpack],line=line))
                        else:
                            key=self.expression(); self.take(":"); value=self.expression()
                            self.require_grouped_namedexpr(key,line,"dict key"); self.require_grouped_namedexpr(value,line,"dict value")
                            pairs.append(Node("pair",children=[key,value],line=line))
                    self.take("}"); left=Node("dict",children=pairs,line=line)
                else:
                    values=[first]
                    if self.text() in ("for","async"):
                        left=self.comprehension("setcomp",first,line,"}")
                        return self.postfix_and_binary(left,minimum)
                    while self.text()==",":
                        self.take(",")
                        if self.text()=="}": break
                        values.append(self.expression())
                    self.take("}"); left=Node("set",children=values,line=line)
            else: self.take("}"); left=Node("dict",children=[],line=line)
        else:
            left=Node("name",self.take()[1],line=line)
        string_starts=(tokenize.STRING,getattr(tokenize,"FSTRING_START",-1),getattr(tokenize,"TSTRING_START",-4))
        def string_node(node): return node.kind in ("fstring","template") or (node.kind=="constant" and isinstance(node.value,(str,bytes)))
        while string_node(left) and self.current()[0] in string_starts:
            right=self.expression(100,True)
            if not string_node(right): raise ParseError(f"잘못된 인접 문자열 리터럴 (줄 {line})")
            if "template" in (left.kind,right.kind):
                if left.kind!="template" or right.kind!="template": raise ParseError(f"t-string은 다른 문자열 리터럴과 섞을 수 없습니다 (줄 {line})")
                left=Node("template",children=[*left.children,*right.children],line=line)
                continue
            if (left.kind=="constant" and isinstance(left.value,bytes)) or (right.kind=="constant" and isinstance(right.value,bytes)):
                if left.kind!="constant" or right.kind!="constant" or not isinstance(left.value,bytes) or not isinstance(right.value,bytes): raise ParseError(f"바이트와 문자열 리터럴은 섞을 수 없습니다 (줄 {line})")
                left=Node("constant",left.value+right.value,line=line); continue
            left_parts=left.children if left.kind=="fstring" else [Node("constant",left.value,line=line)]
            right_parts=right.children if right.kind=="fstring" else [Node("constant",right.value,line=line)]
            left=Node("fstring",children=[*left_parts,*right_parts],line=line)
        if atom_only: return left
        return self.postfix_and_binary(left,minimum)

    def comprehension(self,kind,element,line,closing):
        clauses=[]
        while self.text() in ("for","async"):
            is_async=self.text()=="async"
            if is_async: self.take("async")
            self.take("for"); target=self.loop_target(); self.take("in"); iterable=self.expression(1)
            filters=[]
            while self.text()=="if": self.take(); filters.append(self.expression(1))
            clauses.append(Node("comp_clause",(target,is_async),[iterable,*filters],line))
        self.take(closing)
        return Node(kind,None,[element,*clauses],line)

    def loop_target(self):
        line=self.current()[2]; first=self.expression(7); values=[first]; had_comma=False
        while self.text()==",":
            self.take(","); had_comma=True
            if self.text()=="in": break
            values.append(self.expression(7))
        target=Node("tuple",children=values,line=line) if had_comma else first
        if target.kind not in ("name","tuple","list","starred","attribute","subscript"): raise ParseError(f"잘못된 반복 대입 대상 (줄 {line})")
        self.validate_unpack_target(target,line)
        return target

    def subscript_item(self,line):
        start=Node("constant",None,line=line) if self.text()==":" else self.expression()
        if self.text()!=":": return start
        if start.kind=="starred": raise ParseError(f"slice 경계에는 별표 표현식을 사용할 수 없습니다 (줄 {line})")
        self.take(":")
        stop=Node("constant",None,line=line) if self.text() in (":",",","]") else self.expression()
        if stop.kind=="starred": raise ParseError(f"slice 경계에는 별표 표현식을 사용할 수 없습니다 (줄 {line})")
        step=Node("constant",None,line=line)
        if self.text()==":":
            self.take(":"); step=Node("constant",None,line=line) if self.text() in (",","]") else self.expression()
            if step.kind=="starred": raise ParseError(f"slice 경계에는 별표 표현식을 사용할 수 없습니다 (줄 {line})")
        return Node("slice",children=[start,stop,step],line=line)

    def postfix_and_binary(self,left,minimum):
        line=left.line
        while self.text() in ("(", ".", "["):
            if self.text()=="(":
                self.take(); args=[]; descriptors=[]; closed=False; saw_keyword=False; saw_kwstar=False
                if self.text()!=")":
                    while True:
                        if self.current()[0]==tokenize.NAME and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][1]=="=":
                            keyword=self.take()[1]
                            if any(item[0]=="keyword" and item[1]==keyword for item in descriptors): raise ParseError(f"키워드 인자 중복: {keyword} (줄 {line})")
                            self.take("="); value=self.expression(); self.require_grouped_namedexpr(value,line,"키워드 인자"); args.append(value); descriptors.append(["keyword",keyword]); saw_keyword=True
                        elif self.text()=="*":
                            if saw_kwstar: raise ParseError(f"** 키워드 unpack 뒤에는 * 위치 unpack을 둘 수 없습니다 (줄 {line})")
                            self.take("*"); args.append(self.expression()); descriptors.append(["star",None])
                        elif self.text()=="**":
                            self.take("**"); args.append(self.expression()); descriptors.append(["kwstar",None]); saw_keyword=True; saw_kwstar=True
                        else:
                            if saw_keyword: raise ParseError(f"키워드 인자 뒤에는 일반 위치 인자를 둘 수 없습니다 (줄 {line})")
                            argument=self.expression()
                            if self.text() in ("for","async"):
                                argument=self.comprehension("generatorexpr",argument,line,")"); closed=True
                            args.append(argument); descriptors.append(["positional",None])
                            if closed: break
                        if self.text()!=",": break
                        self.take(",")
                        if self.text()==")": break
                if not closed: self.take(")")
                left=Node("call",descriptors,[left,*args],line=line)
            elif self.text()==".":
                self.take("."); left=Node("attribute",self.take()[1],[left],line)
            else:
                self.take("[")
                if self.text() in ("]",","): raise ParseError(f"첨자에는 하나 이상의 항목이 필요합니다 (줄 {line})")
                values=[self.subscript_item(line)]; had_comma=False
                while self.text()==",":
                    self.take(","); had_comma=True
                    if self.text()=="]": break
                    values.append(self.subscript_item(line))
                index=Node("tuple",children=values,line=line) if had_comma or values[0].kind=="starred" else values[0]
                self.take("]")
                left=Node("subscript",children=[left,index],line=line)
        while True:
            compound=None
            if self.text()=="is" and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][1]=="not": compound="is not"
            if self.text()=="not" and self.pos+1<len(self.tokens) and self.tokens[self.pos+1][1]=="in": compound="not in"
            candidate=compound or self.text()
            if candidate not in self.PRECEDENCE or self.PRECEDENCE[candidate]<minimum: break
            if candidate=="!=" and "barry_as_FLUFL" in self.future_features: raise ParseError(f"barry_as_FLUFL에서는 != 대신 <>를 사용해야 합니다 (줄 {line})")
            if candidate=="<>" and "barry_as_FLUFL" not in self.future_features: break
            if compound: self.take(); self.take(); op=compound
            else: op=self.take()[1]
            if op=="<>": op="!="
            precedence=self.PRECEDENCE[op]
            right=self.expression(precedence+(0 if op=="**" else 1))
            comparisons={"==","!=","<","<=",">",">=","in","is","not in","is not"}
            if op in comparisons:
                if left.kind=="compare_chain": left.value.append(op); left.children.append(right)
                else: left=Node("compare_chain",[op],[left,right],line)
            else: left=Node("binary",op,[left,right],line)
        if left.kind=="compare_chain" and len(left.value)==1:
            left=Node("binary",left.value[0],left.children,line)
        if minimum<=0 and self.text()==":=":
            if left.kind!="name": raise ParseError(f"바다코끼리 대입 대상은 이름이어야 합니다 (줄 {line})")
            self.take(":="); left=Node("namedexpr",left.value,[self.expression()],line)
        if minimum<=0 and self.text()=="if":
            self.take(); condition=self.expression(); self.take("else"); otherwise=self.expression()
            left=Node("conditional",children=[condition,left,otherwise],line=line)
        return left

def parse(source: str, filename: str = "<하이썬>") -> Node: return Parser(source,filename).parse()
