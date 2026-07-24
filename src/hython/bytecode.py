"""HBC container and instruction model; unrelated to CPython bytecode."""
from __future__ import annotations
import hashlib
import json
import struct
import zlib
import base64
from dataclasses import asdict, dataclass, field
from pathlib import Path

MAGIC = b"HYBC"
VERSION = 6
MAX_COMPRESSED_SIZE = 64 * 1024 * 1024
MAX_INSTRUCTIONS = 1_000_000
_NO_ARG = {"RETURN","POP","NOP","ITER","SET_ITEM","GET_ITEM","FORMAT","NEG","POS","NOT","IMPORT_STAR",
           "ADD","SUB","MUL","DIV","FLOORDIV","MOD","POW","BIT_OR","BIT_XOR","BIT_AND","LSHIFT","RSHIFT","MATMUL","IADD","ISUB","IMUL","IDIV","IFLOORDIV","IMOD","IPOW","IBIT_OR","IBIT_XOR","IBIT_AND","ILSHIFT","IRSHIFT","IMATMUL","EQ","NE","LT","LE","GT","GE","IN","IS","NOT_IN","IS_NOT","BOOL_AND","BOOL_OR","INVERT","RAISE","RAISE_FROM","RERAISE","DELETE_ITEM","ASSERT","DUP","DUP2","BUILD_SLICE","YIELD","YIELD_FROM","AWAIT","SIGNAL_RETURN","SIGNAL_BREAK","SIGNAL_CONTINUE","MAKE_INTERPOLATION","CALL_BEGIN","CALL_READY","CLASS_BEGIN","COLLECTION_READY"}
_NAME_ARG = {"LOAD","STORE","STORE_GLOBAL","STORE_NONLOCAL","DELETE","DELETE_GLOBAL","DELETE_NONLOCAL","GET_ATTR","SET_ATTR","DELETE_ATTR","IMPORT","ANNOTATE","SUPER","SAVE_NAME","RESTORE_NAME"}
_INT_ARG = {"CALL","UNPACK","UNPACK_EX","BUILD_LIST","BUILD_TUPLE","BUILD_SET","BUILD_DICT","BUILD_STRING","BUILD_TEMPLATE"}

@dataclass
class CodeObject:
    name: str
    parameters: list[str]
    constants: list[object]
    instructions: list[list]
    lines: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name":self.name,"parameters":self.parameters,"constants":[_encode_constant(value) for value in self.constants],"instructions":self.instructions,"lines":self.lines}

    @classmethod
    def from_dict(cls, value: dict) -> "CodeObject":
        return cls(value["name"], value["parameters"], [_decode_constant(item) for item in value["constants"]], value["instructions"],value.get("lines",[]))

def _encode_constant(value):
    if value is Ellipsis: return {"$hython_constant":"ellipsis"}
    if isinstance(value,bytes): return {"$hython_constant":"bytes","data":base64.b64encode(value).decode("ascii")}
    if isinstance(value,complex): return {"$hython_constant":"complex","real":value.real,"imag":value.imag}
    if isinstance(value,tuple): return {"$hython_constant":"tuple","items":[_encode_constant(item) for item in value]}
    return value

def _decode_constant(value):
    if not isinstance(value,dict) or "$hython_constant" not in value: return value
    kind=value["$hython_constant"]
    if kind=="ellipsis": return Ellipsis
    if kind=="bytes": return base64.b64decode(value["data"],validate=True)
    if kind=="complex": return complex(value["real"],value["imag"])
    if kind=="tuple": return tuple(_decode_constant(item) for item in value["items"])
    raise ValueError("알 수 없는 HBC 상수 형식")

class BytecodeError(ValueError):
    pass

def dumps(code: CodeObject) -> bytes:
    raw = json.dumps(code.to_dict(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = zlib.compress(raw, level=9)
    digest = hashlib.sha256(payload).digest()
    return MAGIC + bytes([VERSION]) + struct.pack(">I", len(payload)) + digest + payload

def loads(data: bytes) -> CodeObject:
    if len(data) < 41 or data[:4] != MAGIC:
        raise BytecodeError("하이썬 HBC 파일이 아닙니다.")
    if data[4] != VERSION:
        raise BytecodeError(f"지원하지 않는 HBC 버전: {data[4]}")
    size = struct.unpack(">I", data[5:9])[0]
    if size > MAX_COMPRESSED_SIZE:
        raise BytecodeError("HBC 파일이 허용 크기를 초과합니다.")
    digest, payload = data[9:41], data[41:]
    if size != len(payload) or hashlib.sha256(payload).digest() != digest:
        raise BytecodeError("HBC 크기 또는 SHA-256 무결성 검사가 실패했습니다.")
    try:
        decompressor=zlib.decompressobj()
        raw=decompressor.decompress(payload,MAX_COMPRESSED_SIZE+1)
        if len(raw)>MAX_COMPRESSED_SIZE or decompressor.unconsumed_tail:
            raise BytecodeError("HBC 압축 해제 크기가 제한을 초과합니다.")
        value = json.loads(raw.decode("utf-8"))
        code=CodeObject.from_dict(value)
        verify(code)
        return code
    except BytecodeError:
        raise
    except (ValueError, KeyError, TypeError, zlib.error) as exc:
        raise BytecodeError("손상된 HBC 내용입니다.") from exc

def write(path: Path, code: CodeObject) -> None:
    path.write_bytes(dumps(code))

def read(path: Path) -> CodeObject:
    return loads(path.read_bytes())

def _verify_target(spec) -> None:
    if isinstance(spec,str): return
    if not isinstance(spec,dict): raise TypeError
    kind=spec.get("kind")
    if kind=="name":
        if not isinstance(spec.get("name"),str) or spec.get("scope","local") not in ("local","global","nonlocal"): raise TypeError
    elif kind=="starred": _verify_target(spec["target"])
    elif kind=="sequence":
        if not isinstance(spec.get("items"),list): raise TypeError
        for item in spec["items"]: _verify_target(item)
    elif kind=="attribute":
        if not isinstance(spec.get("name"),str): raise TypeError
        verify(CodeObject.from_dict(spec["object"]))
    elif kind=="subscript":
        verify(CodeObject.from_dict(spec["object"])); verify(CodeObject.from_dict(spec["index"]))
    else: raise TypeError

def _verify_pattern(spec) -> None:
    if not isinstance(spec,dict): raise TypeError
    kind=spec.get("kind"); scopes=("local","global","nonlocal")
    if kind in ("wildcard","literal","singleton"): return
    if kind in ("capture","star"):
        if not isinstance(spec.get("name"),str) or spec.get("scope","local") not in scopes: raise TypeError
        return
    if kind=="value":
        if not isinstance(spec.get("path"),str): raise TypeError
        return
    if kind=="or" or kind=="sequence":
        key="items"
        if not isinstance(spec.get(key),list): raise TypeError
        for item in spec[key]: _verify_pattern(item)
        return
    if kind=="as":
        if not isinstance(spec.get("name"),str) or spec.get("scope","local") not in scopes: raise TypeError
        _verify_pattern(spec["pattern"]); return
    if kind=="mapping":
        if spec.get("rest") is not None and not isinstance(spec["rest"],str): raise TypeError
        if spec.get("rest_scope","local") not in scopes or not isinstance(spec.get("pairs"),list): raise TypeError
        for pair in spec["pairs"]:
            key=pair["key"]
            if not isinstance(key,dict) or key.get("kind") not in ("literal","value"): raise TypeError
            if key["kind"]=="value" and not isinstance(key.get("path"),str): raise TypeError
            _verify_pattern(pair["pattern"])
        return
    if kind=="class":
        if not isinstance(spec.get("name"),str) or not isinstance(spec.get("positional"),list) or not isinstance(spec.get("keywords"),list): raise TypeError
        for item in spec["positional"]: _verify_pattern(item)
        for item in spec["keywords"]:
            if not isinstance(item.get("name"),str): raise TypeError
            _verify_pattern(item["pattern"])
        return
    raise TypeError

def verify(code: CodeObject) -> None:
    """Reject malformed programs before the VM executes any instruction."""
    if not isinstance(code.name,str) or not isinstance(code.parameters,list) or not all(isinstance(x,str) for x in code.parameters):
        raise BytecodeError("잘못된 HBC 코드 객체입니다.")
    if len(code.instructions)>MAX_INSTRUCTIONS: raise BytecodeError("HBC 명령어 제한을 초과합니다.")
    if code.lines and (len(code.lines)!=len(code.instructions) or not all(isinstance(line,int) and line>=0 for line in code.lines)):
        raise BytecodeError("HBC 소스 위치 테이블 오류")
    count=len(code.instructions)
    for index, ins in enumerate(code.instructions):
        if not isinstance(ins,list) or not ins or not isinstance(ins[0],str):
            raise BytecodeError(f"잘못된 명령어: {index}")
        op=ins[0]; args=ins[1:]
        if op in _NO_ARG:
            if args: raise BytecodeError(f"{op} 명령어 인자 오류")
        elif op in _NAME_ARG:
            if len(args)!=1 or not isinstance(args[0],str): raise BytecodeError(f"{op} 이름 인자 오류")
        elif op in _INT_ARG:
            if len(args)!=1 or not isinstance(args[0],int) or args[0]<0: raise BytecodeError(f"{op} 정수 인자 오류")
        elif op=="CONST":
            if len(args)!=1 or not isinstance(args[0],int) or not 0<=args[0]<len(code.constants): raise BytecodeError("CONST 인덱스 오류")
        elif op in ("JUMP","JUMP_FALSE","FOR_ITER","JUMP_IF_FALSE_OR_POP","JUMP_IF_TRUE_OR_POP"):
            if len(args)!=1 or not isinstance(args[0],int) or not 0<=args[0]<=count: raise BytecodeError(f"{op} 점프 범위 오류")
        elif op=="MAKE_FUNCTION":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("함수 코드 객체 오류")
            try:
                if not isinstance(args[0]["defaults"],list) or not all(isinstance(x,str) for x in args[0]["defaults"]): raise TypeError
                if not isinstance(args[0].get("annotations",[]),list) or not all(isinstance(x,str) for x in args[0].get("annotations",[])): raise TypeError
                if not isinstance(args[0].get("annotation_codes",{}),dict) or not all(isinstance(name,str) and isinstance(code,dict) for name,code in args[0].get("annotation_codes",{}).items()): raise TypeError
                if not isinstance(args[0].get("annotation_strings",{}),dict) or not all(isinstance(name,str) and isinstance(text,str) for name,text in args[0].get("annotation_strings",{}).items()): raise TypeError
                for annotation_code in args[0].get("annotation_codes",{}).values(): verify(CodeObject.from_dict(annotation_code))
                if not isinstance(args[0].get("type_params",[]),list) or not all(isinstance(x,str) for x in args[0].get("type_params",[])): raise TypeError
                if not isinstance(args[0].get("local_names",[]),list) or not all(isinstance(x,str) for x in args[0].get("local_names",[])): raise TypeError
                if not isinstance(args[0].get("free_names",[]),list) or not all(isinstance(x,str) for x in args[0].get("free_names",[])): raise TypeError
                signature=args[0]["signature"]
                if not isinstance(args[0]["generator"],bool): raise TypeError
                if not isinstance(args[0]["async"],bool): raise TypeError
                if not isinstance(signature["positional"],list) or not isinstance(signature["keyword_only"],list): raise TypeError
                if not isinstance(signature["positional_only"],list): raise TypeError
                if not all(isinstance(x,str) for x in signature["positional"]+signature["positional_only"]+signature["keyword_only"]): raise TypeError
                if signature["vararg"] is not None and not isinstance(signature["vararg"],str): raise TypeError
                if signature["kwarg"] is not None and not isinstance(signature["kwarg"],str): raise TypeError
                verify(CodeObject.from_dict(args[0]["code"]))
            except (KeyError,TypeError) as exc: raise BytecodeError("함수 코드 객체 오류") from exc
        elif op=="IMPORT_FROM":
            if len(args)!=1 or not isinstance(args[0],dict) or not isinstance(args[0].get("module"),str) or not isinstance(args[0].get("name"),str):
                raise BytecodeError("IMPORT_FROM 인자 오류")
        elif op=="ANNOTATE_LAZY":
            if len(args)!=1 or not isinstance(args[0],dict) or not isinstance(args[0].get("name"),str) or not isinstance(args[0].get("text",""),str) or not isinstance(args[0].get("code"),dict): raise BytecodeError("ANNOTATE_LAZY 인자 오류")
            verify(CodeObject.from_dict(args[0]["code"]))
        elif op=="MAKE_CLASS":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("중첩 코드 객체 오류")
            try:
                if not isinstance(args[0]["bases"],int) or args[0]["bases"]<0: raise TypeError
                if not isinstance(args[0].get("incremental_arguments",False),bool): raise TypeError
                if not isinstance(args[0].get("base_starred",[False]*args[0]["bases"]),list) or len(args[0].get("base_starred",[False]*args[0]["bases"]))!=args[0]["bases"] or not all(isinstance(x,bool) for x in args[0].get("base_starred",[False]*args[0]["bases"])): raise TypeError
                if not isinstance(args[0].get("keywords",[]),list) or not all(x is None or isinstance(x,str) for x in args[0].get("keywords",[])): raise TypeError
                if not isinstance(args[0].get("type_params",[]),list) or not all(isinstance(x,str) for x in args[0].get("type_params",[])): raise TypeError
                if not isinstance(args[0].get("local_names",[]),list) or not all(isinstance(x,str) for x in args[0].get("local_names",[])): raise TypeError
                verify(CodeObject.from_dict(args[0]["code"]))
            except (KeyError,TypeError) as exc: raise BytecodeError("중첩 코드 객체 오류") from exc
        elif op in ("CALL_EX","CALL_ARG","CLASS_ARG"):
            if len(args)!=1 or not isinstance(args[0],list): raise BytecodeError("CALL_EX 인자 오류")
            descriptors=args[0] if op=="CALL_EX" else [args[0]]
            for descriptor in descriptors:
                allowed=("base","keyword","star","kwstar") if op=="CLASS_ARG" else ("positional","keyword","star","kwstar")
                if not isinstance(descriptor,list) or len(descriptor)!=2 or descriptor[0] not in allowed: raise BytecodeError("CALL_EX 설명자 오류")
                if descriptor[0]=="keyword" and not isinstance(descriptor[1],str): raise BytecodeError("CALL_EX 키워드 오류")
        elif op=="BUILD_UNPACK":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("BUILD_UNPACK 인자 오류")
            try:
                if args[0]["kind"] not in ("list","tuple","set"): raise TypeError
                if not isinstance(args[0]["starred"],list) or not all(isinstance(x,bool) for x in args[0]["starred"]): raise TypeError
            except (KeyError,TypeError) as exc: raise BytecodeError("BUILD_UNPACK 인자 오류") from exc
        elif op=="BUILD_DICT_UNPACK":
            if len(args)!=1 or not isinstance(args[0],list) or not all(item in ("pair","unpack") for item in args[0]): raise BytecodeError("BUILD_DICT_UNPACK 인자 오류")
        elif op=="COLLECTION_BEGIN":
            if len(args)!=1 or args[0] not in ("list","tuple","set","dict"): raise BytecodeError("COLLECTION_BEGIN 인자 오류")
        elif op=="COLLECTION_ADD":
            if len(args)!=1 or args[0] not in ("item","star","pair","unpack"): raise BytecodeError("COLLECTION_ADD 인자 오류")
        elif op=="FORMAT_VALUE":
            if len(args)!=1 or not isinstance(args[0],dict) or args[0].get("conversion") not in (None,"r","s","a") or not isinstance(args[0].get("has_spec"),bool): raise BytecodeError("FORMAT_VALUE 인자 오류")
        elif op=="CHAIN_COMPARE":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("CHAIN_COMPARE 인자 오류")
            try:
                valid={"==","!=","<","<=",">",">=","in","is","not in","is not"}
                if not args[0]["operators"] or not all(item in valid for item in args[0]["operators"]): raise TypeError
                if len(args[0]["operands"])!=len(args[0]["operators"])+1: raise TypeError
                for item in args[0]["operands"]: verify(CodeObject.from_dict(item))
            except (KeyError,TypeError) as exc: raise BytecodeError("CHAIN_COMPARE 인자 오류") from exc
        elif op=="MAKE_TYPE_ALIAS":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("MAKE_TYPE_ALIAS 인자 오류")
            try:
                if not isinstance(args[0]["name"],str): raise TypeError
                if args[0].get("value_text") is not None and not isinstance(args[0]["value_text"],str): raise TypeError
                if not isinstance(args[0]["parameters"],list): raise TypeError
                for item in args[0]["parameters"]:
                    if isinstance(item,(list,tuple)) and len(item)==2 and item[0] in ("typevar","typevartuple","paramspec") and isinstance(item[1],str): continue
                    if not isinstance(item,dict) or item.get("kind") not in ("typevar","typevartuple","paramspec") or not isinstance(item.get("name"),str): raise TypeError
                    for key in ("bound","default"):
                        if item.get(key) is not None: verify(CodeObject.from_dict(item[key]))
                    for key in ("bound_text","default_text"):
                        if item.get(key) is not None and not isinstance(item[key],str): raise TypeError
                verify(CodeObject.from_dict(args[0]["value"]))
            except (KeyError,TypeError) as exc: raise BytecodeError("MAKE_TYPE_ALIAS 인자 오류") from exc
        elif op=="MAKE_TYPE_PARAMETER":
            if len(args)!=1 or not isinstance(args[0],dict) or args[0].get("kind") not in ("typevar","typevartuple","paramspec") or not isinstance(args[0].get("name"),str): raise BytecodeError("MAKE_TYPE_PARAMETER 인자 오류")
            for key in ("bound","default"):
                if args[0].get(key) is not None: verify(CodeObject.from_dict(args[0][key]))
            for key in ("bound_text","default_text"):
                if args[0].get(key) is not None and not isinstance(args[0][key],str): raise BytecodeError("MAKE_TYPE_PARAMETER 인자 오류")
        elif op=="MATCH_PATTERN":
            if len(args)!=1: raise BytecodeError("MATCH_PATTERN 인자 오류")
            try: _verify_pattern(args[0])
            except (KeyError,TypeError) as exc: raise BytecodeError("MATCH_PATTERN 인자 오류") from exc
        elif op=="TRY":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("TRY 코드 객체 오류")
            payload=args[0]
            try:
                verify(CodeObject.from_dict(payload["body"]))
                for handler in payload["handlers"]:
                    if handler["type"] is not None:
                        if not isinstance(handler["type"],dict): raise TypeError
                        verify(CodeObject.from_dict(handler["type"]))
                    if handler["alias"] is not None and not isinstance(handler["alias"],str): raise TypeError
                    if handler.get("alias_scope","local") not in ("local","global","nonlocal"): raise TypeError
                    if not isinstance(handler.get("star",False),bool): raise TypeError
                    verify(CodeObject.from_dict(handler["code"]))
                for key in ("else","finally"):
                    if payload[key] is not None: verify(CodeObject.from_dict(payload[key]))
                for key in ("break_target","continue_target"):
                    if payload[key] is not None and (not isinstance(payload[key],int) or not 0<=payload[key]<=len(code.instructions)): raise TypeError
            except (KeyError,TypeError) as exc: raise BytecodeError("TRY 코드 객체 오류") from exc
        elif op=="COMPREHENSION":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("컴프리헨션 코드 객체 오류")
            payload=args[0]
            try:
                if payload["kind"] not in ("listcomp","setcomp","dictcomp","generatorexpr") or not payload["clauses"]: raise TypeError
                if not isinstance(payload.get("bindings",[]),list) or not all(isinstance(name,str) for name in payload.get("bindings",[])): raise TypeError
                for clause in payload["clauses"]:
                    _verify_target(clause["target"])
                    if not isinstance(clause.get("async",False),bool): raise TypeError
                    verify(CodeObject.from_dict(clause["iter"]))
                    for item in clause["filters"]: verify(CodeObject.from_dict(item))
                keys=("key","value") if payload["kind"]=="dictcomp" else ("element",)
                for key in keys: verify(CodeObject.from_dict(payload[key]))
            except (KeyError,TypeError) as exc: raise BytecodeError("컴프리헨션 코드 객체 오류") from exc
        elif op=="WITH":
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError("WITH 코드 객체 오류")
            try:
                verify(CodeObject.from_dict(args[0]["body"]))
                for manager in args[0]["managers"]:
                    if manager["alias"] is not None: _verify_target(manager["alias"])
                    verify(CodeObject.from_dict(manager["code"]))
            except (KeyError,TypeError) as exc: raise BytecodeError("WITH 코드 객체 오류") from exc
        elif op in ("ASYNC_FOR","ASYNC_WITH"):
            if len(args)!=1 or not isinstance(args[0],dict): raise BytecodeError(f"{op} 코드 객체 오류")
            try:
                if op=="ASYNC_FOR":
                    _verify_target(args[0]["target"])
                    verify(CodeObject.from_dict(args[0]["iter"])); verify(CodeObject.from_dict(args[0]["body"]))
                    if args[0].get("else") is not None: verify(CodeObject.from_dict(args[0]["else"]))
                else:
                    verify(CodeObject.from_dict(args[0]["body"]))
                    for manager in args[0]["managers"]:
                        if manager.get("alias") is not None: _verify_target(manager["alias"])
                        verify(CodeObject.from_dict(manager["code"]))
            except (KeyError,TypeError) as exc: raise BytecodeError(f"{op} 코드 객체 오류") from exc
        else: raise BytecodeError(f"허용되지 않은 HBC 명령어: {op}")
    _verify_stack(code)

def _verify_stack(code: CodeObject) -> None:
    """Follow every reachable branch and reject stack underflow/inconsistent merges."""
    instructions=code.instructions; count=len(instructions)
    pending=[(0,0)]; seen: dict[int,int]={}
    simple_effect={
        "CONST":1,"LOAD":1,"IMPORT":1,"IMPORT_FROM":1,"IMPORT_STAR":-1,"MAKE_TYPE_ALIAS":1,"MAKE_TYPE_PARAMETER":1,"SUPER":1,
        "STORE":-1,"STORE_GLOBAL":-1,"STORE_NONLOCAL":-1,"ANNOTATE":-1,"DELETE":0,"DELETE_GLOBAL":0,"DELETE_NONLOCAL":0,"SAVE_NAME":0,"RESTORE_NAME":0,"POP":-1,"ITER":0,"NOP":0,"FORMAT":0,"GET_ATTR":0,
        "SET_ATTR":-2,"DELETE_ATTR":-1,"GET_ITEM":-1,"SET_ITEM":-3,"DELETE_ITEM":-2,"ASSERT":-2,"DUP":1,"DUP2":2,"BUILD_SLICE":-2,
        "NEG":0,"POS":0,"NOT":0,"INVERT":0,
        "ADD":-1,"SUB":-1,"MUL":-1,"DIV":-1,"FLOORDIV":-1,"MOD":-1,"POW":-1,
        "IADD":-1,"ISUB":-1,"IMUL":-1,"IDIV":-1,"IFLOORDIV":-1,"IMOD":-1,"IPOW":-1,
        "EQ":-1,"NE":-1,"LT":-1,"LE":-1,"GT":-1,"GE":-1,"IN":-1,"IS":-1,"NOT_IN":-1,"IS_NOT":-1,
        "BIT_OR":-1,"BIT_XOR":-1,"BIT_AND":-1,"LSHIFT":-1,"RSHIFT":-1,"MATMUL":-1,
        "IBIT_OR":-1,"IBIT_XOR":-1,"IBIT_AND":-1,"ILSHIFT":-1,"IRSHIFT":-1,"IMATMUL":-1,
        "BOOL_AND":-1,"BOOL_OR":-1,
        "RAISE":-1,"RAISE_FROM":-2,"RERAISE":0,"SIGNAL_RETURN":-1,"SIGNAL_BREAK":0,"SIGNAL_CONTINUE":0,"YIELD":0,"YIELD_FROM":0,"AWAIT":0,"MATCH_PATTERN":0,"TRY":0,"COMPREHENSION":1,"WITH":0,"ASYNC_FOR":0,"ASYNC_WITH":0,"MAKE_INTERPOLATION":-3,"ANNOTATE_LAZY":0,"CALL_BEGIN":1,"CALL_ARG":-1,"CALL_READY":-1,"CLASS_BEGIN":1,"CLASS_ARG":-1,"COLLECTION_BEGIN":1,"COLLECTION_READY":0,
    }
    while pending:
        ip,depth=pending.pop()
        if ip==count: continue
        previous=seen.get(ip)
        if previous is not None:
            if previous!=depth: raise BytecodeError(f"명령어 {ip}의 스택 깊이가 일치하지 않습니다.")
            continue
        seen[ip]=depth; ins=instructions[ip]; op=ins[0]; arg=ins[1] if len(ins)>1 else None
        if op=="RETURN":
            if depth<1: raise BytecodeError(f"명령어 {ip}에서 스택 언더플로")
            continue
        if op=="JUMP": pending.append((arg,depth)); continue
        if op=="JUMP_FALSE":
            if depth<1: raise BytecodeError(f"명령어 {ip}에서 스택 언더플로")
            pending.extend(((arg,depth-1),(ip+1,depth-1))); continue
        if op in ("JUMP_IF_FALSE_OR_POP","JUMP_IF_TRUE_OR_POP"):
            if depth<1: raise BytecodeError(f"명령어 {ip}에서 스택 언더플로")
            pending.extend(((arg,depth),(ip+1,depth-1))); continue
        if op=="FOR_ITER":
            if depth<1: raise BytecodeError(f"명령어 {ip}에서 스택 언더플로")
            pending.extend(((arg,depth-1),(ip+1,depth+1))); continue
        if op=="CALL": effect=-arg
        elif op=="UNPACK": effect=arg-1
        elif op=="UNPACK_EX": effect=((arg>>16)+(arg&0xFFFF)+1)-1
        elif op=="CALL_EX": effect=-len(arg)
        elif op=="MAKE_FUNCTION": effect=1-len(arg["defaults"])-len(arg.get("annotations",[]))-len(arg.get("type_params",[]))
        elif op=="MAKE_CLASS": effect=-len(arg.get("type_params",[])) if arg.get("incremental_arguments") else 1-arg["bases"]-len(arg.get("keywords",[]))-len(arg.get("type_params",[]))
        elif op in ("BUILD_LIST","BUILD_TUPLE","BUILD_SET","BUILD_STRING","BUILD_TEMPLATE"): effect=1-arg
        elif op=="BUILD_DICT": effect=1-(arg*2)
        elif op=="BUILD_UNPACK": effect=1-len(arg["starred"])
        elif op=="BUILD_DICT_UNPACK": effect=1-sum(2 if item=="pair" else 1 for item in arg)
        elif op=="COLLECTION_ADD": effect=-2 if arg=="pair" else -1
        elif op=="FORMAT_VALUE": effect=-1 if arg["has_spec"] else 0
        elif op=="CHAIN_COMPARE": effect=1
        else: effect=simple_effect[op]
        new_depth=depth+effect
        if new_depth<0: raise BytecodeError(f"명령어 {ip}에서 스택 언더플로")
        pending.append((ip+1,new_depth))
