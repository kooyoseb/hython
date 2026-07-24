"""Hython Intermediate Representation and conservative optimizer."""
from __future__ import annotations
from dataclasses import dataclass, field
import operator

@dataclass
class HIRCode:
    name: str
    parameters: list[str]
    constants: list[object] = field(default_factory=list)
    instructions: list[list] = field(default_factory=list)
    lines: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "parameters": self.parameters, "constants": self.constants, "instructions": self.instructions,"lines":self.lines}

    @classmethod
    def from_dict(cls,value:dict) -> "HIRCode":
        return cls(value["name"],value["parameters"],value["constants"],value["instructions"],value.get("lines",[]))

_BINARY = {"ADD":operator.add,"SUB":operator.sub,"MUL":operator.mul,"DIV":operator.truediv,
           "FLOORDIV":operator.floordiv,"MOD":operator.mod,"POW":operator.pow,
           "EQ":operator.eq,"NE":operator.ne,"LT":operator.lt,"LE":operator.le,
           "GT":operator.gt,"GE":operator.ge,"IS":operator.is_}
_UNARY = {"NEG":operator.neg,"POS":operator.pos,"NOT":operator.not_}

def optimize_hir(code: HIRCode) -> HIRCode:
    """Fold safe constants without changing instruction offsets."""
    ins = code.instructions
    for index in range(len(ins) - 2):
        first, second, third = ins[index:index + 3]
        if first[0] == second[0] == "CONST" and third[0] in _BINARY:
            try:
                value = _BINARY[third[0]](code.constants[first[1]], code.constants[second[1]])
            except Exception:
                continue
            if isinstance(value, (type(None), bool, int, float, str)):
                code.constants.append(value)
                ins[index:index + 3] = [["CONST", len(code.constants)-1], ["NOP"], ["NOP"]]
    for index in range(len(ins) - 1):
        first, second = ins[index:index + 2]
        if first[0] == "CONST" and second[0] in _UNARY:
            try: value = _UNARY[second[0]](code.constants[first[1]])
            except Exception: continue
            code.constants.append(value)
            ins[index:index + 2] = [["CONST", len(code.constants)-1], ["NOP"]]
    for instruction in ins:
        if instruction[0] in ("MAKE_FUNCTION","MAKE_CLASS"):
            nested = instruction[1]["code"]
            child = HIRCode.from_dict(nested)
            optimized=optimize_hir(child).to_dict()
            instruction[1]["code"]=optimized
        elif instruction[0]=="TRY":
            payload=instruction[1]
            for key in ("body","else","finally"):
                nested=payload.get(key)
                if nested:
                    payload[key]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
            for handler in payload["handlers"]:
                nested=handler["code"]
                handler["code"]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
        elif instruction[0]=="COMPREHENSION":
            payload=instruction[1]
            for key in ("element","key","value"):
                nested=payload.get(key)
                if nested: payload[key]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
            for clause in payload["clauses"]:
                nested=clause["iter"]
                clause["iter"]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
                clause["filters"]=[optimize_hir(HIRCode.from_dict(n)).to_dict() for n in clause["filters"]]
        elif instruction[0]=="WITH":
            payload=instruction[1]; nested=payload["body"]
            payload["body"]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
            for manager in payload["managers"]:
                nested=manager["code"]
                manager["code"]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
        elif instruction[0] in ("ASYNC_FOR","ASYNC_WITH"):
            payload=instruction[1]
            for key in ("iter","body","else"):
                nested=payload.get(key)
                if nested: payload[key]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
            for manager in payload.get("managers",[]):
                nested=manager["code"]; manager["code"]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
        elif instruction[0]=="ANNOTATE_LAZY":
            nested=instruction[1]["code"]; instruction[1]["code"]=optimize_hir(HIRCode.from_dict(nested)).to_dict()
    return code

def format_hir(code: HIRCode) -> str:
    lines = [f"HIR {code.name}({', '.join(code.parameters)})"]
    for index, instruction in enumerate(code.instructions):
        argument = " ".join(map(str, instruction[1:]))
        lines.append(f"{index:04d}  {instruction[0]:14} {argument}")
    return "\n".join(lines)
