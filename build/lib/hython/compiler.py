"""Bootstrap compiler from Hython source into independent HBC instructions."""
from __future__ import annotations
import io
import tokenize
from .bytecode import CodeObject
from .hir import HIRCode, optimize_hir
from .frontend import Node, parse

class CompileError(SyntaxError):
    pass

def _target_names(node:Node) -> set[str]:
    if node.kind=="name": return {node.value}
    if node.kind=="starred": return _target_names(node.children[0])
    if node.kind in ("tuple","list"):
        result=set()
        for child in node.children: result.update(_target_names(child))
        return result
    return set()

def _find_nodes(node:Node,kinds:set[str]) -> list[Node]:
    found=[node] if node.kind in kinds else []
    if node.kind in ("def","class","lambda"): return found
    for child in node.children: found.extend(_find_nodes(child,kinds))
    return found

def _find_nodes_deep(node:Node,kinds:set[str]) -> list[Node]:
    """Find syntax even across nested scope nodes when the grammar rule is lexical."""
    found=[node] if node.kind in kinds else []
    for child in node.children: found.extend(_find_nodes_deep(child,kinds))
    return found

def _scope_bindings(nodes:list[Node]) -> set[str]:
    result=set()
    for node in nodes:
        if node.kind in ("def","class"):
            result.add(node.value[0]); continue
        if node.kind=="assign": result.update(_target_names(node.children[0]))
        elif node.kind=="annassign": result.update(_target_names(node.children[0]))
        elif node.kind=="augassign": result.update(_target_names(node.children[0]))
        elif node.kind=="assign_chain":
            for target in node.children[:-1]: result.update(_target_names(target))
        elif node.kind in ("del","dels"):
            for target in (node.children if node.kind=="dels" else node.children[:1]): result.update(_target_names(target))
        elif node.kind in ("for","async_for"): result.update(_target_names(node.value))
        elif node.kind in ("with","async_with"):
            for item in node.children[0].children:
                if len(item.children)>1: result.update(_target_names(item.children[1]))
        elif node.kind=="try":
            for handler in node.children[1].children:
                if handler.value[1]: result.add(handler.value[1])
        elif node.kind=="type_alias": result.add(node.value[0])
        elif node.kind in ("pattern_capture","pattern_star") and node.value!="_": result.add(node.value)
        elif node.kind in ("import","imports"):
            imports=[node.value] if node.kind=="import" else node.value
            result.update(alias for _,alias in imports)
        elif node.kind=="fromimport": result.update(alias for name,alias in node.value[1] if name!="*")
        elif node.kind=="namedexpr": result.add(node.value)
        for child in node.children: result.update(_scope_bindings([child]))
    return result

def _scope_declarations(nodes:list[Node]):
    globals_=set(); nonlocals=set()
    def visit(node):
        if node.kind in ("def","class","lambda"): return
        if node.kind=="global": globals_.update(node.value); return
        if node.kind=="nonlocal": nonlocals.update(node.value); return
        for child in node.children: visit(child)
    for node in nodes: visit(node)
    return globals_,nonlocals

def _validate_declarations(nodes:list[Node],parameters=frozenset()):
    globals_=set(); nonlocals=set(); seen={}
    def mark(name,line,kind): seen.setdefault(name,(line,kind))
    def target(node,line):
        if node.kind=="name": mark(node.value,line,"대입"); return
        if node.kind=="starred": target(node.children[0],line); return
        if node.kind in ("tuple","list"):
            for child in node.children: target(child,line)
            return
        for child in node.children: visit(child)
    def definition_inputs(node):
        if node.kind=="def":
            for value in node.value[2].values(): visit(value)
        elif node.kind=="class":
            descriptors=node.value[4] if len(node.value)>4 else []
            if descriptors:
                for descriptor in descriptors: visit(descriptor[2])
            else:
                for base in node.value[1]: visit(base)
    def visit(node):
        if node.kind=="global":
            for name in node.value:
                if name in parameters: raise CompileError(f"매개변수와 글로벌 선언 충돌: {name} (줄 {node.line})")
                if name in nonlocals: raise CompileError(f"글로벌과 논로컬 선언 충돌: {name} (줄 {node.line})")
                if name in seen: raise CompileError(f"{seen[name][1]} 뒤의 글로벌 선언: {name} (줄 {node.line})")
                globals_.add(name)
            return
        if node.kind=="nonlocal":
            for name in node.value:
                if name in parameters: raise CompileError(f"매개변수와 논로컬 선언 충돌: {name} (줄 {node.line})")
                if name in globals_: raise CompileError(f"글로벌과 논로컬 선언 충돌: {name} (줄 {node.line})")
                if name in seen: raise CompileError(f"{seen[name][1]} 뒤의 논로컬 선언: {name} (줄 {node.line})")
                nonlocals.add(name)
            return
        if node.kind in ("def","class"):
            definition_inputs(node)
            mark(node.value[0],node.line,"대입"); return
        if node.kind=="decorated":
            for decorator in node.children[:-1]: visit(decorator)
            target_node=node.children[-1]; definition_inputs(target_node); mark(target_node.value[0],target_node.line,"대입"); return
        if node.kind=="assign": visit(node.children[1]); target(node.children[0],node.line); return
        if node.kind=="assign_chain":
            visit(node.children[-1])
            for item in node.children[:-1]: target(item,node.line)
            return
        if node.kind=="augassign": visit(node.children[0]); visit(node.children[1]); target(node.children[0],node.line); return
        if node.kind in ("for","async_for"):
            visit(node.children[0]); target(node.value,node.line)
            for child in node.children[1:]: visit(child)
            return
        if node.kind=="name": mark(node.value,node.line,"사용"); return
        for child in node.children: visit(child)
    for node in nodes: visit(node)

def _validate_future_imports(nodes:list[Node]) -> None:
    import __future__
    known=set(__future__.all_feature_names)
    future_zone=True
    for index,node in enumerate(nodes):
        is_future=node.kind=="fromimport" and node.value[0]=="__future__"
        if is_future:
            if not future_zone: raise CompileError(f"__future__ import는 파일 시작 부분에 있어야 합니다 (줄 {node.line})")
            for name,_ in node.value[1]:
                if name=="braces": raise CompileError(f"future 기능 braces는 지원될 가능성이 없습니다 (줄 {node.line})")
                if name not in known: raise CompileError(f"정의되지 않은 future 기능: {name} (줄 {node.line})")
            continue
        is_docstring=index==0 and node.kind=="expr" and node.children and node.children[0].kind=="constant" and isinstance(node.children[0].value,str)
        if not is_docstring: future_zone=False
        def reject_nested(current):
            if current.kind=="fromimport" and current.value[0]=="__future__": raise CompileError(f"__future__ import는 파일 시작 부분에 있어야 합니다 (줄 {current.line})")
            for child in current.children: reject_nested(child)
        reject_nested(node)

def _validate_context(nodes:list[Node],in_function=False,in_async=False,enclosing=(),current_scope=frozenset(),in_class=False,in_except_star=False,in_async_generator=False,loop_depth=0):
    for node in nodes:
        if node.kind=="return" and not in_function: raise CompileError(f"함수 밖의 리턴 (줄 {node.line})")
        if node.kind=="return" and in_async_generator and bool(node.value): raise CompileError(f"비동기 제너레이터는 값을 리턴할 수 없습니다 (줄 {node.line})")
        if in_except_star and node.kind in ("return","break","continue"): raise CompileError(f"익셉트* 안의 {node.kind}는 허용되지 않습니다 (줄 {node.line})")
        if node.kind in ("yield","yield_from","yield_expr","yield_from_expr") and not in_function: raise CompileError(f"함수 밖의 일드 (줄 {node.line})")
        if in_async and node.kind in ("yield_from","yield_from_expr"): raise CompileError(f"어싱크 함수 안의 yield from은 허용되지 않습니다 (줄 {node.line})")
        if node.kind in ("break","continue") and loop_depth==0: raise CompileError(f"루프 밖의 {node.kind} (줄 {node.line})")
        if node.kind=="fromimport" and (in_function or in_class) and any(name=="*" for name,_ in node.value[1]): raise CompileError(f"모듈 범위 밖의 import *는 허용되지 않습니다 (줄 {node.line})")
        if node.kind=="await" and not in_async: raise CompileError(f"어싱크 함수 밖의 어웨이트 (줄 {node.line})")
        if node.kind in ("async_for","async_with") and not in_async: raise CompileError(f"어싱크 함수 밖의 {node.kind} (줄 {node.line})")
        if node.kind in ("listcomp","setcomp","dictcomp") and not in_async and any(clause.value[1] for clause in node.children[1:] if clause.kind=="comp_clause"):
            raise CompileError(f"어싱크 함수 밖의 비동기 컴프리헨션 (줄 {node.line})")
        if node.kind in ("listcomp","setcomp","dictcomp","generatorexpr"):
            clauses=[clause for clause in node.children[1:] if clause.kind=="comp_clause"]
            iteration_names=set()
            for clause in clauses: iteration_names.update(_target_names(clause.value[0]))
            named=_find_nodes(node,{"namedexpr"}); named_names={item.value for item in named}
            if iteration_names & named_names: raise CompileError(f"컴프리헨션 반복 변수는 :=로 다시 바인딩할 수 없습니다 (줄 {node.line})")
            if any(_find_nodes_deep(clause.children[0],{"namedexpr"}) for clause in clauses): raise CompileError(f"컴프리헨션 iterable 안의 :=는 허용되지 않습니다 (줄 {node.line})")
            if _find_nodes(node,{"yield","yield_from","yield_expr","yield_from_expr"}): raise CompileError(f"컴프리헨션 안의 일드는 허용되지 않습니다 (줄 {node.line})")
            if in_class and named: raise CompileError(f"클래스 컴프리헨션 안의 :=는 허용되지 않습니다 (줄 {node.line})")
        if node.kind=="nonlocal":
            for name in node.value:
                if not any(name in scope for scope in enclosing): raise CompileError(f"바인딩되지 않은 논로컬 이름: {name} (줄 {node.line})")
        if node.kind=="def":
            params=node.value[1]; vararg=node.value[3]; kwarg=node.value[4]; kwonly=node.value[5]
            bindings=_scope_bindings(node.children)|set(params)|set(kwonly)
            if vararg: bindings.add(vararg)
            if kwarg: bindings.add(kwarg)
            _validate_declarations(node.children,frozenset(set(params)|set(kwonly)|({vararg} if vararg else set())|({kwarg} if kwarg else set())))
            outer=(*enclosing,current_scope) if in_function else enclosing
            is_async_generator=node.value[6] and any(_find_nodes(item,{"yield","yield_from","yield_expr","yield_from_expr"}) for item in node.children)
            _validate_context(node.children,True,node.value[6],outer,frozenset(bindings),False,False,is_async_generator,0); continue
        if node.kind=="class":
            _validate_declarations(node.children)
            outer=(*enclosing,current_scope) if in_function else enclosing
            _validate_context(node.children,False,False,outer,frozenset(),True,False,False,0); continue
        if node.kind=="lambda":
            outer=(*enclosing,current_scope) if in_function else enclosing
            _validate_context(node.children,True,False,outer,frozenset(),False,False,False,0); continue
        if node.kind=="except":
            _validate_context(node.children,in_function,in_async,enclosing,current_scope,in_class,in_except_star or node.value[2],in_async_generator,loop_depth); continue
        if node.kind in ("for","async_for","while"):
            _validate_context(node.children[:1],in_function,in_async,enclosing,current_scope,in_class,in_except_star,in_async_generator,loop_depth)
            _validate_context(node.children[1:2],in_function,in_async,enclosing,current_scope,in_class,in_except_star,in_async_generator,loop_depth+1)
            _validate_context(node.children[2:],in_function,in_async,enclosing,current_scope,in_class,in_except_star,in_async_generator,loop_depth)
            continue
        _validate_context(node.children,in_function,in_async,enclosing,current_scope,in_class,in_except_star,in_async_generator,loop_depth)

class Compiler:
    def __init__(self, name: str = "<모듈>", parameters: list[str] | None = None, signal_returns: bool = False,
                 evaluate_annotations: bool = True, private_class: str | None = None):
        self.private_class=private_class
        self.code = HIRCode(name, [self.mangle(item) for item in (parameters or [])], [], [])
        self.loops: list[tuple[int,list[int],bool]] = []
        self.global_names: set[str] = set()
        self.nonlocal_names: set[str] = set()
        self.temp_counter=0
        self.signal_returns=signal_returns
        self.evaluate_annotations=evaluate_annotations
        self.current_line=0
        self.defer_definition_store=False
        self.definition_firstlineno=None

    def mangle(self,name:str) -> str:
        if not self.private_class or not isinstance(name,str) or not name.startswith("__") or name.endswith("__") or "." in name: return name
        class_name=self.private_class.lstrip("_")
        return f"_{class_name}{name}" if class_name else name

    def mangle_path(self,path:str) -> str:
        return ".".join(self.mangle(part) for part in path.split("."))

    def emit(self, op: str, arg=None) -> int:
        instruction = [op] if arg is None else [op, arg]
        self.code.instructions.append(instruction)
        self.code.lines.append(self.current_line)
        return len(self.code.instructions) - 1

    def patch(self, index: int, target: int) -> None:
        self.code.instructions[index][1] = target

    def name_scope(self,name:str) -> str:
        name=self.mangle(name)
        return "global" if name in self.global_names else "nonlocal" if name in self.nonlocal_names else "local"

    def store_name(self,name:str) -> None:
        name=self.mangle(name)
        self.emit("STORE_GLOBAL" if name in self.global_names else "STORE_NONLOCAL" if name in self.nonlocal_names else "STORE",name)

    def delete_target(self,target:Node) -> None:
        if target.kind in ("tuple","list"):
            for child in target.children: self.delete_target(child)
        elif target.kind=="name":
            name=self.mangle(target.value); self.emit("DELETE_GLOBAL" if name in self.global_names else "DELETE_NONLOCAL" if name in self.nonlocal_names else "DELETE",name)
        elif target.kind=="attribute": self.expression(target.children[0]); self.emit("DELETE_ATTR",self.mangle(target.value))
        elif target.kind=="subscript": self.expression(target.children[0]); self.expression(target.children[1]); self.emit("DELETE_ITEM")
        else: self.unsupported(target)

    def constant(self, value) -> int:
        self.code.constants.append(value)
        return len(self.code.constants) - 1

    @staticmethod
    def docstring(nodes:list[Node]):
        if nodes and nodes[0].kind=="expr" and nodes[0].children and nodes[0].children[0].kind=="constant" and isinstance(nodes[0].children[0].value,str):
            return nodes[0].children[0].value
        return None

    @staticmethod
    def annotation_node(value): return value[0] if isinstance(value,tuple) else value
    def annotation_text(self,value):
        text=value[1] if isinstance(value,tuple) else ""
        if not self.private_class or "__" not in text: return text
        replacements=[]
        try:
            tokens=tokenize.generate_tokens(io.StringIO(text).readline)
            for token in tokens:
                if token.type==tokenize.NAME:
                    mangled=self.mangle(token.string)
                    if mangled!=token.string: replacements.append((token.start[1],token.end[1],mangled))
        except (IndentationError,tokenize.TokenError):
            return text
        for start,end,replacement in reversed(replacements): text=text[:start]+replacement+text[end:]
        return text

    @staticmethod
    def static_attributes(nodes:list[Node]) -> list[str]:
        names=set()
        def target(node):
            if node.kind=="attribute" and node.children and node.children[0].kind=="name" and node.children[0].value=="self": names.add(node.value)
            elif node.kind=="starred": target(node.children[0])
            elif node.kind in ("tuple","list"):
                for child in node.children: target(child)
        def visit(node,inside_function=False):
            if node.kind=="class": return
            if node.kind=="decorated":
                visit(node.children[-1],inside_function); return
            if node.kind in ("def","lambda"):
                for child in node.children: visit(child,True)
                return
            if not inside_function: return
            if node.kind in ("assign","annassign","augassign") and (node.kind!="annassign" or len(node.children)>2): target(node.children[0])
            elif node.kind=="assign_chain":
                for item in node.children[:-1]: target(item)
            elif node.kind in ("for","async_for"): target(node.value)
            elif node.kind in ("with","async_with"):
                for item in node.children[0].children:
                    if len(item.children)>1: target(item.children[1])
            for child in node.children: visit(child,inside_function)
        for node in nodes: visit(node)
        return sorted(names)

    def expression_code(self,node:Node,label:str) -> HIRCode:
        child=self.scope_child(f"{self.code.name}:{label}")
        child.expression(node); child.emit("RETURN")
        return child.code

    def scope_child(self,name:str,signal_returns:bool=False) -> "Compiler":
        child=Compiler(name,[],signal_returns,evaluate_annotations=self.evaluate_annotations,private_class=self.private_class)
        child.global_names=set(self.global_names)
        child.nonlocal_names=set(self.nonlocal_names)
        return child

    @staticmethod
    def has_yield(nodes:list[Node]) -> bool:
        for node in nodes:
            if node.kind in ("yield","yield_from","yield_expr","yield_from_expr"): return True
            if node.kind not in ("def","class","lambda") and Compiler.has_yield(node.children): return True
        return False

    @staticmethod
    def has_await(nodes:list[Node]) -> bool:
        for node in nodes:
            if node.kind=="await": return True
            if node.kind not in ("def","class","lambda") and Compiler.has_await(node.children): return True
        return False

    @staticmethod
    def named_expression_targets(node:Node) -> set[str]:
        if node.kind=="namedexpr": return {node.value} | Compiler.named_expression_targets(node.children[0])
        if node.kind in ("lambda","def","class"): return set()
        result=set()
        for child in node.children: result.update(Compiler.named_expression_targets(child))
        return result

    def pattern_spec(self,node:Node):
        if node.kind=="pattern_wildcard": return {"kind":"wildcard"}
        if node.kind=="pattern_capture": return {"kind":"capture","name":self.mangle(node.value),"scope":self.name_scope(node.value)}
        if node.kind=="pattern_literal":
            value=node.children[0]
            if value.kind!="constant": self.unsupported(value)
            return {"kind":"singleton" if value.value is None or type(value.value) is bool else "literal","value":value.value}
        if node.kind=="pattern_or": return {"kind":"or","items":[self.pattern_spec(item) for item in node.children]}
        if node.kind=="pattern_as": return {"kind":"as","name":self.mangle(node.value),"scope":self.name_scope(node.value),"pattern":self.pattern_spec(node.children[0])}
        if node.kind=="pattern_value": return {"kind":"value","path":self.mangle_path(node.value)}
        if node.kind=="pattern_sequence": return {"kind":"sequence","items":[self.pattern_spec(item) for item in node.children]}
        if node.kind=="pattern_star": return {"kind":"star","name":self.mangle(node.value),"scope":self.name_scope(node.value)}
        if node.kind=="pattern_mapping":
            pairs=[]
            for pair in node.children:
                key=pair.children[0]
                literal=None; is_literal=False
                if key.kind=="constant": literal=key.value; is_literal=True
                elif key.kind=="unary" and key.value in ("+","-") and key.children[0].kind=="constant" and isinstance(key.children[0].value,(int,float,complex)):
                    literal=key.children[0].value if key.value=="+" else -key.children[0].value; is_literal=True
                elif key.kind=="binary" and key.value in ("+","-") and all(child.kind=="constant" for child in key.children):
                    left,right=(child.value for child in key.children)
                    if isinstance(left,(int,float)) and isinstance(right,complex) and right.real==0:
                        literal=left+right if key.value=="+" else left-right; is_literal=True
                if is_literal: key_spec={"kind":"literal","value":literal}
                else:
                    parts=[]; current=key
                    while current.kind=="attribute": parts.append(current.value); current=current.children[0]
                    if current.kind!="name" or not parts: self.unsupported(key)
                    key_spec={"kind":"value","path":self.mangle_path(".".join([current.value,*reversed(parts)]))}
                pairs.append({"key":key_spec,"pattern":self.pattern_spec(pair.children[1])})
            literal_keys=[item["key"]["value"] for item in pairs if item["key"]["kind"]=="literal"]
            if len(literal_keys)!=len(set(literal_keys)): raise CompileError(f"매핑 패턴 키 중복 (줄 {node.line})")
            return {"kind":"mapping","pairs":pairs,"rest":self.mangle(node.value) if node.value else node.value,"rest_scope":self.name_scope(node.value) if node.value else "local"}
        if node.kind=="pattern_class":
            positional=[]; keywords=[]
            for item in node.children:
                if item.kind=="pattern_keyword": keywords.append({"name":item.value,"pattern":self.pattern_spec(item.children[0])})
                else: positional.append(self.pattern_spec(item))
            return {"kind":"class","name":self.mangle_path(node.value),"positional":positional,"keywords":keywords}
        self.unsupported(node)

    def validate_pattern(self,node:Node) -> set[str]:
        if node.kind in ("pattern_wildcard","pattern_literal","pattern_value"): return set()
        if node.kind in ("pattern_capture","pattern_star"):
            return set() if node.value=="_" else {node.value}
        if node.kind=="pattern_as":
            if node.value=="_": raise CompileError(f"AS 패턴의 대상은 _일 수 없습니다 (줄 {node.line})")
            names=self.validate_pattern(node.children[0])
            if node.value!="_":
                if node.value in names: raise CompileError(f"패턴 이름 중복: {node.value} (줄 {node.line})")
                names.add(node.value)
            return names
        if node.kind=="pattern_or":
            alternatives=[self.validate_pattern(item) for item in node.children]
            if any(names!=alternatives[0] for names in alternatives[1:]): raise CompileError(f"OR 패턴의 이름 바인딩이 일치하지 않습니다 (줄 {node.line})")
            if any(self.irrefutable_pattern(item) for item in node.children[:-1]): raise CompileError(f"OR 패턴의 모든 값을 잡는 대안은 마지막이어야 합니다 (줄 {node.line})")
            return alternatives[0]
        names=set()
        children=node.children
        if node.kind=="pattern_sequence" and sum(child.kind=="pattern_star" for child in children)>1: raise CompileError(f"시퀀스 패턴에는 별표가 하나만 허용됩니다 (줄 {node.line})")
        if node.kind=="pattern_mapping":
            keys=[pair.children[0].value for pair in children if pair.children[0].kind=="constant"]
            if len(keys)!=len(set(keys)): raise CompileError(f"매핑 패턴 키 중복 (줄 {node.line})")
        if node.kind=="pattern_class":
            keywords=[child.value for child in children if child.kind=="pattern_keyword"]
            if len(keywords)!=len(set(keywords)): raise CompileError(f"클래스 패턴 키워드 중복 (줄 {node.line})")
        if node.kind=="pattern_mapping" and node.value:
            if node.value!="_": names.add(node.value)
        for child in children:
            if child.kind=="pattern_pair": child=child.children[1]
            elif child.kind=="pattern_keyword": child=child.children[0]
            child_names=self.validate_pattern(child)
            duplicate=names & child_names
            if duplicate: raise CompileError(f"패턴 이름 중복: {next(iter(duplicate))} (줄 {node.line})")
            names.update(child_names)
        return names

    @staticmethod
    def irrefutable_pattern(node:Node) -> bool:
        if node.kind in ("pattern_wildcard","pattern_capture"): return True
        if node.kind=="pattern_as": return Compiler.irrefutable_pattern(node.children[0])
        if node.kind=="pattern_or": return any(Compiler.irrefutable_pattern(item) for item in node.children)
        return False

    def target_spec(self,node:Node):
        if node.kind=="name": return {"kind":"name","name":self.mangle(node.value),"scope":self.name_scope(node.value)}
        if node.kind=="starred": return {"kind":"starred","target":self.target_spec(node.children[0])}
        if node.kind in ("tuple","list"): return {"kind":"sequence","items":[self.target_spec(item) for item in node.children]}
        if node.kind=="attribute": return {"kind":"attribute","name":self.mangle(node.value),"object":self.expression_code(node.children[0],"target-object").to_dict()}
        if node.kind=="subscript": return {"kind":"subscript","object":self.expression_code(node.children[0],"target-object").to_dict(),"index":self.expression_code(node.children[1],"target-index").to_dict()}
        self.unsupported(node)

    def type_parameter_payload(self,item):
        if isinstance(item,(list,tuple)): kind,name=item; return {"kind":kind,"name":name,"bound":None,"default":None}
        return {"kind":item["kind"],"name":item["name"],
                "bound":self.expression_code(item["bound"],"type-bound").to_dict() if item["bound"] and item.get("bound_text") is None else None,
                "default":self.expression_code(item["default"],"type-default").to_dict() if item["default"] and item.get("default_text") is None else None,
                "bound_text":item.get("bound_text"),"default_text":item.get("default_text")}

    def compile_body(self, body: list[Node]) -> HIRCode:
        globals_,nonlocals=_scope_declarations(body)
        self.global_names.update(globals_); self.nonlocal_names.update(nonlocals)
        for node in body:
            self.statement(node)
        self.emit("CONST", self.constant(None))
        self.emit("RETURN")
        return self.code

    def statement(self, node: Node) -> None:
        self.current_line=node.line
        if node.kind == "expr":
            self.expression(node.children[0]); self.emit("POP")
        elif node.kind in ("import","imports"):
            imports=[node.value] if node.kind=="import" else node.value
            for module,alias in imports:
                self.emit("IMPORT",module)
                if "." in module and alias==module.split(".")[0]:
                    self.emit("POP"); self.emit("IMPORT",module.split(".")[0])
                self.store_name(alias)
        elif node.kind == "fromimport":
            module,names=node.value
            for name,alias in names:
                if name=="*": self.emit("IMPORT",module); self.emit("IMPORT_STAR")
                else: self.emit("IMPORT_FROM",{"module":module,"name":name}); self.store_name(alias)
        elif node.kind == "global": self.global_names.update(self.mangle(name) for name in node.value)
        elif node.kind == "nonlocal": self.nonlocal_names.update(self.mangle(name) for name in node.value)
        elif node.kind in ("del","dels"):
            targets=node.children if node.kind=="dels" else [node.children[0]]
            for target in targets: self.delete_target(target)
        elif node.kind == "assert":
            self.expression(node.children[0]); failure=self.emit("JUMP_FALSE",-1); end=self.emit("JUMP",-1)
            self.patch(failure,len(self.code.instructions)); self.emit("CONST",self.constant(False)); self.expression(node.children[1]); self.emit("ASSERT")
            self.patch(end,len(self.code.instructions))
        elif node.kind == "type_alias":
            name,parameters,*text=node.value
            self.emit("MAKE_TYPE_ALIAS",{"name":name,"parameters":[self.type_parameter_payload(item) for item in parameters],"value":self.expression_code(node.children[0],"type-alias").to_dict(),"value_text":text[0] if text else None}); self.store_name(name)
        elif node.kind == "assign":
            target, value = node.children
            self.expression(value); self.store_target(target)
        elif node.kind == "assign_chain":
            targets=node.children[:-1]; self.expression(node.children[-1])
            for index,target in enumerate(targets):
                if index<len(targets)-1: self.emit("DUP")
                self.store_target(target)
        elif node.kind == "annassign":
            target,annotation=node.children[:2]
            if len(node.children)>2:
                value=node.children[2]
                self.expression(value); self.store_target(target)
            elif target.kind=="attribute":
                self.expression(target.children[0]); self.emit("POP")
            elif target.kind=="subscript":
                self.expression(target.children[0]); self.emit("POP")
                self.expression(target.children[1]); self.emit("POP")
            if target.kind=="name" and self.evaluate_annotations:
                annotation_name=self.mangle(target.value)
                self.emit("ANNOTATE_LAZY",{"name":annotation_name,"text":node.value or "","code":self.expression_code(annotation,f"annotation-{annotation_name}").to_dict()})
        elif node.kind == "augassign":
            operator=node.value; target,value=node.children
            opcode={"+":"IADD","-":"ISUB","*":"IMUL","/":"IDIV","//":"IFLOORDIV","%":"IMOD","**":"IPOW","|":"IBIT_OR","&":"IBIT_AND","^":"IBIT_XOR","<<":"ILSHIFT",">>":"IRSHIFT","@":"IMATMUL"}.get(operator)
            if not opcode: self.unsupported(node)
            if target.kind=="name":
                name=self.mangle(target.value); self.emit("LOAD",name); self.expression(value); self.emit(opcode)
                self.emit("STORE_GLOBAL" if name in self.global_names else "STORE_NONLOCAL" if name in self.nonlocal_names else "STORE",name)
            elif target.kind=="attribute":
                attribute=self.mangle(target.value); self.expression(target.children[0]); self.emit("DUP"); self.emit("GET_ATTR",attribute)
                self.expression(value); self.emit(opcode); self.emit("SET_ATTR",attribute)
            elif target.kind=="subscript":
                self.expression(target.children[0]); self.emit("DUP"); self.expression(target.children[1]); self.emit("DUP2")
                self.emit("GET_ITEM"); self.expression(value); self.emit(opcode); self.emit("SET_ITEM")
            else: self.unsupported(target)
        elif node.kind == "if":
            self.expression(node.children[0]); false = self.emit("JUMP_FALSE", -1)
            for item in node.children[1].children: self.statement(item)
            end = self.emit("JUMP", -1); self.patch(false, len(self.code.instructions))
            for item in node.children[2].children: self.statement(item)
            self.patch(end, len(self.code.instructions))
        elif node.kind == "while":
            start = len(self.code.instructions); self.expression(node.children[0])
            end = self.emit("JUMP_FALSE", -1)
            breaks: list[int]=[]; self.loops.append((start,breaks,False))
            for item in node.children[1].children: self.statement(item)
            self.loops.pop()
            self.emit("JUMP", start); self.patch(end, len(self.code.instructions))
            for item in node.children[2].children: self.statement(item)
            for jump in breaks:
                if isinstance(jump,int): self.patch(jump,len(self.code.instructions))
                else: jump["break_target"]=len(self.code.instructions)
        elif node.kind == "for":
            self.expression(node.children[0]); self.emit("ITER"); start = len(self.code.instructions)
            end = self.emit("FOR_ITER", -1); self.store_target(node.value)
            breaks=[]; self.loops.append((start,breaks,True))
            for item in node.children[1].children: self.statement(item)
            self.loops.pop()
            self.emit("JUMP", start); self.patch(end, len(self.code.instructions))
            for item in node.children[2].children: self.statement(item)
            for jump in breaks:
                if isinstance(jump,int): self.patch(jump,len(self.code.instructions))
                else: jump["break_target"]=len(self.code.instructions)
        elif node.kind == "def":
            name, params, defaults, vararg, kwarg, kwonly, is_async, posonly, *extra = node.value
            annotations=extra[0] if extra else {}; type_parameters=extra[1] if len(extra)>1 else []
            all_parameters=[*params,*kwonly,*([vararg] if vararg else []),*([kwarg] if kwarg else [])]
            child_compiler=Compiler(name,all_parameters,evaluate_annotations=False,private_class=self.private_class)
            child = child_compiler.compile_body(node.children)
            for parameter in [*params,*kwonly]:
                if parameter in defaults: self.expression(defaults[parameter])
            type_parameter_names=[item[1] if isinstance(item,(list,tuple)) else item["name"] for item in type_parameters]
            for type_index,item in enumerate(type_parameters):
                payload=self.type_parameter_payload(item); payload.update({"group_names":type_parameter_names,"group_index":type_index}); type_name=payload["name"]
                self.emit("SAVE_NAME",type_name)
                self.emit("MAKE_TYPE_PARAMETER",payload); self.emit("DUP"); self.emit("STORE",type_name)
            annotation_names=list(annotations)
            declared_globals,declared_nonlocals=_scope_declarations(node.children)
            mangled_globals={self.mangle(item) for item in declared_globals}; mangled_nonlocals={self.mangle(item) for item in declared_nonlocals}
            local_names=sorted({self.mangle(item) for item in (_scope_bindings(node.children)|set(all_parameters))}-mangled_globals-mangled_nonlocals)
            mangled_params=[self.mangle(item) for item in params]; mangled_kwonly=[self.mangle(item) for item in kwonly]
            mangled_vararg=self.mangle(vararg) if vararg else None; mangled_kwarg=self.mangle(kwarg) if kwarg else None
            self.emit("MAKE_FUNCTION", {"code":child.to_dict(),"defaults":[self.mangle(p) for p in [*params,*kwonly] if p in defaults],
                      "name":name,"doc":self.docstring(node.children),
                      "annotations":[],"annotation_codes":{self.mangle(annotation_name) if annotation_name!="return" else annotation_name:self.expression_code(self.annotation_node(annotations[annotation_name]),f"annotation-{annotation_name}").to_dict() for annotation_name in annotation_names},"annotation_strings":{self.mangle(annotation_name) if annotation_name!="return" else annotation_name:self.annotation_text(annotations[annotation_name]) for annotation_name in annotation_names},
                      "type_params":type_parameter_names,
                      "local_names":local_names,
                      "free_names":sorted(mangled_nonlocals),
                      "signature":{"positional":mangled_params,"positional_only":[self.mangle(item) for item in posonly],"keyword_only":mangled_kwonly,"vararg":mangled_vararg,"kwarg":mangled_kwarg},
                      "generator":self.has_yield(node.children),"async":is_async})
            if not self.defer_definition_store: self.store_name(name)
            for item in reversed(type_parameters): self.emit("RESTORE_NAME",item[1] if isinstance(item,(list,tuple)) else item["name"])
        elif node.kind == "class":
            if len(node.value)==2: name,bases=node.value; type_parameters=[]
            elif len(node.value)==3: name,bases,type_parameters=node.value; keywords=[]
            elif len(node.value)==4: name,bases,type_parameters,keywords=node.value; arguments=[]
            else: name,bases,type_parameters,keywords,arguments=node.value
            type_parameter_names=[item[1] if isinstance(item,(list,tuple)) else item["name"] for item in type_parameters]
            for type_index,item in enumerate(type_parameters):
                payload=self.type_parameter_payload(item); payload.update({"group_names":type_parameter_names,"group_index":type_index}); type_name=payload["name"]
                self.emit("SAVE_NAME",type_name)
                self.emit("MAKE_TYPE_PARAMETER",payload); self.emit("DUP"); self.emit("STORE",type_name)
            if arguments:
                self.emit("CLASS_BEGIN")
                for kind,key,value in arguments:
                    self.expression(value); self.emit("CLASS_ARG",[kind,key])
            else:
                for base in bases: self.expression(base.children[0] if base.kind=="starred" else base)
                for _,value in keywords: self.expression(value)
            child_compiler=Compiler(name,[],private_class=name); child=child_compiler.compile_body(node.children)
            declared_globals,declared_nonlocals=_scope_declarations(node.children)
            class_local_names=sorted({child_compiler.mangle(item) for item in _scope_bindings(node.children)}-{child_compiler.mangle(item) for item in declared_globals}-{child_compiler.mangle(item) for item in declared_nonlocals})
            self.emit("MAKE_CLASS",{"code":child.to_dict(),"name":name,"doc":self.docstring(node.children),"firstlineno":self.definition_firstlineno if self.definition_firstlineno is not None else node.line,"bases":len(bases),"base_starred":[base.kind=="starred" for base in bases],"keywords":[item[0] for item in keywords],"class_arguments":[[kind,key] for kind,key,_ in arguments] if arguments else None,"incremental_arguments":bool(arguments),"type_params":type_parameter_names,"local_names":class_local_names,"free_names":sorted(declared_nonlocals),"static_attributes":self.static_attributes(node.children)})
            if not self.defer_definition_store: self.store_name(name)
            for item in reversed(type_parameters): self.emit("RESTORE_NAME",item[1] if isinstance(item,(list,tuple)) else item["name"])
        elif node.kind == "decorated":
            decorators=node.children[:-1]; target=node.children[-1]
            for decorator in decorators: self.expression(decorator)
            previous=self.defer_definition_store; previous_line=self.definition_firstlineno
            self.defer_definition_store=True; self.definition_firstlineno=node.line
            try: self.statement(target)
            finally: self.defer_definition_store=previous; self.definition_firstlineno=previous_line
            name=target.value[0]
            for _ in reversed(decorators): self.emit("CALL",1)
            self.store_name(name)
        elif node.kind == "return":
            self.expression(node.children[0]); self.emit("SIGNAL_RETURN" if self.signal_returns else "RETURN")
        elif node.kind == "raise":
            self.expression(node.children[0])
            if len(node.children)>1: self.expression(node.children[1]); self.emit("RAISE_FROM")
            else: self.emit("RAISE")
        elif node.kind == "reraise": self.emit("RERAISE")
        elif node.kind in ("yield","yield_from"):
            self.expression(node.children[0]); self.emit("YIELD_FROM" if node.kind=="yield_from" else "YIELD"); self.emit("POP")
        elif node.kind == "try":
            body,handlers,otherwise,final=node.children
            payload={
                "body": self.scope_child(f"{self.code.name}:try",True).compile_body(body.children).to_dict(),
                "handlers": [
                    {"type":self.expression_code(handler.value[0],"except-type").to_dict() if handler.value[0] else None,"alias":handler.value[1],"alias_scope":self.name_scope(handler.value[1]) if handler.value[1] else "local","star":handler.value[2] if len(handler.value)>2 else False,
                     "code":self.scope_child(f"{self.code.name}:except",True).compile_body(handler.children).to_dict()}
                    for handler in handlers.children
                ],
                "else": self.scope_child(f"{self.code.name}:else",True).compile_body(otherwise.children).to_dict() if otherwise.children else None,
                "finally": self.scope_child(f"{self.code.name}:finally",True).compile_body(final.children).to_dict() if final.children else None,
                "break_target":None,"continue_target":self.loops[-1][0] if self.loops else None,
            }
            self.emit("TRY",payload)
            if self.loops: self.loops[-1][1].append(payload)
        elif node.kind == "with":
            managers,body=node.children
            payload={"managers":[{"alias":self.target_spec(item.children[1]) if len(item.children)>1 else None,"code":self.expression_code(item.children[0],"with-manager").to_dict()} for item in managers.children],
                     "body":self.scope_child(f"{self.code.name}:with",True).compile_body(body.children).to_dict(),
                     "break_target":None,"continue_target":self.loops[-1][0] if self.loops else None}
            self.emit("WITH",payload)
            if self.loops: self.loops[-1][1].append(payload)
        elif node.kind == "async_for":
            payload={"target":self.target_spec(node.value),"iter":self.expression_code(node.children[0],"async-iter").to_dict(),
                     "body":self.scope_child(f"{self.code.name}:async-for",True).compile_body(node.children[1].children).to_dict(),
                     "else":self.scope_child(f"{self.code.name}:async-for-else",True).compile_body(node.children[2].children).to_dict() if len(node.children)>2 and node.children[2].children else None}
            self.emit("ASYNC_FOR",payload)
        elif node.kind == "async_with":
            managers,body=node.children
            payload={"managers":[{"alias":self.target_spec(item.children[1]) if len(item.children)>1 else None,"code":self.expression_code(item.children[0],"async-manager").to_dict()} for item in managers.children],
                     "body":self.scope_child(f"{self.code.name}:async-with",True).compile_body(body.children).to_dict(),
                     "break_target":None,"continue_target":self.loops[-1][0] if self.loops else None}
            self.emit("ASYNC_WITH",payload)
            if self.loops: self.loops[-1][1].append(payload)
        elif node.kind == "match":
            temp=f"$매치{self.temp_counter}"; self.temp_counter+=1
            self.expression(node.children[0]); self.emit("STORE",temp); end_jumps=[]
            for case in node.children[1:-1]:
                if case.value is None and self.irrefutable_pattern(case.children[0]): raise CompileError(f"모든 값을 잡는 케이스는 마지막이어야 합니다 (줄 {case.line})")
            for case in node.children[1:]:
                pattern=case.children[0]; self.validate_pattern(pattern); failure=None
                self.emit("LOAD",temp); self.emit("MATCH_PATTERN",self.pattern_spec(pattern)); failure=self.emit("JUMP_FALSE",-1)
                if case.value is not None:
                    self.expression(case.value); guard_failure=self.emit("JUMP_FALSE",-1)
                else: guard_failure=None
                for item in case.children[1].children: self.statement(item)
                end_jumps.append(self.emit("JUMP",-1)); next_case=len(self.code.instructions)
                if failure is not None: self.patch(failure,next_case)
                if guard_failure is not None: self.patch(guard_failure,next_case)
            end=len(self.code.instructions)
            for jump in end_jumps: self.patch(jump,end)
            self.emit("DELETE",temp)
        elif node.kind == "pass":
            self.emit("NOP")
        elif node.kind == "break":
            if not self.loops:
                if self.signal_returns: self.emit("SIGNAL_BREAK"); return
                raise CompileError(f"루프 밖의 브레이크 (줄 {node.line})")
            if self.loops[-1][2]: self.emit("POP")
            self.loops[-1][1].append(self.emit("JUMP",-1))
        elif node.kind == "continue":
            if not self.loops:
                if self.signal_returns: self.emit("SIGNAL_CONTINUE"); return
                raise CompileError(f"루프 밖의 컨티뉴 (줄 {node.line})")
            self.emit("JUMP",self.loops[-1][0])
        else: self.unsupported(node)

    def store_target(self,target:Node):
        if target.kind=="name":
            name=self.mangle(target.value); self.emit("STORE_GLOBAL" if name in self.global_names else "STORE_NONLOCAL" if name in self.nonlocal_names else "STORE",name)
        elif target.kind in ("tuple","list"):
            stars=[index for index,item in enumerate(target.children) if item.kind=="starred"]
            if len(stars)>1: raise CompileError(f"구조 분해 별표 대상은 하나만 허용됩니다 (줄 {target.line})")
            if stars:
                before=stars[0]; after=len(target.children)-before-1
                self.emit("UNPACK_EX",(before<<16)|after)
            else: self.emit("UNPACK",len(target.children))
            for item in target.children: self.store_target(item.children[0] if item.kind=="starred" else item)
        elif target.kind=="attribute":
            temp=f"$대입{self.temp_counter}"; self.temp_counter+=1
            self.emit("STORE",temp); self.expression(target.children[0]); self.emit("LOAD",temp); self.emit("SET_ATTR",self.mangle(target.value)); self.emit("DELETE",temp)
        elif target.kind=="subscript":
            temp=f"$대입{self.temp_counter}"; self.temp_counter+=1
            self.emit("STORE",temp); self.expression(target.children[0]); self.expression(target.children[1]); self.emit("LOAD",temp); self.emit("SET_ITEM"); self.emit("DELETE",temp)
        else: self.unsupported(target)

    def expression(self, node: Node) -> None:
        self.current_line=node.line
        if node.kind == "constant": self.emit("CONST", self.constant(node.value))
        elif node.kind == "name": self.emit("LOAD", self.mangle(node.value))
        elif node.kind == "binary":
            if node.value in ("and","or"):
                self.expression(node.children[0])
                jump=self.emit("JUMP_IF_FALSE_OR_POP" if node.value=="and" else "JUMP_IF_TRUE_OR_POP",-1)
                self.expression(node.children[1]); self.patch(jump,len(self.code.instructions)); return
            self.expression(node.children[0]); self.expression(node.children[1])
            ops = {"+":"ADD","-":"SUB","*":"MUL","/":"DIV","//":"FLOORDIV","%":"MOD","**":"POW",
                   "==":"EQ","!=":"NE","<":"LT","<=":"LE",">":"GT",">=":"GE","in":"IN","is":"IS","not in":"NOT_IN","is not":"IS_NOT"}
            ops.update({"|":"BIT_OR","^":"BIT_XOR","&":"BIT_AND","<<":"LSHIFT",">>":"RSHIFT","@":"MATMUL"})
            op=ops.get(node.value); self.emit(op) if op else self.unsupported(node)
        elif node.kind == "compare_chain":
            self.emit("CHAIN_COMPARE",{"operators":node.value,"operands":[self.expression_code(item,"compare-operand").to_dict() for item in node.children]})
        elif node.kind == "unary":
            self.expression(node.children[0]); op={"-":"NEG","+":"POS","not":"NOT","~":"INVERT"}.get(node.value)
            self.emit(op) if op else self.unsupported(node)
        elif node.kind == "call":
            if node.children[0].kind=="name" and node.children[0].value=="super" and len(node.children)==1:
                self.emit("SUPER",self.code.parameters[0] if self.code.parameters else ""); return
            self.expression(node.children[0])
            descriptors=node.value or [["positional",None] for _ in node.children[1:]]
            if any(item[0] in ("star","kwstar") for item in descriptors):
                self.emit("CALL_BEGIN")
                for argument,descriptor in zip(node.children[1:],descriptors):
                    self.expression(argument); self.emit("CALL_ARG",descriptor)
                self.emit("CALL_READY")
            else:
                for argument in node.children[1:]: self.expression(argument)
                if all(item[0]=="positional" for item in descriptors): self.emit("CALL",len(descriptors))
                else: self.emit("CALL_EX",descriptors)
        elif node.kind == "list":
            if any(item.kind=="starred" for item in node.children):
                self.emit("COLLECTION_BEGIN","list")
                for item in node.children:
                    self.expression(item.children[0] if item.kind=="starred" else item); self.emit("COLLECTION_ADD","star" if item.kind=="starred" else "item")
                self.emit("COLLECTION_READY")
            else:
                for item in node.children: self.expression(item)
                self.emit("BUILD_LIST", len(node.children))
        elif node.kind == "tuple":
            if any(item.kind=="starred" for item in node.children):
                self.emit("COLLECTION_BEGIN","tuple")
                for item in node.children:
                    self.expression(item.children[0] if item.kind=="starred" else item); self.emit("COLLECTION_ADD","star" if item.kind=="starred" else "item")
                self.emit("COLLECTION_READY")
            else:
                for item in node.children: self.expression(item)
                self.emit("BUILD_TUPLE",len(node.children))
        elif node.kind == "set":
            self.emit("COLLECTION_BEGIN","set")
            for item in node.children:
                self.expression(item.children[0] if item.kind=="starred" else item); self.emit("COLLECTION_ADD","star" if item.kind=="starred" else "item")
            self.emit("COLLECTION_READY")
        elif node.kind == "dict":
            self.emit("COLLECTION_BEGIN","dict")
            for pair in node.children:
                if pair.kind=="dict_unpack": self.expression(pair.children[0]); self.emit("COLLECTION_ADD","unpack")
                else: self.expression(pair.children[0]); self.expression(pair.children[1]); self.emit("COLLECTION_ADD","pair")
            self.emit("COLLECTION_READY")
        elif node.kind == "subscript":
            self.expression(node.children[0]); self.expression(node.children[1]); self.emit("GET_ITEM")
        elif node.kind == "slice":
            for item in node.children: self.expression(item)
            self.emit("BUILD_SLICE")
        elif node.kind == "attribute":
            self.expression(node.children[0]); self.emit("GET_ATTR", self.mangle(node.value))
        elif node.kind == "format":
            self.expression(node.children[0])
            if len(node.children)>1: self.expression(node.children[1])
            self.emit("FORMAT_VALUE",{"conversion":node.value,"has_spec":len(node.children)>1})
        elif node.kind == "fstring":
            for item in node.children: self.expression(item)
            self.emit("BUILD_STRING",len(node.children))
        elif node.kind == "interpolation":
            self.expression(node.children[0]); self.emit("CONST",self.constant(node.value["expression"])); self.emit("CONST",self.constant(node.value["conversion"]))
            if len(node.children)>1: self.expression(node.children[1])
            else: self.emit("CONST",self.constant(""))
            self.emit("MAKE_INTERPOLATION")
        elif node.kind == "template":
            for item in node.children: self.expression(item)
            self.emit("BUILD_TEMPLATE",len(node.children))
        elif node.kind in ("listcomp","setcomp","dictcomp","generatorexpr"):
            element=node.children[0]
            payload={"kind":node.kind,"clauses":[
                {"target":self.target_spec(clause.value[0] if isinstance(clause.value,tuple) else clause.value),"async":clause.value[1] if isinstance(clause.value,tuple) else False,"iter":self.expression_code(clause.children[0],"comp-iter").to_dict(),
                 "filters":[self.expression_code(item,"comp-filter").to_dict() for item in clause.children[1:]]}
                for clause in node.children[1:]]}
            payload["async"]=any(clause["async"] for clause in payload["clauses"]) or self.has_await(node.children)
            payload["bindings"]=sorted(set().union(*(self.named_expression_targets(item) for item in node.children)))
            if node.kind=="dictcomp":
                payload["key"]=self.expression_code(element.children[0],"comp-key").to_dict()
                payload["value"]=self.expression_code(element.children[1],"comp-value").to_dict()
            else: payload["element"]=self.expression_code(element,"comp-element").to_dict()
            self.emit("COMPREHENSION",payload)
        elif node.kind=="lambda":
            signature=node.value if isinstance(node.value,dict) else {"params":node.value,"posonly":[],"kwonly":[],"defaults":{},"vararg":None,"kwarg":None}
            all_parameters=[*signature["params"],*signature["kwonly"],*([signature["vararg"]] if signature["vararg"] else []),*([signature["kwarg"]] if signature["kwarg"] else [])]
            child=Compiler("<lambda>",all_parameters,evaluate_annotations=False,private_class=self.private_class)
            child.expression(node.children[0]); child.emit("RETURN")
            default_names=[name for name in [*signature["params"],*signature["kwonly"]] if name in signature["defaults"]]
            for name in default_names: self.expression(signature["defaults"][name])
            self.emit("MAKE_FUNCTION",{"code":child.code.to_dict(),"defaults":[self.mangle(item) for item in default_names],
                      "name":"<lambda>","doc":None,
                      "annotations":[],
                      "local_names":sorted(self.mangle(item) for item in (set(all_parameters)|self.named_expression_targets(node.children[0]))),
                      "free_names":[],
                      "type_params":[],
                      "signature":{"positional":[self.mangle(item) for item in signature["params"]],"positional_only":[self.mangle(item) for item in signature["posonly"]],"keyword_only":[self.mangle(item) for item in signature["kwonly"]],"vararg":self.mangle(signature["vararg"]) if signature["vararg"] else None,"kwarg":self.mangle(signature["kwarg"]) if signature["kwarg"] else None},"generator":self.has_yield(node.children),"async":False})
        elif node.kind=="await":
            self.expression(node.children[0]); self.emit("AWAIT")
        elif node.kind in ("yield_expr","yield_from_expr"):
            self.expression(node.children[0]); self.emit("YIELD_FROM" if node.kind=="yield_from_expr" else "YIELD")
        elif node.kind=="namedexpr":
            self.expression(node.children[0]); self.emit("DUP"); self.store_name(node.value)
        elif node.kind=="conditional":
            self.expression(node.children[0]); false=self.emit("JUMP_FALSE",-1)
            self.expression(node.children[1]); end=self.emit("JUMP",-1); self.patch(false,len(self.code.instructions))
            self.expression(node.children[2]); self.patch(end,len(self.code.instructions))
        else: self.unsupported(node)

    def unsupported(self, node) -> None:
        raise CompileError(f"아직 지원하지 않는 구문: {node.kind} (줄 {node.line})")

def compile_hir(source: str, filename: str = "<하이썬>", *, optimize: bool = True) -> HIRCode:
    try:
        tree = parse(source,filename)
    except SyntaxError as exc:
        if exc.filename is None: exc.filename=filename
        raise
    _validate_declarations(tree.children)
    _validate_future_imports(tree.children)
    _validate_context(tree.children)
    hir = Compiler(filename).compile_body(tree.children)
    return optimize_hir(hir) if optimize else hir

def _lower(hir: HIRCode) -> CodeObject:
    instructions: list[list] = []
    for instruction in hir.instructions:
        lowered = list(instruction)
        if lowered[0] in ("MAKE_FUNCTION","MAKE_CLASS"):
            nested = lowered[1]["code"]
            result=_lower(HIRCode.from_dict(nested)).to_dict()
            lowered[1]["code"]=result
        elif lowered[0]=="TRY":
            payload=lowered[1]
            for key in ("body","else","finally"):
                nested=payload.get(key)
                if nested: payload[key]=_lower(HIRCode.from_dict(nested)).to_dict()
            for handler in payload["handlers"]:
                nested=handler["code"]
                handler["code"]=_lower(HIRCode.from_dict(nested)).to_dict()
        elif lowered[0]=="COMPREHENSION":
            payload=lowered[1]
            for key in ("element","key","value"):
                nested=payload.get(key)
                if nested: payload[key]=_lower(HIRCode.from_dict(nested)).to_dict()
            for clause in payload["clauses"]:
                nested=clause["iter"]
                clause["iter"]=_lower(HIRCode.from_dict(nested)).to_dict()
                clause["filters"]=[_lower(HIRCode.from_dict(n)).to_dict() for n in clause["filters"]]
        elif lowered[0]=="WITH":
            payload=lowered[1]; nested=payload["body"]
            payload["body"]=_lower(HIRCode.from_dict(nested)).to_dict()
            for manager in payload["managers"]:
                nested=manager["code"]
                manager["code"]=_lower(HIRCode.from_dict(nested)).to_dict()
        elif lowered[0] in ("ASYNC_FOR","ASYNC_WITH"):
            payload=lowered[1]
            for key in ("iter","body","else"):
                nested=payload.get(key)
                if nested: payload[key]=_lower(HIRCode.from_dict(nested)).to_dict()
            for manager in payload.get("managers",[]):
                nested=manager["code"]; manager["code"]=_lower(HIRCode.from_dict(nested)).to_dict()
        elif lowered[0]=="ANNOTATE_LAZY":
            nested=lowered[1]["code"]; lowered[1]["code"]=_lower(HIRCode.from_dict(nested)).to_dict()
        instructions.append(lowered)
    return CodeObject(hir.name, hir.parameters, hir.constants, instructions,list(hir.lines))

def compile_source(source: str, filename: str = "<하이썬>", *, optimize: bool = True) -> CodeObject:
    return _lower(compile_hir(source, filename, optimize=optimize))
