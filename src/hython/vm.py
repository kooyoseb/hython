"""Small stack VM for HBC v1."""
from __future__ import annotations
import operator
import asyncio
import types
import builtins
import inspect
import annotationlib
import importlib
import sys
from string.templatelib import Template,Interpolation
from collections.abc import Mapping,Sequence
from typing import TypeAliasType,TypeVar,TypeVarTuple,ParamSpec
from dataclasses import dataclass,field
from pathlib import Path
from types import SimpleNamespace
from .bytecode import CodeObject
from .bytecode import read as read_hbc

class VMError(RuntimeError): pass
class _GeneratorReturn(Exception):
    def __init__(self,value=None): self.value=value
class _AsyncGeneratorReturn(Exception): pass
_MISSING=object()
_MATCH_SELF_TYPES=(bool,bytearray,bytes,dict,float,frozenset,int,list,set,str,tuple)
def _exception_leaf_ids(error):
    if isinstance(error,BaseExceptionGroup):
        result=set()
        for child in error.exceptions: result.update(_exception_leaf_ids(child))
        return result
    return {id(error)}
def _merge_except_star(original,reraised,raised,remaining):
    leaf_ids=set()
    for subgroup in reraised: leaf_ids.update(_exception_leaf_ids(subgroup))
    if remaining is not None: leaf_ids.update(_exception_leaf_ids(remaining))
    if leaf_ids==_exception_leaf_ids(original): propagated=original
    else: propagated=original.subgroup(lambda error: not isinstance(error,BaseExceptionGroup) and id(error) in leaf_ids) if leaf_ids else None
    if not raised: return propagated
    if propagated is not None: raised.append(propagated)
    return raised[0] if len(raised)==1 else BaseExceptionGroup("",raised)
def _thrown_exception(exception,args):
    if isinstance(exception,type):
        if not issubclass(exception,BaseException): raise TypeError("예외 형식이 필요합니다.")
        if len(args)>2: raise TypeError("throw() 인자가 너무 많습니다.")
        value=args[0] if args else None
        error=value if isinstance(value,exception) else exception() if value is None else exception(value)
        if len(args)==2:
            traceback=args[1]
            if traceback is not None and not isinstance(traceback,types.TracebackType): raise TypeError("traceback 객체가 필요합니다.")
            error=error.with_traceback(traceback)
        return error
    if not isinstance(exception,BaseException): raise TypeError("예외 인스턴스가 필요합니다.")
    if args: raise TypeError("예외 인스턴스 뒤에는 별도 값을 전달할 수 없습니다.")
    return exception
class HythonModule(types.ModuleType):
    """Module object whose globals remain visible during circular imports."""
    def __init__(self,__name__,**attributes):
        super().__init__(__name__,attributes.pop("__doc__",None)); vars(self).update(attributes)
    def __getattribute__(self,name):
        if name=="__annotations__":
            namespace=types.ModuleType.__getattribute__(self,"__dict__")
            annotations=namespace.get(name)
            if isinstance(annotations,LazyAnnotations): return annotations.evaluate()
        return types.ModuleType.__getattribute__(self,name)
    def __getattr__(self,name):
        scope=vars(self).get("_hython_scope",{})
        if name in scope: return scope[name]
        raise AttributeError(name)
class ComprehensionScope(dict):
    """Isolate iteration targets while publishing assignment expressions immediately."""
    def __init__(self,outer,bindings):
        super().__init__(); self.outer=outer; self.bindings=set(bindings)
    def __contains__(self,name): return dict.__contains__(self,name) or name in self.outer
    def __getitem__(self,name):
        if dict.__contains__(self,name): return dict.__getitem__(self,name)
        return self.outer[name]
    def get(self,name,default=None):
        try: return self[name]
        except KeyError: return default
    def __setitem__(self,name,value):
        dict.__setitem__(self,name,value)
        if name in self.bindings: self.outer[name]=value
class TypeExpressionNamespace(dict):
    """Globals dictionary that resolves type-expression names against a live HBC scope."""
    def __init__(self,scope,initial=None,globals_=None): super().__init__(initial or {}); self.scope=scope; self.globals=globals_ or {}
    def __missing__(self,name):
        current=self.scope; seen=set()
        while isinstance(current,dict) and id(current) not in seen:
            seen.add(id(current))
            if name in current: return current[name]
            if name in current.get("$local_names",()): raise KeyError(name)
            current=current.get("$closure")
        if name in self.globals: return self.globals[name]
        raise KeyError(name)
    def __contains__(self,name):
        if dict.__contains__(self,name): return True
        try: self.__missing__(name); return True
        except KeyError: return False
    def get(self,name,default=None):
        try: return self[name]
        except KeyError: return default
class ClassAnnotationScope(dict):
    """Live class namespace view retaining the lexical outer scope for lazy annotations."""
    def __init__(self,owner,outer,type_parameters=None): super().__init__({"$closure":outer,**(type_parameters or {})}); self.owner=owner
    def __contains__(self,name): return dict.__contains__(self,name) or name in vars(self.owner)
    def __getitem__(self,name):
        if name!="$closure" and name in vars(self.owner): return vars(self.owner)[name]
        if dict.__contains__(self,name): return dict.__getitem__(self,name)
        raise KeyError(name)
    def get(self,name,default=None):
        try: return self[name]
        except KeyError: return default
class LazyAnnotations(dict):
    """Dictionary-compatible Python 3.14 annotation thunk container."""
    def __init__(self,vm,scope,initial=None):
        super().__init__(initial or {}); self.vm=vm; self.scope=scope; self.codes={}; self.strings={}; self.evaluated=False; self.owner=None
    def add(self,name,code,text=""): self.codes[name]=code; self.strings[name]=text; self.evaluated=False
    def evaluate(self,format=annotationlib.Format.VALUE,*_args,**_kwargs):
        if format==annotationlib.Format.STRING:
            for code in self.codes.values():
                try: self.vm.run(CodeObject.from_dict(code),self.scope)
                except NameError: pass
            return dict(self.strings)
        if format==annotationlib.Format.FORWARDREF:
            class ForwardGlobals(dict):
                def __missing__(inner,key): return annotationlib.ForwardRef(key,owner=self.owner)
            environment=ForwardGlobals(self.scope)
            return {name:eval(text,environment) for name,text in self.strings.items()}
        if not self.evaluated:
            pending={name:self.vm.run(CodeObject.from_dict(code),self.scope) for name,code in self.codes.items() if not dict.__contains__(self,name)}
            dict.update(self,pending)
            self.evaluated=True
        return self
    def __getitem__(self,key): self.evaluate(); return dict.__getitem__(self,key)
    def __iter__(self): self.evaluate(); return dict.__iter__(self)
    def __len__(self): self.evaluate(); return dict.__len__(self)
    def __repr__(self): self.evaluate(); return dict.__repr__(self)
    def __eq__(self,other): self.evaluate(); return dict.__eq__(self,other)
    def items(self): self.evaluate(); return dict.items(self)
    def keys(self): self.evaluate(); return dict.keys(self)
    def values(self): self.evaluate(); return dict.values(self)
    def get(self,key,default=None): self.evaluate(); return dict.get(self,key,default)
class HythonReturn(BaseException):
    def __init__(self,value): self.value=value
class HythonBreak(BaseException): pass
class HythonContinue(BaseException): pass
class HythonAwait(BaseException):
    def __init__(self,awaitable): self.awaitable=awaitable
class HythonAsyncDelegate(BaseException):
    def __init__(self,iterator): self.iterator=iterator

@dataclass
class CallArguments:
    positional: list
    keywords: dict

@dataclass
class CollectionBuilder:
    kind: str
    value: object

@dataclass(eq=False)
class Function:
    code: CodeObject
    globals: dict
    defaults: dict = None
    signature: dict = None
    closure: dict = None
    generator: bool = False
    asynchronous: bool = False
    annotations: dict = None
    type_parameters: dict = None
    class_owner: type = None
    function_name: str = None
    qualname: str = None
    module_name: str = None
    docstring: str = None
    annotation_codes: dict = None
    annotations_evaluated: bool = False
    annotation_strings: dict = None
    runtime_vm: object = None
    local_names: set = None
    free_names: set = None
    class_cell: object = None
    positional_defaults: object = _MISSING
    keyword_defaults: object = _MISSING
    annotation_callable: object = _MISSING
    raw_type_parameters: object = _MISSING
    user_attributes: dict = field(default_factory=dict)
    builtins_namespace: object = _MISSING
    def __getattribute__(self,name):
        if name=="__dict__": return object.__getattribute__(self,"user_attributes")
        if name=="__builtins__":
            value=object.__getattribute__(self,"builtins_namespace")
            if value is _MISSING: value=object.__getattribute__(self,"globals").get("__builtins__",builtins.__dict__)
            return value.__dict__ if isinstance(value,types.ModuleType) else value
        if name=="__annotations__": return object.__getattribute__(self,"_evaluate_annotations")()
        if name=="__annotate__":
            custom=object.__getattribute__(self,"annotation_callable")
            if custom is not _MISSING: return custom
            return object.__getattribute__(self,"_evaluate_annotations") if object.__getattribute__(self,"annotation_codes") else None
        if name=="__type_params__":
            raw=object.__getattribute__(self,"raw_type_parameters")
            return raw if raw is not _MISSING else tuple((object.__getattribute__(self,"type_parameters") or {}).values())
        if name=="__name__": return object.__getattribute__(self,"function_name") or object.__getattribute__(self,"code").name
        if name=="__qualname__": return object.__getattribute__(self,"qualname") or self.__name__
        if name=="__module__": return object.__getattribute__(self,"module_name")
        if name=="__doc__": return object.__getattribute__(self,"docstring")
        if name=="__code__": return object.__getattribute__(self,"code")
        if name=="__globals__": return object.__getattribute__(self,"globals")
        if name=="__closure__": return object.__getattribute__(self,"closure")
        if name=="__signature__": return object.__getattribute__(self,"_inspect_signature")()
        if name=="__defaults__":
            raw=object.__getattribute__(self,"positional_defaults")
            if raw is not _MISSING: return raw
            signature=object.__getattribute__(self,"signature") or {}; defaults=object.__getattribute__(self,"defaults") or {}
            values=[defaults[item] for item in signature.get("positional",[]) if item in defaults]
            return tuple(values) if values else None
        if name=="__kwdefaults__":
            raw=object.__getattribute__(self,"keyword_defaults")
            if raw is not _MISSING: return raw
            signature=object.__getattribute__(self,"signature") or {}; defaults=object.__getattribute__(self,"defaults") or {}
            values={item:defaults[item] for item in signature.get("keyword_only",[]) if item in defaults}
            return values or None
        try: return object.__getattribute__(self,name)
        except AttributeError:
            attributes=object.__getattribute__(self,"user_attributes")
            if name in attributes: return attributes[name]
            raise
    def __setattr__(self,name,value):
        if name=="__dict__":
            if not isinstance(value,dict): raise TypeError("__dict__ must be set to a dictionary")
            object.__setattr__(self,"user_attributes",value); return
        if name=="__builtins__": raise AttributeError("readonly attribute")
        if name in ("__globals__","__closure__"): raise AttributeError("readonly attribute")
        if name=="__code__":
            if not isinstance(value,CodeObject): raise TypeError("__code__ must be set to a Hython code object")
            object.__setattr__(self,"code",value); return
        if name=="__annotations__":
            if value is not None and not isinstance(value,dict): raise TypeError("__annotations__ must be set to a dict object")
            object.__setattr__(self,"annotations",{} if value is None else value)
            object.__setattr__(self,"annotations_evaluated",True); object.__setattr__(self,"annotation_codes",{})
            object.__setattr__(self,"annotation_strings",{}); object.__setattr__(self,"annotation_callable",None); return
        if name=="__annotate__":
            if value is not None and not callable(value): raise TypeError("__annotate__ must be callable or None")
            object.__setattr__(self,"annotation_callable",value)
            if value is not None: object.__setattr__(self,"annotations_evaluated",False)
            return
        if name=="__name__":
            if not isinstance(value,str): raise TypeError("__name__ must be set to a string object")
            object.__setattr__(self,"function_name",value); return
        if name=="__qualname__":
            if not isinstance(value,str): raise TypeError("__qualname__ must be set to a string object")
            object.__setattr__(self,"qualname",value); return
        if name=="__type_params__":
            if not isinstance(value,tuple): raise TypeError("__type_params__ must be set to a tuple")
            object.__setattr__(self,"raw_type_parameters",value); return
        if name=="__module__": object.__setattr__(self,"module_name",value); return
        if name=="__doc__": object.__setattr__(self,"docstring",value); return
        if name=="__defaults__":
            if value is not None and not isinstance(value,tuple): raise TypeError("__defaults__ must be set to a tuple object")
            signature=object.__getattribute__(self,"signature") or {}; positional=signature.get("positional",[])
            defaults=dict(object.__getattribute__(self,"defaults") or {})
            for parameter in positional: defaults.pop(parameter,None)
            if value:
                usable=value[-len(positional):] if positional else ()
                defaults.update(zip(positional[-len(usable):],usable))
            object.__setattr__(self,"defaults",defaults); object.__setattr__(self,"positional_defaults",value); return
        if name=="__kwdefaults__":
            if value is not None and not isinstance(value,dict): raise TypeError("__kwdefaults__ must be set to a dict object")
            signature=object.__getattribute__(self,"signature") or {}; keyword_only=signature.get("keyword_only",[])
            defaults=dict(object.__getattribute__(self,"defaults") or {})
            for parameter in keyword_only: defaults.pop(parameter,None)
            if value: defaults.update({key:item for key,item in value.items() if key in keyword_only})
            object.__setattr__(self,"defaults",defaults); object.__setattr__(self,"keyword_defaults",value); return
        fields=getattr(type(self),"__dataclass_fields__",{})
        if name in fields or name.startswith("_") or "user_attributes" not in object.__getattribute__(self,"__dict__"):
            object.__setattr__(self,name,value); return
        object.__getattribute__(self,"user_attributes")[name]=value
    def __delattr__(self,name):
        if name=="__dict__": raise TypeError("cannot delete __dict__")
        attributes=object.__getattribute__(self,"user_attributes")
        if name in attributes: del attributes[name]; return
        object.__delattr__(self,name)
    def _evaluate_annotations(self,format=annotationlib.Format.VALUE,*_args,**_kwargs):
        custom=self.annotation_callable
        if custom is not _MISSING and custom is not None:
            if format!=annotationlib.Format.VALUE: return custom(format)
            if not self.annotations_evaluated:
                result=custom(format)
                if not isinstance(result,dict): raise TypeError("__annotate__ returned a non-dict")
                self.annotations=result; self.annotations_evaluated=True
            return self.annotations or {}
        codes=self.annotation_codes or {}
        if format==annotationlib.Format.STRING:
            scope=self._annotation_scope()
            vm=VM(); vm.globals=self.globals
            for code in codes.values():
                try: vm.run(CodeObject.from_dict(code),scope)
                except NameError: pass
            return dict(self.annotation_strings or {})
        if format==annotationlib.Format.FORWARDREF:
            owner=self
            class ForwardGlobals(dict):
                def __missing__(inner,key): return annotationlib.ForwardRef(key,owner=owner)
            environment=ForwardGlobals(self._annotation_values())
            return {name:eval(text,environment) for name,text in (self.annotation_strings or {}).items()}
        if codes and not self.annotations_evaluated:
            vm=VM(); vm.globals=self.globals
            scope=self._annotation_scope()
            self.annotations={name:vm.run(CodeObject.from_dict(code),scope) for name,code in codes.items()}
            self.annotations_evaluated=True
        return self.annotations or {}
    def _annotation_values(self):
        values={**self.globals}
        values.update({name:value for name,value in (self.closure or {}).items() if not name.startswith("$")})
        if self.class_owner is not None:
            values.update({parameter.__name__:parameter for parameter in getattr(self.class_owner,"__type_params__",())})
            values.update(vars(self.class_owner))
        values.update(self.type_parameters or {})
        return values
    def _annotation_scope(self):
        outer=self.closure or {}
        if self.class_owner is not None:
            class_parameters={parameter.__name__:parameter for parameter in getattr(self.class_owner,"__type_params__",())}
            outer=ClassAnnotationScope(self.class_owner,outer,class_parameters)
        return TypeExpressionNamespace(outer,self.type_parameters or {},self.globals)
    def _inspect_signature(self):
        specification=self.signature or {"positional":self.code.parameters,"positional_only":[],"keyword_only":[],"vararg":None,"kwarg":None}
        defaults=self.defaults or {}; annotations=self.__annotations__; parameters=[]; positional_only=set(specification.get("positional_only",[]))
        for name in specification.get("positional",[]):
            parameters.append(inspect.Parameter(name,inspect.Parameter.POSITIONAL_ONLY if name in positional_only else inspect.Parameter.POSITIONAL_OR_KEYWORD,default=defaults.get(name,inspect.Parameter.empty),annotation=annotations.get(name,inspect.Parameter.empty)))
        if specification.get("vararg"):
            name=specification["vararg"]; parameters.append(inspect.Parameter(name,inspect.Parameter.VAR_POSITIONAL,annotation=annotations.get(name,inspect.Parameter.empty)))
        for name in specification.get("keyword_only",[]):
            parameters.append(inspect.Parameter(name,inspect.Parameter.KEYWORD_ONLY,default=defaults.get(name,inspect.Parameter.empty),annotation=annotations.get(name,inspect.Parameter.empty)))
        if specification.get("kwarg"):
            name=specification["kwarg"]; parameters.append(inspect.Parameter(name,inspect.Parameter.VAR_KEYWORD,annotation=annotations.get(name,inspect.Parameter.empty)))
        return inspect.Signature(parameters,return_annotation=annotations.get("return",inspect.Signature.empty))
    def __get__(self, instance, owner=None):
        if instance is None: return self
        return BoundFunction(self,instance)
    def __call__(self,*args,**kwargs):
        vm=self.runtime_vm or VM(); vm.globals=self.globals
        scope={**(self.type_parameters or {}),**vm.bind(self,args,kwargs),"$closure":self.closure or {},"$local_names":set(self.local_names or self.code.parameters),"$free_names":set(self.free_names or ()),"$qualname_prefix":f"{self.__qualname__}.<locals>"}
        if self.class_cell is not None:
            try: scope["__class__"]=self.class_cell.cell_contents
            except ValueError: pass
            scope["$has_class_cell"]=True
        if self.class_cell is not None: scope["$class_cell"]=self.class_cell
        if self.generator and self.asynchronous: return HythonAsyncGenerator(HythonGenerator(vm,self.code,scope,self.__name__,self.__qualname__))
        if self.generator: return HythonGenerator(vm,self.code,scope,self.__name__,self.__qualname__)
        if self.asynchronous: return HythonCoroutine(vm,self.code,scope,self.__name__,self.__qualname__)
        active_exception=sys.exception()
        if active_exception is not None: scope["$active_exception"]=active_exception
        try: return vm.run(self.code,scope)
        except HythonReturn as signal: return signal.value

@dataclass(frozen=True)
class BoundFunction:
    function: Function
    instance: object
    def __call__(self,*args,**kwargs): return self.function(self.instance,*args,**kwargs)
    def __getattr__(self,name):
        if name=="__signature__":
            signature=self.function.__signature__; parameters=list(signature.parameters.values())
            return signature.replace(parameters=parameters[1:] if parameters else [])
        return getattr(self.function,name)
    @property
    def __self__(self): return self.instance
    @property
    def __func__(self): return self.function
    @property
    def __func__(self): return self.function

class HythonGenerator:
    """Resumable HBC frame implementing lazy yield/yield-from."""
    def __init__(self,vm,code,local,function_name=None,qualname=None):
        self.vm=vm; self.code=code; self.local=local; self.function_name=function_name or code.name; self.qualname=qualname or self.function_name; self.stack=[]; self.ip=0; self.delegate=None; self.delegate_push_result=True; self.delegate_control=None; self.done=False; self.started=False; self.suspended=False; self._running=False
    @property
    def gi_code(self): return self.code
    @property
    def gi_frame(self): return None if self.done else SimpleNamespace(f_code=self.code,f_locals=self.local,f_lasti=self.ip-1)
    @property
    def gi_running(self): return self._running
    @property
    def gi_suspended(self): return self.suspended and not self._running and not self.done
    @property
    def gi_yieldfrom(self): return self.delegate
    def __getattribute__(self,name):
        if name=="__name__": return object.__getattribute__(self,"function_name")
        if name=="__qualname__": return object.__getattribute__(self,"qualname")
        return object.__getattribute__(self,name)
    def __iter__(self): return self
    def __next__(self): return self.send(None)
    def send(self,value):
        if self._running: raise ValueError("generator already executing")
        if self.done: raise StopIteration
        active_exception=sys.exception()
        if active_exception is not None and "$active_exception" not in self.local:
            self.local["$active_exception"]=active_exception
            self.local["$inherited_active_exception"]=active_exception
        self._running=True
        try: return self._send(value)
        except _GeneratorReturn as signal: raise StopIteration(signal.value) from None
        except StopIteration as exc:
            self.done=True
            raise RuntimeError("generator raised StopIteration") from exc
        except (HythonReturn,HythonBreak,HythonContinue): raise
        except BaseException as exc:
            self.vm.restore_saved_names(self.local)
            index=max(0,self.ip-1); line=self.code.lines[index] if self.code.lines and index<len(self.code.lines) else 0
            frames=getattr(exc,"__hython_frames__",None)
            if frames is None: frames=[]; setattr(exc,"__hython_frames__",frames)
            frame=(self.code.name,line,index)
            if not frames or frames[-1]!=frame:
                frames.append(frame); exc.add_note(f"하이썬 위치: {self.code.name}:{line}" if line else f"하이썬 위치: {self.code.name}")
            raise
        finally:
            inherited=self.local.pop("$inherited_active_exception",_MISSING)
            if inherited is not _MISSING and self.local.get("$active_exception") is inherited:
                self.local.pop("$active_exception",None)
            self._running=False
    def _send(self,value):
        if self.done: raise StopIteration
        if not self.started and value is not None: raise TypeError("시작 전 제너레이터에는 None만 보낼 수 있습니다.")
        if self.suspended:
            if self.delegate is None: self.stack.append(value)
            self.suspended=False
        self.started=True
        if self.delegate is not None:
            try:
                return next(self.delegate) if value is None else self.delegate.send(value)
            except HythonReturn as signal:
                self.done=True; self.delegate=None; self.stack.clear()
                raise _GeneratorReturn(signal.value)
            except (HythonBreak,HythonContinue) as signal:
                control=self.delegate_control; self.delegate=None; self.delegate_control=None
                target=control["break_target"] if isinstance(signal,HythonBreak) else control["continue_target"]
                if target is None: raise
                self.ip=target; self.suspended=False
                return self._send(None)
            except StopIteration as stop:
                self.delegate=None
                if self.delegate_push_result: self.stack.append(stop.value)
                self.delegate_push_result=True
        insns=self.code.instructions; stack=self.stack
        binary={"ADD":operator.add,"SUB":operator.sub,"MUL":operator.mul,"DIV":operator.truediv,"FLOORDIV":operator.floordiv,"MOD":operator.mod,"POW":operator.pow,
                "EQ":operator.eq,"NE":operator.ne,"LT":operator.lt,"LE":operator.le,"GT":operator.gt,"GE":operator.ge,"IN":lambda a,b:a in b,"IS":operator.is_,"NOT_IN":lambda a,b:a not in b,"IS_NOT":operator.is_not}
        binary.update({"BIT_OR":operator.or_,"BIT_XOR":operator.xor,"BIT_AND":operator.and_,"LSHIFT":operator.lshift,"RSHIFT":operator.rshift,"MATMUL":operator.matmul})
        binary.update({"IADD":operator.iadd,"ISUB":operator.isub,"IMUL":operator.imul,"IDIV":operator.itruediv,"IFLOORDIV":operator.ifloordiv,"IMOD":operator.imod,"IPOW":operator.ipow,"IBIT_OR":operator.ior,"IBIT_XOR":operator.ixor,"IBIT_AND":operator.iand,"ILSHIFT":operator.ilshift,"IRSHIFT":operator.irshift,"IMATMUL":operator.imatmul})
        while self.ip<len(insns):
            ins=insns[self.ip]; op=ins[0]; arg=ins[1] if len(ins)>1 else None; self.ip+=1
            if op=="CONST": stack.append(self.code.constants[arg])
            elif op=="LOAD":
                if arg in self.local: stack.append(self.local[arg])
                elif arg in self.local.get("$local_names",()): raise UnboundLocalError(f"local variable '{arg}' referenced before assignment")
                elif arg in self.local.get("$free_names",()):
                    closure=self.vm.nonlocal_scope(self.local,arg)
                    if arg not in closure: raise NameError(f"free variable '{arg}' is not defined in enclosing scope")
                    stack.append(closure[arg])
                elif (found:=self.vm.lookup_closure(self.local,arg))[0]: stack.append(found[1])
                elif "$class_outer" in self.local and arg not in self.local.get("$class_local_names",()) and arg in self.local["$class_outer"]: stack.append(self.local["$class_outer"][arg])
                elif arg in self.vm.globals: stack.append(self.vm.globals[arg])
                else: raise NameError(f"name '{arg}' is not defined")
            elif op=="STORE": self.local[arg]=stack.pop()
            elif op=="SAVE_NAME": self.vm.save_name(self.local,arg)
            elif op=="RESTORE_NAME": self.vm.restore_name(self.local,arg)
            elif op=="ANNOTATE": self.local.setdefault("__annotations__",{})[arg]=stack.pop()
            elif op=="ANNOTATE_LAZY": self.vm.register_annotation(self.local,arg)
            elif op=="SUPER": stack.append(self.vm.zero_argument_super(self.local,arg))
            elif op=="MAKE_TYPE_ALIAS": stack.append(self.vm.make_type_alias(arg,self.local))
            elif op=="MAKE_TYPE_PARAMETER": stack.append(self.vm.make_type_parameter(arg,self.local))
            elif op=="STORE_GLOBAL": self.vm.globals[arg]=stack.pop()
            elif op=="STORE_NONLOCAL":
                closure=self.vm.nonlocal_scope(self.local,arg)
                closure[arg]=stack.pop()
            elif op=="DELETE":
                if arg not in self.local: raise self.vm.missing_delete_error(self.local,arg)
                del self.local[arg]
            elif op=="DELETE_GLOBAL":
                if arg not in self.vm.globals: raise NameError(f"name '{arg}' is not defined")
                del self.vm.globals[arg]
            elif op=="DELETE_NONLOCAL":
                closure=self.vm.nonlocal_scope(self.local,arg)
                if arg not in closure: raise NameError(f"free variable '{arg}' is not defined in enclosing scope")
                del closure[arg]
            elif op=="UNPACK":
                values=self.vm.unpack_exact(stack.pop(),arg)
                stack.extend(reversed(values))
            elif op=="UNPACK_EX":
                before=arg>>16; after=arg&0xFFFF
                stack.extend(reversed(self.vm.unpack_extended(stack.pop(),before,after)))
            elif op=="POP": stack.pop()
            elif op=="DUP": stack.append(stack[-1])
            elif op=="DUP2": stack.extend(stack[-2:])
            elif op in binary: b=stack.pop(); a=stack.pop(); stack.append(binary[op](a,b))
            elif op in ("NEG","POS","NOT","INVERT"): stack.append({"NEG":operator.neg,"POS":operator.pos,"NOT":operator.not_,"INVERT":operator.invert}[op](stack.pop()))
            elif op=="JUMP": self.ip=arg
            elif op=="JUMP_FALSE":
                if not stack.pop(): self.ip=arg
            elif op=="JUMP_IF_FALSE_OR_POP":
                if not stack[-1]: self.ip=arg
                else: stack.pop()
            elif op=="JUMP_IF_TRUE_OR_POP":
                if stack[-1]: self.ip=arg
                else: stack.pop()
            elif op=="ITER": stack.append(iter(stack.pop()))
            elif op=="FOR_ITER":
                try: stack.append(next(stack[-1]))
                except StopIteration: stack.pop(); self.ip=arg
            elif op in ("BUILD_LIST","BUILD_TUPLE","BUILD_SET"):
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(list(values) if op=="BUILD_LIST" else tuple(values) if op=="BUILD_TUPLE" else set(values))
            elif op=="BUILD_DICT":
                values=stack[-arg*2:] if arg else []
                if arg: del stack[-arg*2:]
                stack.append(dict(zip(values[::2],values[1::2])))
            elif op=="BUILD_UNPACK":
                count=len(arg["starred"]); values=stack[-count:] if count else []
                if count: del stack[-count:]
                merged=[]
                for value,starred in zip(values,arg["starred"]): merged.extend(value) if starred else merged.append(value)
                stack.append(tuple(merged) if arg["kind"]=="tuple" else set(merged) if arg["kind"]=="set" else merged)
            elif op=="BUILD_DICT_UNPACK":
                count=sum(2 if item=="pair" else 1 for item in arg); values=stack[-count:] if count else []
                if count: del stack[-count:]
                result={}; index=0
                for item in arg:
                    if item=="pair": result[values[index]]=values[index+1]; index+=2
                    else: result.update(values[index]); index+=1
                stack.append(result)
            elif op=="COLLECTION_BEGIN": stack.append(self.vm.collection_builder(arg))
            elif op=="COLLECTION_ADD":
                value=stack.pop(); key=stack.pop() if arg=="pair" else None
                self.vm.add_collection_item(stack[-1],arg,value,key)
            elif op=="COLLECTION_READY": stack.append(self.vm.finish_collection(stack.pop()))
            elif op=="BUILD_SLICE":
                step=stack.pop(); stop=stack.pop(); start=stack.pop(); stack.append(slice(start,stop,step))
            elif op=="GET_ATTR": stack.append(getattr(stack.pop(),arg))
            elif op=="SET_ATTR":
                value=stack.pop(); target=stack.pop(); setattr(target,arg,value)
            elif op=="GET_ITEM": index=stack.pop(); stack.append(stack.pop()[index])
            elif op=="SET_ITEM":
                value=stack.pop(); index=stack.pop(); stack.pop()[index]=value
            elif op=="DELETE_ITEM":
                index=stack.pop(); del stack.pop()[index]
            elif op=="DELETE_ATTR": delattr(stack.pop(),arg)
            elif op=="IMPORT": stack.append(self.vm.import_module(arg,self.code))
            elif op=="IMPORT_FROM": stack.append(self.vm.import_from(arg["module"],arg["name"],self.code))
            elif op=="IMPORT_STAR": self.vm.import_star(self.local,stack.pop())
            elif op=="FORMAT": stack.append(str(stack.pop()))
            elif op=="FORMAT_VALUE":
                spec=stack.pop() if arg["has_spec"] else ""; value=stack.pop()
                if arg["conversion"]=="r": value=repr(value)
                elif arg["conversion"]=="s": value=str(value)
                elif arg["conversion"]=="a": value=ascii(value)
                stack.append(format(value,spec))
            elif op=="BUILD_STRING":
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append("".join(values))
            elif op=="MAKE_INTERPOLATION":
                spec=stack.pop(); conversion=stack.pop(); expression=stack.pop(); value=stack.pop(); stack.append(Interpolation(value,expression,conversion,spec))
            elif op=="BUILD_TEMPLATE":
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(Template(*values))
            elif op=="ASSERT":
                message=stack.pop(); condition=stack.pop()
                if not condition: raise AssertionError(message) if message is not None else AssertionError()
            elif op=="RAISE": raise stack.pop()
            elif op=="RAISE_FROM":
                cause=stack.pop(); error=stack.pop(); raise error from cause
            elif op=="RERAISE":
                self.vm.reraise(self.local)
            elif op=="MATCH_PATTERN":
                bindings={}; matched=self.vm.match_pattern(stack.pop(),arg,bindings,self.local)
                if matched: self.vm.apply_pattern_bindings(self.local,bindings)
                stack.append(matched)
            elif op=="CHAIN_COMPARE": stack.append(self.vm.run_compare_chain(arg,self.local))
            elif op=="CALL":
                args=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(self.vm.call_value(stack.pop(),args,{},self.local))
            elif op=="CALL_EX":
                values=stack[-len(arg):] if arg else []
                if arg: del stack[-len(arg):]
                function=stack.pop(); positional,keywords=self.vm.expand_call_arguments(arg,values)
                stack.append(self.vm.call_value(function,positional,keywords,self.local))
            elif op=="CALL_BEGIN": stack.append(CallArguments([],{}))
            elif op=="CALL_ARG": self.vm.add_call_argument(stack[-2],arg,stack.pop())
            elif op=="CALL_READY":
                arguments=stack.pop(); function=stack.pop()
                stack.append(self.vm.call_value(function,arguments.positional,arguments.keywords,self.local))
            elif op=="CLASS_BEGIN": stack.append(CallArguments([],{}))
            elif op=="CLASS_ARG": self.vm.add_class_argument(stack[-2],arg,stack.pop())
            elif op=="MAKE_FUNCTION":
                stack.append(self.vm.create_function(arg,self.local,stack))
            elif op=="MAKE_CLASS":
                stack.append(self.vm.create_class(arg,self.local,stack))
            elif op=="COMPREHENSION":
                if arg.get("async",any(clause.get("async",False) for clause in arg["clauses"])):
                    if arg["kind"]=="generatorexpr":
                        self.suspended=True; raise HythonAwait(self.vm.prepare_async_generator_expression(arg,self.local))
                    self.suspended=True; raise HythonAwait(self.vm.run_async_comprehension(arg,self.local))
                if arg["kind"]=="generatorexpr": stack.append(self.vm.generator_expression(arg,self.local)); continue
                scope=ComprehensionScope(self.vm.comprehension_parent(self.local),arg.get("bindings",())); result={} if arg["kind"]=="dictcomp" else set() if arg["kind"]=="setcomp" else []
                def collect(index):
                    if index<len(arg["clauses"]):
                        clause=arg["clauses"][index]
                        for item in self.vm.run(CodeObject.from_dict(clause["iter"]),scope):
                            self.vm.assign_target(scope,clause["target"],item)
                            if all(self.vm.run(CodeObject.from_dict(test),scope) for test in clause["filters"]): collect(index+1)
                        return
                    if arg["kind"]=="dictcomp":
                        key=self.vm.run(CodeObject.from_dict(arg["key"]),scope)
                        result[key]=self.vm.run(CodeObject.from_dict(arg["value"]),scope)
                    else:
                        value=self.vm.run(CodeObject.from_dict(arg["element"]),scope)
                        result.add(value) if arg["kind"]=="setcomp" else result.append(value)
                collect(0); self.vm.commit_comprehension_bindings(arg,scope,self.local); stack.append(result)
            elif op=="YIELD":
                result=stack.pop(); self.suspended=True; return result
            elif op=="AWAIT":
                awaitable=stack.pop(); self.vm.inherit_active_exception(awaitable,self.local)
                self.suspended=True; raise HythonAwait(awaitable)
            elif op=="ASYNC_FOR": raise HythonAsyncDelegate(self._run_async_for(arg))
            elif op=="ASYNC_WITH": raise HythonAsyncDelegate(self._run_async_with(arg))
            elif op=="YIELD_FROM":
                self.delegate=iter(stack.pop()); self.delegate_push_result=True; self.delegate_control=None
                try:
                    result=next(self.delegate); self.suspended=True; return result
                except StopIteration as stop: self.delegate=None; stack.append(stop.value)
            elif op=="TRY":
                self.delegate=self._run_try(arg); self.delegate_push_result=False; self.delegate_control=arg
                try:
                    result=next(self.delegate); self.suspended=True; return result
                except HythonReturn as signal:
                    self.done=True; self.delegate=None; raise _GeneratorReturn(signal.value)
                except StopIteration:
                    self.delegate=None; self.delegate_push_result=True
            elif op=="WITH":
                self.delegate=self._run_with(arg); self.delegate_push_result=False; self.delegate_control=arg
                try:
                    result=next(self.delegate); self.suspended=True; return result
                except HythonReturn as signal:
                    self.done=True; self.delegate=None; raise _GeneratorReturn(signal.value)
                except StopIteration:
                    self.delegate=None; self.delegate_push_result=True
            elif op=="RETURN": self.done=True; raise _GeneratorReturn(stack.pop())
            elif op=="SIGNAL_RETURN": self.done=True; raise HythonReturn(stack.pop())
            elif op=="SIGNAL_BREAK": self.done=True; raise HythonBreak()
            elif op=="SIGNAL_CONTINUE": self.done=True; raise HythonContinue()
            elif op=="NOP": pass
            else: raise VMError(f"제너레이터에서 아직 지원하지 않는 HBC 명령어: {op}")
        self.done=True; raise _GeneratorReturn()
    def _run_child(self,payload):
        return HythonGenerator(self.vm,CodeObject.from_dict(payload),self.local)
    def _run_try(self,arg):
        """Execute structured TRY payload while preserving yields and injected exceptions."""
        try:
            try:
                yield from self._run_child(arg["body"])
            except (HythonReturn,HythonBreak,HythonContinue):
                raise
            except BaseException as exc:
                if arg["handlers"] and arg["handlers"][0].get("star",False):
                    original=exc if isinstance(exc,BaseExceptionGroup) else BaseExceptionGroup("",[exc]); remaining=original; raised=[]; reraised=[]
                    for handler in arg["handlers"]:
                        expected=self.vm.run(CodeObject.from_dict(handler["type"]),self.local)
                        matched,remaining=remaining.split(expected)
                        if matched is None: continue
                        if handler["alias"]: self.vm.assign_name(self.local,handler["alias"],matched,handler.get("alias_scope","local"))
                        previous=self.vm.push_active_exception(self.local,matched)
                        try: yield from self._run_child(handler["code"])
                        except BaseException as failure:
                            (reraised if failure is matched else raised).append(failure)
                        finally:
                            self.vm.pop_active_exception(self.local,previous)
                            if handler["alias"]: self.vm.delete_name(self.local,handler["alias"],handler.get("alias_scope","local"))
                    failure=_merge_except_star(original,reraised,raised,remaining)
                    if failure is not None: raise failure
                    return
                handled=False
                for handler in arg["handlers"]:
                    expected=self.vm.run(CodeObject.from_dict(handler["type"]),self.local) if handler["type"] else BaseException
                    if isinstance(exc,expected):
                        if handler["alias"]: self.vm.assign_name(self.local,handler["alias"],exc,handler.get("alias_scope","local"))
                        previous=self.vm.push_active_exception(self.local,exc)
                        try: yield from self._run_child(handler["code"])
                        finally:
                            self.vm.pop_active_exception(self.local,previous)
                            if handler["alias"]: self.vm.delete_name(self.local,handler["alias"],handler.get("alias_scope","local"))
                        handled=True; break
                if not handled: raise
            else:
                if arg["else"]: yield from self._run_child(arg["else"])
        finally:
            if arg["finally"]:
                active=sys.exception(); previous=_MISSING; pushed=False
                if active is not None and not isinstance(active,(HythonReturn,HythonBreak,HythonContinue)):
                    previous=self.vm.push_active_exception(self.local,active); pushed=True
                try: yield from self._run_child(arg["finally"])
                finally:
                    if pushed: self.vm.pop_active_exception(self.local,previous)
    def _run_with(self,arg):
        exits=[]; failure=None
        try:
            for manager in arg["managers"]:
                context=self.vm.run(CodeObject.from_dict(manager["code"]),self.local)
                enter_method,exit_method=self.vm.context_methods(context,False)
                entered=enter_method()
                exits.append(exit_method)
                if manager["alias"]: self.vm.assign_target(self.local,manager["alias"],entered)
            yield from self._run_child(arg["body"])
        except BaseException as caught:
            failure=caught
        self.vm.unwind_exits(exits,failure)
    async def _run_async_for(self,arg):
        iterable=self.vm.run(CodeObject.from_dict(arg["iter"]),self.local)
        broken=False
        async for item in iterable:
            self.vm.assign_target(self.local,arg["target"],item)
            child=HythonAsyncGenerator(self._run_child(arg["body"]))
            try:
                operation=("next",None)
                while True:
                    try:
                        yielded=await (child.__anext__() if operation[0]=="next" else child.asend(operation[1]) if operation[0]=="send" else child.athrow(operation[1]))
                    except StopAsyncIteration: break
                    try:
                        sent=yield yielded; operation=("next",None) if sent is None else ("send",sent)
                    except GeneratorExit:
                        await child.aclose(); raise
                    except BaseException as injected: operation=("throw",injected)
            except HythonContinue: continue
            except HythonBreak: broken=True; break
        if not broken and arg.get("else"):
            child=HythonAsyncGenerator(self._run_child(arg["else"]))
            operation=("next",None)
            while True:
                try:
                    yielded=await (child.__anext__() if operation[0]=="next" else child.asend(operation[1]) if operation[0]=="send" else child.athrow(operation[1]))
                except StopAsyncIteration: break
                try:
                    sent=yield yielded; operation=("next",None) if sent is None else ("send",sent)
                except GeneratorExit:
                    await child.aclose(); raise
                except BaseException as injected: operation=("throw",injected)
    async def _run_async_with(self,arg):
        exits=[]; failure=None
        try:
            for manager in arg["managers"]:
                context=self.vm.run(CodeObject.from_dict(manager["code"]),self.local)
                enter_method,exit_method=self.vm.context_methods(context,True)
                entered=await enter_method()
                exits.append(exit_method)
                if manager["alias"]: self.vm.assign_target(self.local,manager["alias"],entered)
            child=HythonAsyncGenerator(self._run_child(arg["body"]))
            operation=("next",None)
            while True:
                try:
                    yielded=await (child.__anext__() if operation[0]=="next" else child.asend(operation[1]) if operation[0]=="send" else child.athrow(operation[1]))
                except StopAsyncIteration: break
                try:
                    sent=yield yielded; operation=("next",None) if sent is None else ("send",sent)
                except GeneratorExit:
                    await child.aclose(); raise
                except BaseException as injected: operation=("throw",injected)
        except BaseException as caught:
            failure=caught
        await self.vm.unwind_async_exits(exits,failure)
    def close(self):
        if self.done: return None
        if self.delegate is not None and self.delegate_control is None:
            delegate=self.delegate
            try:
                close=getattr(delegate,"close",None)
                if close is not None: close()
                return None
            finally:
                self.done=True; self.stack.clear(); self.delegate=None
        try:
            result=self.throw(GeneratorExit)
        except GeneratorExit: return None
        except StopIteration as stopped: return stopped.value
        else:
            raise RuntimeError("generator ignored GeneratorExit")
        finally:
            self.done=True; self.stack.clear(); self.delegate=None
    def throw(self,exception,*args):
        error=_thrown_exception(exception,args)
        if self.done: raise error
        if self.delegate is not None and hasattr(self.delegate,"throw"):
            try:
                return self.delegate.throw(error)
            except HythonReturn as signal:
                self.done=True; self.delegate=None; self.stack.clear()
                raise StopIteration(signal.value)
            except StopIteration as stop:
                self.delegate=None
                if self.delegate_push_result: self.stack.append(stop.value)
                self.delegate_push_result=True
                return self.send(None)
            except BaseException:
                self.done=True; raise
        self.done=True; self.stack.clear(); self.delegate=None
        if isinstance(error,StopIteration): raise RuntimeError("generator raised StopIteration") from error
        raise error

class HythonCoroutine:
    """Awaitable HBC frame; resumes after each AWAIT opcode."""
    def __init__(self,vm,code,local,function_name=None,qualname=None): self.vm=vm; self.code=code; self.local=local; self.function_name=function_name or code.name; self.qualname=qualname or self.function_name; self.ip=0; self._driver=None; self._running=False; self._closed=False; self._awaiting=None; self._started=False
    @property
    def cr_code(self): return self.code
    @property
    def cr_frame(self): return None if self._closed else SimpleNamespace(f_code=self.code,f_locals=self.local,f_lasti=self.ip-1)
    @property
    def cr_running(self): return self._running
    @property
    def cr_suspended(self): return self._started and not self._running and not self._closed
    @property
    def cr_await(self):
        awaiting=self._awaiting
        seen=set()
        while isinstance(awaiting,HythonCoroutine) and id(awaiting) not in seen:
            seen.add(id(awaiting)); nested=awaiting.cr_await
            if nested is None: break
            awaiting=nested
        return awaiting
    def __getattribute__(self,name):
        if name=="__name__": return object.__getattribute__(self,"function_name")
        if name=="__qualname__": return object.__getattribute__(self,"qualname")
        return object.__getattribute__(self,name)
    def _iterator(self):
        if self._driver is None:
            if self._closed: raise RuntimeError("cannot reuse already awaited coroutine")
            self._driver=self.wrapped().__await__()
        return self._driver
    def __await__(self): return self
    def __iter__(self): return self
    def __next__(self): return self.send(None)
    def send(self,value):
        if self._closed: raise RuntimeError("cannot reuse already awaited coroutine")
        if self._running: raise ValueError("coroutine already executing")
        self._running=True
        self._started=True
        try: return self._iterator().send(value)
        except StopIteration: self._closed=True; raise
        except BaseException: self._closed=True; raise
        finally: self._running=False
    def throw(self,exception,*args):
        if self._closed: raise RuntimeError("cannot reuse already awaited coroutine")
        if self._running: raise ValueError("coroutine already executing")
        error=_thrown_exception(exception,args)
        self._running=True
        self._started=True
        try: return self._iterator().throw(error)
        except StopIteration: self._closed=True; raise
        except BaseException: self._closed=True; raise
        finally: self._running=False
    def close(self):
        if self._running: raise ValueError("coroutine already executing")
        if self._closed: return None
        self._closed=True
        if self._driver is not None: return self._driver.close()
        return None
    async def wrapped(self):
        try: return await self.execute()
        except HythonReturn as signal: return signal.value
        except BaseException as exc:
            self.vm.restore_saved_names(self.local)
            index=max(0,self.ip-1); line=self.code.lines[index] if self.code.lines and index<len(self.code.lines) else 0
            frames=getattr(exc,"__hython_frames__",None)
            if frames is None: frames=[]; setattr(exc,"__hython_frames__",frames)
            frame=(self.code.name,line,index)
            if not frames or frames[-1]!=frame:
                frames.append(frame); exc.add_note(f"하이썬 위치: {self.code.name}:{line}" if line else f"하이썬 위치: {self.code.name}")
            raise
    async def _await(self,awaitable):
        self._awaiting=awaitable
        try: return await awaitable
        finally: self._awaiting=None
    async def execute(self):
        stack=[]; ip=0; insns=self.code.instructions
        binary={"ADD":operator.add,"SUB":operator.sub,"MUL":operator.mul,"DIV":operator.truediv,"FLOORDIV":operator.floordiv,"MOD":operator.mod,"POW":operator.pow,
                "EQ":operator.eq,"NE":operator.ne,"LT":operator.lt,"LE":operator.le,"GT":operator.gt,"GE":operator.ge}
        binary.update({"IN":lambda a,b:a in b,"IS":operator.is_,"NOT_IN":lambda a,b:a not in b,"IS_NOT":operator.is_not,
                       "BIT_OR":operator.or_,"BIT_XOR":operator.xor,"BIT_AND":operator.and_,"LSHIFT":operator.lshift,"RSHIFT":operator.rshift,"MATMUL":operator.matmul})
        binary.update({"IADD":operator.iadd,"ISUB":operator.isub,"IMUL":operator.imul,"IDIV":operator.itruediv,"IFLOORDIV":operator.ifloordiv,"IMOD":operator.imod,"IPOW":operator.ipow,"IBIT_OR":operator.ior,"IBIT_XOR":operator.ixor,"IBIT_AND":operator.iand,"ILSHIFT":operator.ilshift,"IRSHIFT":operator.irshift,"IMATMUL":operator.imatmul})
        while ip<len(insns):
            self.ip=ip
            ins=insns[ip]; op=ins[0]; arg=ins[1] if len(ins)>1 else None; ip+=1; self.ip=ip
            if op=="CONST": stack.append(self.code.constants[arg])
            elif op=="LOAD":
                if arg in self.local: stack.append(self.local[arg])
                elif arg in self.local.get("$local_names",()): raise UnboundLocalError(f"local variable '{arg}' referenced before assignment")
                elif arg in self.local.get("$free_names",()):
                    closure=self.vm.nonlocal_scope(self.local,arg)
                    if arg not in closure: raise NameError(f"free variable '{arg}' is not defined in enclosing scope")
                    stack.append(closure[arg])
                elif (found:=self.vm.lookup_closure(self.local,arg))[0]: stack.append(found[1])
                elif arg in self.vm.globals: stack.append(self.vm.globals[arg])
                else: raise NameError(f"name '{arg}' is not defined")
            elif op=="STORE": self.local[arg]=stack.pop()
            elif op=="SAVE_NAME": self.vm.save_name(self.local,arg)
            elif op=="RESTORE_NAME": self.vm.restore_name(self.local,arg)
            elif op=="ANNOTATE": self.local.setdefault("__annotations__",{})[arg]=stack.pop()
            elif op=="ANNOTATE_LAZY": self.vm.register_annotation(self.local,arg)
            elif op=="SUPER": stack.append(self.vm.zero_argument_super(self.local,arg))
            elif op=="MAKE_TYPE_ALIAS": stack.append(self.vm.make_type_alias(arg,self.local))
            elif op=="MAKE_TYPE_PARAMETER": stack.append(self.vm.make_type_parameter(arg,self.local))
            elif op=="STORE_GLOBAL": self.vm.globals[arg]=stack.pop()
            elif op=="STORE_NONLOCAL":
                closure=self.vm.nonlocal_scope(self.local,arg); closure[arg]=stack.pop()
            elif op=="UNPACK":
                values=self.vm.unpack_exact(stack.pop(),arg)
                stack.extend(reversed(values))
            elif op=="UNPACK_EX":
                before=arg>>16; after=arg&0xFFFF
                stack.extend(reversed(self.vm.unpack_extended(stack.pop(),before,after)))
            elif op=="DELETE":
                if arg not in self.local: raise self.vm.missing_delete_error(self.local,arg)
                del self.local[arg]
            elif op=="DELETE_GLOBAL":
                if arg not in self.vm.globals: raise NameError(f"name '{arg}' is not defined")
                del self.vm.globals[arg]
            elif op=="DELETE_NONLOCAL":
                closure=self.vm.nonlocal_scope(self.local,arg)
                if arg not in closure: raise NameError(f"free variable '{arg}' is not defined in enclosing scope")
                del closure[arg]
            elif op=="DELETE_ITEM": index=stack.pop(); del stack.pop()[index]
            elif op=="DELETE_ATTR": delattr(stack.pop(),arg)
            elif op=="POP": stack.pop()
            elif op=="DUP": stack.append(stack[-1])
            elif op=="DUP2": stack.extend(stack[-2:])
            elif op in binary: b=stack.pop(); a=stack.pop(); stack.append(binary[op](a,b))
            elif op in ("NEG","POS","NOT","INVERT"): stack.append({"NEG":operator.neg,"POS":operator.pos,"NOT":operator.not_,"INVERT":operator.invert}[op](stack.pop()))
            elif op=="JUMP": ip=arg
            elif op=="JUMP_FALSE":
                if not stack.pop(): ip=arg
            elif op=="JUMP_IF_FALSE_OR_POP":
                if not stack[-1]: ip=arg
                else: stack.pop()
            elif op=="JUMP_IF_TRUE_OR_POP":
                if stack[-1]: ip=arg
                else: stack.pop()
            elif op=="ITER": stack.append(iter(stack.pop()))
            elif op=="FOR_ITER":
                try: stack.append(next(stack[-1]))
                except StopIteration: stack.pop(); ip=arg
            elif op in ("BUILD_LIST","BUILD_TUPLE","BUILD_SET"):
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(list(values) if op=="BUILD_LIST" else tuple(values) if op=="BUILD_TUPLE" else set(values))
            elif op=="BUILD_DICT":
                values=stack[-arg*2:] if arg else []
                if arg: del stack[-arg*2:]
                stack.append(dict(zip(values[::2],values[1::2])))
            elif op=="BUILD_UNPACK":
                count=len(arg["starred"]); values=stack[-count:] if count else []
                if count: del stack[-count:]
                merged=[]
                for value,starred in zip(values,arg["starred"]): merged.extend(value) if starred else merged.append(value)
                stack.append(tuple(merged) if arg["kind"]=="tuple" else set(merged) if arg["kind"]=="set" else merged)
            elif op=="BUILD_DICT_UNPACK":
                count=sum(2 if item=="pair" else 1 for item in arg); values=stack[-count:] if count else []
                if count: del stack[-count:]
                result={}; index=0
                for item in arg:
                    if item=="pair": result[values[index]]=values[index+1]; index+=2
                    else: result.update(values[index]); index+=1
                stack.append(result)
            elif op=="COLLECTION_BEGIN": stack.append(self.vm.collection_builder(arg))
            elif op=="COLLECTION_ADD":
                value=stack.pop(); key=stack.pop() if arg=="pair" else None
                self.vm.add_collection_item(stack[-1],arg,value,key)
            elif op=="COLLECTION_READY": stack.append(self.vm.finish_collection(stack.pop()))
            elif op=="BUILD_SLICE":
                step=stack.pop(); stop=stack.pop(); start=stack.pop(); stack.append(slice(start,stop,step))
            elif op=="GET_ITEM": index=stack.pop(); stack.append(stack.pop()[index])
            elif op=="SET_ITEM": value=stack.pop(); index=stack.pop(); stack.pop()[index]=value
            elif op=="GET_ATTR": stack.append(getattr(stack.pop(),arg))
            elif op=="SET_ATTR":
                value=stack.pop(); target=stack.pop(); setattr(target,arg,value)
            elif op=="IMPORT": stack.append(self.vm.import_module(arg,self.code))
            elif op=="IMPORT_FROM": stack.append(self.vm.import_from(arg["module"],arg["name"],self.code))
            elif op=="IMPORT_STAR": self.vm.import_star(self.local,stack.pop())
            elif op=="FORMAT": stack.append(str(stack.pop()))
            elif op=="FORMAT_VALUE":
                spec=stack.pop() if arg["has_spec"] else ""; value=stack.pop()
                if arg["conversion"]=="r": value=repr(value)
                elif arg["conversion"]=="s": value=str(value)
                elif arg["conversion"]=="a": value=ascii(value)
                stack.append(format(value,spec))
            elif op=="BUILD_STRING":
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append("".join(values))
            elif op=="MAKE_INTERPOLATION":
                spec=stack.pop(); conversion=stack.pop(); expression=stack.pop(); value=stack.pop(); stack.append(Interpolation(value,expression,conversion,spec))
            elif op=="BUILD_TEMPLATE":
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(Template(*values))
            elif op=="ASSERT":
                message=stack.pop(); condition=stack.pop()
                if not condition: raise AssertionError(message) if message is not None else AssertionError()
            elif op=="MATCH_PATTERN":
                bindings={}; matched=self.vm.match_pattern(stack.pop(),arg,bindings,self.local)
                if matched: self.vm.apply_pattern_bindings(self.local,bindings)
                stack.append(matched)
            elif op=="CHAIN_COMPARE":
                operands=arg["operands"]; operators=arg["operators"]; left=await HythonCoroutine(self.vm,CodeObject.from_dict(operands[0]),self.local).execute(); result=True
                for index,(operator_name,payload) in enumerate(zip(operators,operands[1:])):
                    right=await HythonCoroutine(self.vm,CodeObject.from_dict(payload),self.local).execute()
                    result=self.vm.compare_values(operator_name,left,right)
                    if index<len(operators)-1 and not result: break
                    left=right
                stack.append(result)
            elif op=="CALL":
                args=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(self.vm.call_value(stack.pop(),args,{},self.local))
            elif op=="CALL_EX":
                values=stack[-len(arg):] if arg else []
                if arg: del stack[-len(arg):]
                function=stack.pop(); positional,keywords=self.vm.expand_call_arguments(arg,values)
                stack.append(self.vm.call_value(function,positional,keywords,self.local))
            elif op=="CALL_BEGIN": stack.append(CallArguments([],{}))
            elif op=="CALL_ARG": self.vm.add_call_argument(stack[-2],arg,stack.pop())
            elif op=="CALL_READY":
                arguments=stack.pop(); function=stack.pop()
                stack.append(self.vm.call_value(function,arguments.positional,arguments.keywords,self.local))
            elif op=="CLASS_BEGIN": stack.append(CallArguments([],{}))
            elif op=="CLASS_ARG": self.vm.add_class_argument(stack[-2],arg,stack.pop())
            elif op=="MAKE_FUNCTION":
                stack.append(self.vm.create_function(arg,self.local,stack))
            elif op=="MAKE_CLASS":
                stack.append(self.vm.create_class(arg,self.local,stack))
            elif op=="AWAIT":
                awaitable=stack.pop(); self.vm.inherit_active_exception(awaitable,self.local); stack.append(await self._await(awaitable))
            elif op=="RAISE": raise stack.pop()
            elif op=="RAISE_FROM":
                cause=stack.pop(); error=stack.pop(); raise error from cause
            elif op=="RERAISE":
                self.vm.reraise(self.local)
            elif op=="TRY":
                control=None
                try:
                    await HythonCoroutine(self.vm,CodeObject.from_dict(arg["body"]),self.local).execute()
                except (HythonBreak,HythonContinue) as signal: control=signal
                except HythonReturn:
                    raise
                except BaseException as exc:
                    if arg["handlers"] and arg["handlers"][0].get("star",False):
                        original=exc if isinstance(exc,BaseExceptionGroup) else BaseExceptionGroup("",[exc]); remaining=original; raised=[]; reraised=[]
                        for handler in arg["handlers"]:
                            expected=self.vm.run(CodeObject.from_dict(handler["type"]),self.local)
                            matched,remaining=remaining.split(expected)
                            if matched is None: continue
                            if handler["alias"]: self.vm.assign_name(self.local,handler["alias"],matched,handler.get("alias_scope","local"))
                            previous=self.vm.push_active_exception(self.local,matched)
                            try: await HythonCoroutine(self.vm,CodeObject.from_dict(handler["code"]),self.local).execute()
                            except BaseException as failure:
                                (reraised if failure is matched else raised).append(failure)
                            finally:
                                self.vm.pop_active_exception(self.local,previous)
                                if handler["alias"]: self.vm.delete_name(self.local,handler["alias"],handler.get("alias_scope","local"))
                        failure=_merge_except_star(original,reraised,raised,remaining)
                        if failure is not None: raise failure
                        continue
                    handled=False
                    for handler in arg["handlers"]:
                        expected=self.vm.run(CodeObject.from_dict(handler["type"]),self.local) if handler["type"] else BaseException
                        if isinstance(exc,expected):
                            if handler["alias"]: self.vm.assign_name(self.local,handler["alias"],exc,handler.get("alias_scope","local"))
                            previous=self.vm.push_active_exception(self.local,exc)
                            try: await HythonCoroutine(self.vm,CodeObject.from_dict(handler["code"]),self.local).execute()
                            finally:
                                self.vm.pop_active_exception(self.local,previous)
                                if handler["alias"]: self.vm.delete_name(self.local,handler["alias"],handler.get("alias_scope","local"))
                            handled=True; break
                    if not handled: raise
                else:
                    if arg["else"]: await HythonCoroutine(self.vm,CodeObject.from_dict(arg["else"]),self.local).execute()
                finally:
                    if arg["finally"]:
                        active=sys.exception(); previous=_MISSING; pushed=False
                        if active is not None and not isinstance(active,(HythonReturn,HythonBreak,HythonContinue)):
                            previous=self.vm.push_active_exception(self.local,active); pushed=True
                        try: await HythonCoroutine(self.vm,CodeObject.from_dict(arg["finally"]),self.local).execute()
                        finally:
                            if pushed: self.vm.pop_active_exception(self.local,previous)
                if isinstance(control,HythonBreak): ip=arg["break_target"]
                elif isinstance(control,HythonContinue): ip=arg["continue_target"]
            elif op=="WITH":
                exits=[]; failure=None
                try:
                    for manager in arg["managers"]:
                        context=self.vm.run(CodeObject.from_dict(manager["code"]),self.local)
                        enter_method,exit_method=self.vm.context_methods(context,False)
                        entered=enter_method(); exits.append(exit_method)
                        if manager["alias"]: self.vm.assign_target(self.local,manager["alias"],entered)
                    await HythonCoroutine(self.vm,CodeObject.from_dict(arg["body"]),self.local).execute()
                except BaseException as caught:
                    failure=caught
                try: self.vm.unwind_exits(exits,failure)
                except HythonBreak: ip=arg["break_target"]
                except HythonContinue: ip=arg["continue_target"]
            elif op=="COMPREHENSION":
                if arg.get("async",any(clause.get("async",False) for clause in arg["clauses"])):
                    if arg["kind"]=="generatorexpr": stack.append(await self.vm.prepare_async_generator_expression(arg,self.local,self._await))
                    else: stack.append(await self.vm.run_async_comprehension(arg,self.local,self._await))
                    continue
                if arg["kind"]=="generatorexpr": stack.append(self.vm.generator_expression(arg,self.local)); continue
                scope=ComprehensionScope(self.vm.comprehension_parent(self.local),arg.get("bindings",())); result={} if arg["kind"]=="dictcomp" else set() if arg["kind"]=="setcomp" else []
                def collect(index):
                    if index<len(arg["clauses"]):
                        clause=arg["clauses"][index]
                        for item in self.vm.run(CodeObject.from_dict(clause["iter"]),scope):
                            self.vm.assign_target(scope,clause["target"],item)
                            if all(self.vm.run(CodeObject.from_dict(test),scope) for test in clause["filters"]): collect(index+1)
                        return
                    if arg["kind"]=="dictcomp": result[self.vm.run(CodeObject.from_dict(arg["key"]),scope)]=self.vm.run(CodeObject.from_dict(arg["value"]),scope)
                    else:
                        value=self.vm.run(CodeObject.from_dict(arg["element"]),scope)
                        result.add(value) if arg["kind"]=="setcomp" else result.append(value)
                collect(0); self.vm.commit_comprehension_bindings(arg,scope,self.local); stack.append(result)
            elif op=="ASYNC_FOR":
                iterable=self.vm.run(CodeObject.from_dict(arg["iter"]),self.local)
                iterator=builtins.aiter(iterable)
                broken=False
                while True:
                    try: item=await self._await(builtins.anext(iterator))
                    except StopAsyncIteration: break
                    self.vm.assign_target(self.local,arg["target"],item)
                    try: await HythonCoroutine(self.vm,CodeObject.from_dict(arg["body"]),self.local).execute()
                    except HythonContinue: continue
                    except HythonBreak: broken=True; break
                if not broken and arg.get("else"): await HythonCoroutine(self.vm,CodeObject.from_dict(arg["else"]),self.local).execute()
            elif op=="ASYNC_WITH":
                exits=[]; failure=None
                try:
                    for manager in arg["managers"]:
                        context=self.vm.run(CodeObject.from_dict(manager["code"]),self.local)
                        enter_method,exit_method=self.vm.context_methods(context,True)
                        entered=await self._await(enter_method())
                        exits.append(exit_method)
                        if manager["alias"]: self.vm.assign_target(self.local,manager["alias"],entered)
                    await HythonCoroutine(self.vm,CodeObject.from_dict(arg["body"]),self.local).execute()
                except BaseException as caught:
                    failure=caught
                try: await self.vm.unwind_async_exits(exits,failure,self._await)
                except HythonBreak: ip=arg["break_target"]
                except HythonContinue: ip=arg["continue_target"]
            elif op=="RETURN": return stack.pop()
            elif op=="SIGNAL_RETURN": raise HythonReturn(stack.pop())
            elif op=="SIGNAL_BREAK": raise HythonBreak()
            elif op=="SIGNAL_CONTINUE": raise HythonContinue()
            elif op=="NOP": pass
            else: raise VMError(f"코루틴에서 아직 지원하지 않는 HBC 명령어: {op}")
        return None

class HythonAsyncGenerator:
    """Asynchronous iterator facade over a resumable HBC generator frame."""
    def __init__(self,generator): self.generator=generator; self.async_delegate=None; self._awaiting=None; self._running=False; self._closed=False
    @property
    def ag_code(self): return self.generator.code
    @property
    def ag_frame(self): return self.generator.gi_frame
    @property
    def ag_running(self): return self._running or self.generator.gi_running
    @property
    def ag_suspended(self): return self.generator.gi_suspended and not self.ag_running and not self._closed
    @property
    def ag_await(self): return self._awaiting if self._awaiting is not None else self.async_delegate
    def __getattribute__(self,name):
        if name in ("__name__","__qualname__"): return getattr(object.__getattribute__(self,"generator"),name)
        return object.__getattribute__(self,name)
    def __aiter__(self): return self
    async def _await(self,awaitable):
        self._awaiting=awaitable
        try: return await awaitable
        finally: self._awaiting=None
    async def _drive(self,value=None):
        while True:
            if self.async_delegate is not None:
                try: return await (builtins.anext(self.async_delegate) if value is None else self.async_delegate.asend(value))
                except StopAsyncIteration: self.async_delegate=None; value=None; continue
            try: return self.generator.send(value)
            except HythonAwait as signal:
                value=await self._await(signal.awaitable)
            except HythonAsyncDelegate as signal:
                self.async_delegate=builtins.aiter(signal.iterator); value=None
            except StopIteration: raise _AsyncGeneratorReturn from None
    async def __anext__(self):
        if self._closed: raise StopAsyncIteration
        if self._running: raise RuntimeError("anext(): asynchronous generator is already running")
        self._running=True
        try: return await self._drive(None)
        except _AsyncGeneratorReturn: raise StopAsyncIteration from None
        except StopAsyncIteration as exc: raise RuntimeError("async generator raised StopAsyncIteration") from exc
        finally: self._running=False
    async def asend(self,value):
        if self._closed: raise StopAsyncIteration
        if self._running: raise RuntimeError("anext(): asynchronous generator is already running")
        self._running=True
        try: return await self._drive(value)
        except _AsyncGeneratorReturn: raise StopAsyncIteration from None
        except StopAsyncIteration as exc: raise RuntimeError("async generator raised StopAsyncIteration") from exc
        finally: self._running=False
    async def aclose(self):
        if self._closed: return None
        try:
            yielded=await self.athrow(GeneratorExit)
        except (GeneratorExit,StopAsyncIteration):
            self._closed=True; return None
        self._closed=True
        raise RuntimeError("비동기 제너레이터가 GeneratorExit를 무시했습니다.")
    async def athrow(self,exception,*args):
        if self._closed: raise StopAsyncIteration
        if self._running: raise RuntimeError("athrow(): asynchronous generator is already running")
        self._running=True
        try:
            if self.async_delegate is not None:
                try: return await self.async_delegate.athrow(exception,*args)
                except StopAsyncIteration: self.async_delegate=None; return await self._drive(None)
            try:
                value=self.generator.throw(exception,*args)
                return value
            except HythonAwait as signal:
                return await self._drive(await self._await(signal.awaitable))
            except StopIteration: raise _AsyncGeneratorReturn from None
            except StopAsyncIteration as exc: raise RuntimeError("async generator raised StopAsyncIteration") from exc
        except _AsyncGeneratorReturn: raise StopAsyncIteration from None
        finally: self._running=False

class VM:
    def __init__(self, module_paths: list[Path] | None = None, modules: dict | None = None,
                 module_files: dict | None = None, instruction_hook=None):
        self.globals = {name:value for name,value in vars(builtins).items() if not name.startswith("_")}
        self.globals["asyncio_run"]=asyncio.run
        self.globals["__name__"]="__main__"
        self.module_paths = module_paths or [Path.cwd()]
        self.modules = modules if modules is not None else {}
        self.module_files = module_files if module_files is not None else {}
        self._last_instruction = {}
        self.instruction_hook = instruction_hook

    @staticmethod
    def save_name(scope,name):
        scope.setdefault("$saved_names",{}).setdefault(name,[]).append((name in scope,scope.get(name)))

    @staticmethod
    def restore_name(scope,name):
        saved=scope["$saved_names"]; existed,value=saved[name].pop()
        if existed: scope[name]=value
        else: scope.pop(name,None)
        if not saved[name]: del saved[name]
        if not saved: del scope["$saved_names"]

    @classmethod
    def restore_saved_names(cls,scope):
        saved=scope.get("$saved_names",{})
        for name in list(saved):
            while name in saved: cls.restore_name(scope,name)
        scope.pop("$type_parameter_scope",None)

    @staticmethod
    def push_active_exception(scope,exception):
        previous=scope.get("$active_exception",_MISSING)
        scope["$active_exception"]=exception
        return previous

    @staticmethod
    def pop_active_exception(scope,previous):
        if previous is _MISSING: scope.pop("$active_exception",None)
        else: scope["$active_exception"]=previous

    @staticmethod
    def reraise(scope):
        exception=scope.get("$active_exception",_MISSING)
        if exception is _MISSING: raise RuntimeError("No active exception to reraise")
        if sys.exception() is exception: raise
        raise exception

    @staticmethod
    def inherit_active_exception(awaitable,scope):
        if "$active_exception" not in scope: return
        target=awaitable.generator if isinstance(awaitable,HythonAsyncGenerator) else awaitable
        if isinstance(target,(HythonCoroutine,HythonGenerator)) and "$active_exception" not in target.local:
            target.local["$active_exception"]=scope["$active_exception"]
            target.local["$inherited_active_exception"]=scope["$active_exception"]

    @staticmethod
    def zero_argument_super(scope,parameter):
        if not parameter: raise RuntimeError("super(): no arguments")
        if not scope.get("$has_class_cell",False): raise RuntimeError("super(): __class__ cell not found")
        if parameter not in scope: raise RuntimeError("super(): arg[0] deleted")
        return super(scope["__class__"],scope[parameter])

    @staticmethod
    def unwind_exits(exits,active=None):
        control=active if isinstance(active,(HythonReturn,HythonBreak,HythonContinue)) else None
        pending=None if control is not None else active
        for exit_method in reversed(exits):
            previous=pending
            try:
                suppressed=exit_method(type(pending),pending,pending.__traceback__) if pending is not None else exit_method(None,None,None)
                if pending is not None and suppressed: pending=None
            except BaseException as failure:
                if failure is not previous: failure.__context__=previous
                pending=failure; control=None
        if pending is not None: raise pending
        if control is not None: raise control

    @staticmethod
    def lookup_special(value,name):
        value_type=type(value)
        for owner in value_type.__mro__:
            if name not in owner.__dict__: continue
            descriptor=owner.__dict__[name]
            getter=getattr(type(descriptor),"__get__",None)
            return getter(descriptor,value,value_type) if getter is not None else descriptor
        raise AttributeError(f"'{value_type.__name__}' object has no attribute '{name}'")

    @classmethod
    def context_methods(cls,context,is_async):
        enter_name="__aenter__" if is_async else "__enter__"
        exit_name="__aexit__" if is_async else "__exit__"
        try: enter_method=cls.lookup_special(context,enter_name)
        except AttributeError as exc:
            protocol="asynchronous context manager" if is_async else "context manager"
            raise TypeError(f"'{type(context).__name__}' object does not support the {protocol} protocol") from exc
        try: exit_method=cls.lookup_special(context,exit_name)
        except AttributeError as exc:
            protocol="asynchronous context manager" if is_async else "context manager"
            raise TypeError(f"'{type(context).__name__}' object does not support the {protocol} protocol (missed {exit_name} method)") from exc
        return enter_method,exit_method

    @staticmethod
    async def unwind_async_exits(exits,active=None,waiter=None):
        control=active if isinstance(active,(HythonReturn,HythonBreak,HythonContinue)) else None
        pending=None if control is not None else active
        for exit_method in reversed(exits):
            previous=pending
            try:
                awaitable=exit_method(type(pending),pending,pending.__traceback__) if pending is not None else exit_method(None,None,None)
                suppressed=await (waiter(awaitable) if waiter is not None else awaitable)
                if pending is not None and suppressed: pending=None
            except BaseException as failure:
                if failure is not previous: failure.__context__=previous
                pending=failure; control=None
        if pending is not None: raise pending
        if control is not None: raise control

    def import_module(self, name: str, parent_code: CodeObject):
        source_path=Path(parent_code.name)
        relative=name.startswith("."); clean=name.lstrip("."); depth=len(name)-len(clean)
        if relative:
            package=self.parent_package(source_path)
            if not package: raise ImportError("attempted relative import with no known parent package")
            parts=package.split(".")
            if depth>len(parts): raise ImportError("attempted relative import beyond top-level package")
            base=parts[:len(parts)-depth+1]
            name=".".join([*base,*([clean] if clean else [])]); clean=name; relative=False
        if name in self.modules:
            module = self.modules[name]
            if module is None: raise VMError(f"순환 모듈 import: {name}")
            return module
        if not clean: raise VMError(f"모듈 이름이 필요합니다: {name}")
        parent=None
        if "." in clean:
            parent_name=clean.rsplit(".",1)[0]
            parent=self.import_module(parent_name,parent_code)
        module_path=Path(*clean.split(".")); roots=[source_path.parent]
        if relative:
            for _ in range(max(0,depth-1)): roots=[root.parent for root in roots]
        else: roots.extend(self.module_paths)
        candidates=[]
        for root in roots: candidates.extend((root/module_path.with_suffix(".hbc"),root/module_path/"__init__.hbc"))
        path=next((candidate for candidate in candidates if candidate.is_file()),None)
        if path is None:
            namespace_path=next((root/module_path for root in roots if (root/module_path).is_dir()),None)
            native_namespace=namespace_path is not None and any(namespace_path.rglob("*.hbc"))
            if not relative and not native_namespace:
                try: module=importlib.import_module(clean)
                except ModuleNotFoundError as exc:
                    if exc.name not in (clean,clean.split(".")[0]): raise
                else:
                    self.modules[name]=module
                    return module
            if namespace_path is None or not native_namespace: raise ModuleNotFoundError(f"HBC 또는 Python 모듈을 찾을 수 없습니다: {name}",name=name)
            cache_key=str(namespace_path.resolve())
            module=self.module_files.get(cache_key)
            if module is None:
                spec=importlib.machinery.ModuleSpec(clean,loader=None,is_package=True)
                spec.submodule_search_locations=[str(namespace_path.resolve())]
                module=HythonModule(clean,__package__=clean,__file__=None,__loader__=None,
                                    __spec__=spec,__cached__=None,__path__=[str(namespace_path.resolve())])
                self.module_files[cache_key]=module
            self.modules[name]=module
            return module
        cache_key=str(path.resolve())
        if cache_key in self.module_files:
            module=self.module_files[cache_key]
            if module is None: raise VMError(f"순환 모듈 import: {name}")
            self.modules[name]=module
            return module
        child=VM([path.parent,*self.module_paths],self.modules,self.module_files)
        initial=dict(child.globals)
        module_name=clean
        is_package=path.name=="__init__.hbc"
        spec=importlib.machinery.ModuleSpec(module_name,loader=None,origin=str(path.resolve()),is_package=is_package)
        if is_package: spec.submodule_search_locations=[str(path.parent.resolve())]
        child.globals.update({
            "__name__":module_name,
            "__file__":str(path.resolve()),
            "__package__":module_name if is_package else module_name.rpartition(".")[0],
            "__loader__":None,"__spec__":spec,"__cached__":str(path.resolve()),
        })
        module=HythonModule(__name__=module_name,__file__=str(path.resolve()),
                            __package__=module_name if is_package else module_name.rpartition(".")[0],
                            __loader__=None,__spec__=spec,__cached__=str(path.resolve()),
                            **({"__path__":[str(path.parent.resolve())]} if is_package else {}),
                            _hython_scope=child.globals)
        self.modules[name]=module; self.module_files[cache_key]=module
        try:
            child.run(read_hbc(path))
        except BaseException:
            self.modules.pop(name,None); self.module_files.pop(cache_key,None)
            raise
        namespace={key:value for key,value in child.globals.items()
                   if key not in initial or value is not initial[key]}
        vars(module).update(namespace); vars(module).pop("_hython_scope",None)
        module_annotations=vars(module).get("__annotations__")
        if isinstance(module_annotations,LazyAnnotations): module_annotations.owner=module; module_annotations.scope=vars(module)
        if "." in clean:
            _,attribute=clean.rsplit(".",1)
            setattr(parent,attribute,module)
        return module

    def parent_package(self,source_path:Path):
        source=source_path.resolve()
        for module in self.modules.values():
            filename=getattr(module,"__file__",None) if module is not None else None
            if not filename: continue
            loaded=Path(filename).resolve()
            if loaded.parent==source.parent and (loaded.stem==source.stem or loaded.name=="__init__.hbc"):
                return getattr(module,"__package__","")
        for root in self.module_paths:
            try: relative=source.parent.relative_to(Path(root).resolve())
            except ValueError: continue
            if relative.parts: return ".".join(relative.parts)
        return ""

    def register_annotation(self,scope,arg):
        annotations=scope.get("__annotations__")
        if not isinstance(annotations,LazyAnnotations):
            annotations=LazyAnnotations(self,scope,annotations if isinstance(annotations,dict) else None)
            scope["__annotations__"]=annotations
            scope["__annotate__"]=staticmethod(annotations.evaluate) if "$class_outer" in scope else annotations.evaluate
        annotations.add(arg["name"],arg["code"],arg.get("text",""))

    @staticmethod
    def import_star(scope: dict, module) -> None:
        namespace=vars(module)
        names=getattr(module,"__all__",None)
        if names is None: names=[name for name in namespace if not name.startswith("_")]
        for name in names:
            if not isinstance(name,str): raise TypeError("__all__의 항목은 문자열이어야 합니다.")
            scope[name]=getattr(module,name)

    def import_from(self,module_name:str,name:str,parent_code:CodeObject):
        if not module_name.lstrip("."):
            return self.import_module(f"{module_name}{name}",parent_code)
        module=self.import_module(module_name,parent_code)
        try: return getattr(module,name)
        except AttributeError:
            separator="" if module_name.endswith(".") else "."
            try: return self.import_module(f"{module_name}{separator}{name}",parent_code)
            except ModuleNotFoundError as exc:
                raise ImportError(f"{module_name}에서 {name} 이름을 가져올 수 없습니다.") from exc

    def bind(self,function:Function,args,kwargs):
        signature=function.signature or {"positional":function.code.parameters,"positional_only":[],"keyword_only":[],"vararg":None,"kwarg":None}
        positional=signature["positional"]; keyword_only=signature["keyword_only"]
        if len(args)>len(positional) and not signature["vararg"]: raise TypeError(f"{function.code.name}: 위치 인자가 너무 많습니다.")
        bound=dict(zip(positional,args)); defaults=function.defaults or {}; extras={}
        if signature["vararg"]: bound[signature["vararg"]]=tuple(args[len(positional):])
        for name,value in kwargs.items():
            if name in signature.get("positional_only",[]):
                if signature["kwarg"]: extras[name]=value; continue
                raise TypeError(f"{function.code.name}: 위치 전용 인자 '{name}'은 키워드로 전달할 수 없습니다.")
            if name not in positional and name not in keyword_only:
                if signature["kwarg"]: extras[name]=value; continue
                raise TypeError(f"{function.code.name}: 알 수 없는 키워드 인자 '{name}'")
            if name in bound: raise TypeError(f"{function.code.name}: 인자 '{name}'이 중복되었습니다.")
            bound[name]=value
        missing=[name for name in [*positional,*keyword_only] if name not in bound and name not in defaults]
        if missing: raise TypeError(f"{function.code.name}: 필수 인자 누락: {', '.join(missing)}")
        for name in [*positional,*keyword_only]:
            if name not in bound: bound[name]=defaults[name]
        if signature["kwarg"]: bound[signature["kwarg"]]=extras
        return bound

    @staticmethod
    def expand_call_arguments(descriptors,values):
        positional=[]; keywords={}
        for descriptor,item in zip(descriptors,values):
            if descriptor[0]=="positional": positional.append(item)
            elif descriptor[0]=="star": positional.extend(item)
            elif descriptor[0]=="kwstar":
                try: names=item.keys()
                except AttributeError: raise TypeError("** 뒤의 인자는 매핑이어야 합니다.") from None
                for name in names:
                    if name in keywords: raise TypeError(f"키워드 인자 중복: {name}")
                    keywords[name]=item[name]
            else:
                name=descriptor[1]
                if name in keywords: raise TypeError(f"키워드 인자 중복: {name}")
                keywords[name]=item
        return positional,keywords

    @staticmethod
    def add_call_argument(arguments,descriptor,value):
        kind,name=descriptor
        if kind=="positional": arguments.positional.append(value); return
        if kind=="star":
            try: iterator=iter(value)
            except TypeError: raise TypeError(f"argument after * must be an iterable, not {type(value).__name__}") from None
            arguments.positional.extend(iterator)
            return
        if kind=="keyword":
            if name in arguments.keywords: raise TypeError(f"키워드 인자 중복: {name}")
            arguments.keywords[name]=value; return
        try: names=value.keys()
        except AttributeError: raise TypeError(f"argument after ** must be a mapping, not {type(value).__name__}") from None
        for key in names:
            if key in arguments.keywords: raise TypeError(f"키워드 인자 중복: {key}")
            arguments.keywords[key]=value[key]

    @staticmethod
    def add_class_argument(arguments,descriptor,value):
        kind,name=descriptor
        if kind!="kwstar":
            VM.add_call_argument(arguments,["positional" if kind=="base" else kind,name],value); return
        try: names=value.keys()
        except AttributeError: raise TypeError(f"argument after ** must be a mapping, not {type(value).__name__}") from None
        for key in names:
            if not isinstance(key,str): raise TypeError("keywords must be strings")
            if key in arguments.keywords: raise TypeError(f"클래스 키워드 인자 중복: {key}")
            arguments.keywords[key]=value[key]

    @staticmethod
    def collection_builder(kind):
        return CollectionBuilder(kind,{} if kind=="dict" else set() if kind=="set" else [])

    @staticmethod
    def add_collection_item(builder,kind,value,key=None):
        if kind=="pair": builder.value[key]=value; return
        if kind=="unpack":
            try: keys=value.keys()
            except AttributeError: raise TypeError(f"'{type(value).__name__}' object is not a mapping") from None
            for item in keys: builder.value[item]=value[item]
            return
        if builder.kind=="set":
            if kind=="star": builder.value.update(value)
            else: builder.value.add(value)
        elif kind=="star": builder.value.extend(value)
        else: builder.value.append(value)

    @staticmethod
    def finish_collection(builder):
        return tuple(builder.value) if builder.kind=="tuple" else builder.value

    @staticmethod
    def pop_class_arguments(stack,arg):
        if arg.get("incremental_arguments"):
            arguments=stack.pop(); type_names=arg.get("type_params",[])
            type_values=stack[-len(type_names):] if type_names else []
            if type_names: del stack[-len(type_names):]
            return arguments.positional,arguments.keywords,type_names,type_values
        descriptors=arg.get("class_arguments")
        if descriptors:
            values=stack[-len(descriptors):]
            del stack[-len(descriptors):]
            bases=[]; keywords={}
            for (kind,name),value in zip(descriptors,values):
                if kind=="base": bases.append(value)
                elif kind=="star": bases.extend(value)
                elif kind=="kwstar":
                    try: names=value.keys()
                    except AttributeError: raise TypeError(f"argument after ** must be a mapping, not {type(value).__name__}") from None
                    for key in names:
                        if not isinstance(key,str): raise TypeError("keywords must be strings")
                        if key in keywords: raise TypeError(f"클래스 키워드 인자 중복: {key}")
                        keywords[key]=value[key]
                else:
                    if name in keywords: raise TypeError(f"클래스 키워드 인자 중복: {name}")
                    keywords[name]=value
            type_names=arg.get("type_params",[]); type_values=stack[-len(type_names):] if type_names else []
            if type_names: del stack[-len(type_names):]
            return bases,keywords,type_names,type_values
        keyword_names=arg.get("keywords",[]); keyword_values=stack[-len(keyword_names):] if keyword_names else []
        if keyword_names: del stack[-len(keyword_names):]
        keywords={}
        for name,value in zip(keyword_names,keyword_values):
            if name is None:
                for key,item in value.items():
                    if key in keywords: raise TypeError(f"클래스 키워드 인자 중복: {key}")
                    keywords[key]=item
            else:
                if name in keywords: raise TypeError(f"클래스 키워드 인자 중복: {name}")
                keywords[name]=value
        count=arg["bases"]; values=stack[-count:] if count else []
        if count: del stack[-count:]
        bases=[]
        for starred,value in zip(arg.get("base_starred",[False]*count),values): bases.extend(value) if starred else bases.append(value)
        type_names=arg.get("type_params",[]); type_values=stack[-len(type_names):] if type_names else []
        if type_names: del stack[-len(type_names):]
        return bases,keywords,type_names,type_values

    @staticmethod
    def mapping_pop(mapping,key,default=None):
        try: value=mapping[key]
        except KeyError: return default
        del mapping[key]
        return value

    def create_class(self,arg,scope,stack):
        bases,keywords,type_names,type_values=self.pop_class_arguments(stack,arg)
        original_bases=tuple(bases); bases=types.resolve_bases(original_bases)
        class_code=CodeObject.from_dict(arg["code"])
        metaclass,namespace,keywords=types.prepare_class(class_code.name,bases,keywords)
        for name,value in zip(type_names,type_values): namespace[name]=value
        class_qualname=self.qualified_name(scope,arg.get("name",class_code.name))
        namespace["__module__"]=scope.get("__name__",self.globals.get("__name__")); namespace["__qualname__"]=class_qualname; namespace["__doc__"]=arg.get("doc")
        if arg.get("firstlineno") is not None: namespace["__firstlineno__"]=arg["firstlineno"]
        namespace["$class_outer"]=scope; namespace["$class_local_names"]=set(arg.get("local_names",[])); namespace["$free_names"]=set(arg.get("free_names",[])); namespace["$qualname_prefix"]=class_qualname; namespace["$class_functions"]=[]; namespace["$class_type_parameters"]=dict(zip(type_names,type_values))
        class_cell=(lambda value: lambda: value)(None).__closure__[0]; del class_cell.cell_contents
        namespace["$class_cell"]=class_cell; namespace["$class_cell_needed"]=False
        if bases!=original_bases: namespace["__orig_bases__"]=original_bases
        self.run(class_code,namespace)
        class_cell_needed=self.mapping_pop(namespace,"$class_cell_needed"); self.mapping_pop(namespace,"$class_cell")
        class_functions=self.mapping_pop(namespace,"$class_functions",[]); self.mapping_pop(namespace,"$class_type_parameters")
        self.mapping_pop(namespace,"__return__"); self.mapping_pop(namespace,"$class_outer"); self.mapping_pop(namespace,"$class_local_names"); self.mapping_pop(namespace,"$free_names"); self.mapping_pop(namespace,"$qualname_prefix")
        namespace["__type_params__"]=tuple(type_values)
        namespace["__static_attributes__"]=tuple(arg.get("static_attributes",()))
        lazy_annotations=self.mapping_pop(namespace,"__annotations__")
        if isinstance(lazy_annotations,LazyAnnotations): lazy_annotations.scope=dict(namespace)
        for name,value in zip(type_names,type_values):
            try: current=namespace[name]
            except KeyError: continue
            if current is value: del namespace[name]
        if class_cell_needed: namespace["__classcell__"]=class_cell
        created=metaclass(class_code.name,bases,namespace,**keywords)
        if isinstance(lazy_annotations,LazyAnnotations): lazy_annotations.owner=created; lazy_annotations.scope=ClassAnnotationScope(created,scope.get("$class_outer",scope),dict(zip(type_names,type_values)))
        if isinstance(created,type):
            self.bind_class_functions(namespace,created)
            for function in class_functions: self.bind_class_function(function,created)
        return created

    def create_function(self,arg,scope,stack):
        type_names=arg.get("type_params",[]); type_values=stack[-len(type_names):] if type_names else []
        if type_names: del stack[-len(type_names):]
        annotation_names=arg.get("annotations",[]); annotation_values=stack[-len(annotation_names):] if annotation_names else []
        if annotation_names: del stack[-len(annotation_names):]
        names=arg["defaults"]; values=stack[-len(names):] if names else []
        if names: del stack[-len(names):]
        closure=scope.get("$class_outer",scope)
        class_parameters=scope.get("$class_type_parameters",{})
        if class_parameters: closure={**class_parameters,"$closure":closure}
        name=arg.get("name",arg["code"].get("name","<함수>")); qualname=self.qualified_name(scope,name)
        function=Function(CodeObject.from_dict(arg["code"]),self.globals,dict(zip(names,values)),arg["signature"],closure,arg["generator"],arg["async"],dict(zip(annotation_names,annotation_values)),dict(zip(type_names,type_values)),None,name,qualname,scope.get("__name__",self.globals.get("__name__")),arg.get("doc"),arg.get("annotation_codes"),not bool(arg.get("annotation_codes")),arg.get("annotation_strings"),self,set(arg.get("local_names",arg["code"].get("parameters",[]))),set(arg.get("free_names",[])))
        function.free_names.update(name for name in class_parameters if self.code_loads_name(function.code.instructions,name))
        function.builtins_namespace=self.globals.get("__builtins__",builtins.__dict__)
        if "$class_functions" in scope: scope["$class_functions"].append(function)
        if "$class_cell" in scope and "__class__" not in function.local_names and self.code_needs_class_cell(function.code.instructions):
            function.class_cell=scope["$class_cell"]
            if "$class_cell_needed" in scope: scope["$class_cell_needed"]=True
        positional=arg["signature"].get("positional",[]); keyword_only=arg["signature"].get("keyword_only",[]); default_map=function.defaults or {}
        positional_values=tuple(default_map[item] for item in positional if item in default_map)
        keyword_values={item:default_map[item] for item in keyword_only if item in default_map}
        function.positional_defaults=positional_values or None; function.keyword_defaults=keyword_values or None
        return function

    def call_value(self,function,args,kwargs,scope=None):
        if any(not isinstance(name,str) for name in kwargs): raise TypeError("keywords must be strings")
        if function is builtins.globals and not args and not kwargs: return self.globals
        if function is builtins.locals and not args and not kwargs: return self.visible_locals(scope) if scope is not None else self.globals
        if function is builtins.vars and not args and not kwargs: return self.visible_locals(scope) if scope is not None else self.globals
        if function is builtins.dir and not args and not kwargs: return sorted(self.visible_locals(scope) if scope is not None else self.globals)
        if function is sys.exception and not args and not kwargs and scope is not None and "$active_exception" in scope:
            return scope["$active_exception"]
        if function is sys.exc_info and not args and not kwargs and scope is not None and "$active_exception" in scope:
            exception=scope["$active_exception"]
            return type(exception),exception,exception.__traceback__
        if function is builtins.eval and len(args)==1 and not kwargs:
            return builtins.eval(args[0],self.globals,scope if scope is not None else self.globals)
        if function is builtins.exec and len(args)==1 and not kwargs:
            builtins.exec(args[0],self.globals,scope if scope is not None else self.globals)
            return None
        if isinstance(function,BoundFunction): args=[function.instance,*args]; function=function.function
        if isinstance(function,Function):
            caller_scope=scope
            function_scope={**(function.type_parameters or {}),**self.bind(function,args,kwargs),"$closure":function.closure or {},"$local_names":set(function.local_names or function.code.parameters),"$free_names":set(function.free_names or ()),"$qualname_prefix":f"{function.__qualname__}.<locals>"}
            if function.class_cell is not None:
                try: function_scope["__class__"]=function.class_cell.cell_contents
                except ValueError: pass
                function_scope["$has_class_cell"]=True
            if function.class_cell is not None: function_scope["$class_cell"]=function.class_cell
            if function.generator and function.asynchronous: return HythonAsyncGenerator(HythonGenerator(self,function.code,function_scope,function.__name__,function.__qualname__))
            if function.generator: return HythonGenerator(self,function.code,function_scope,function.__name__,function.__qualname__)
            if function.asynchronous: return HythonCoroutine(self,function.code,function_scope,function.__name__,function.__qualname__)
            if caller_scope is not None and "$active_exception" in caller_scope: function_scope["$active_exception"]=caller_scope["$active_exception"]
            try: return self.run(function.code,function_scope)
            except HythonReturn as signal: return signal.value
        if scope is not None and "$active_exception" in scope:
            target=args[0] if function is builtins.next and args else getattr(function,"__self__",None)
            if isinstance(target,(HythonGenerator,HythonAsyncGenerator,HythonCoroutine)):
                self.inherit_active_exception(target,scope)
            active=scope["$active_exception"]
            if sys.exception() is not active:
                try: raise active
                except BaseException: return function(*args,**kwargs)
        return function(*args,**kwargs)

    def match_pattern(self,subject,spec,bindings,environment=None):
        environment=environment or self.globals
        kind=spec["kind"]
        if kind=="wildcard": return True
        if kind=="capture": bindings[spec["name"]]=(subject,spec.get("scope","local")); return True
        if kind=="literal": return subject==spec["value"]
        if kind=="singleton": return subject is spec["value"]
        if kind=="value":
            return subject==self.resolve_pattern_value(spec["path"],environment)
        if kind=="as":
            if not self.match_pattern(subject,spec["pattern"],bindings,environment): return False
            if spec["name"]!="_": bindings[spec["name"]]=(subject,spec.get("scope","local"))
            return True
        if kind=="or":
            for item in spec["items"]:
                trial={}
                if self.match_pattern(subject,item,trial,environment): bindings.update(trial); return True
            return False
        if kind=="sequence":
            if isinstance(subject,(str,bytes,bytearray)) or not isinstance(subject,Sequence): return False
            items=spec["items"]; stars=[i for i,p in enumerate(items) if p["kind"]=="star"]
            if len(stars)>1: return False
            if not stars and len(subject)!=len(items): return False
            if stars and len(subject)<len(items)-1: return False
            star=stars[0] if stars else None
            for index,pattern in enumerate(items):
                if pattern["kind"]=="star":
                    if pattern["name"]!="_":
                        stop=len(subject)-(len(items)-index-1)
                        bindings[pattern["name"]]=([subject[position] for position in range(index,stop)],pattern.get("scope","local"))
                    continue
                actual=index if star is None or index<star else len(subject)-(len(items)-index)
                if not self.match_pattern(subject[actual],pattern,bindings,environment): return False
            return True
        if kind=="mapping":
            if not isinstance(subject,Mapping): return False
            used=set()
            for pair in spec["pairs"]:
                key_spec=pair["key"]
                key=key_spec["value"] if key_spec["kind"]=="literal" else self.resolve_pattern_value(key_spec["path"],environment)
                if key in used: raise ValueError(f"매핑 패턴 키 중복: {key!r}")
                value=subject.get(key,_MISSING)
                if value is _MISSING: return False
                used.add(key)
                if not self.match_pattern(value,pair["pattern"],bindings,environment): return False
            if spec["rest"] and spec["rest"]!="_": bindings[spec["rest"]]=({k:v for k,v in subject.items() if k not in used},spec.get("rest_scope","local"))
            return True
        if kind=="class":
            expected=self.resolve_pattern_value(spec["name"],environment)
            if not isinstance(expected,type): raise TypeError("클래스 패턴 대상은 형식이어야 합니다.")
            if not isinstance(subject,expected): return False
            positional=spec["positional"]
            if not positional:
                positional_names=()
            else:
                match_args=getattr(expected,"__match_args__",_MISSING)
                match_self=match_args is _MISSING and issubclass(expected,_MATCH_SELF_TYPES)
                if match_args is _MISSING: match_args=()
                elif not isinstance(match_args,tuple): raise TypeError("__match_args__는 튜플이어야 합니다.")
                if match_self:
                    if len(positional)>1: raise TypeError("클래스 패턴의 위치 패턴이 너무 많습니다.")
                    positional_names=(None,)
                else:
                    if len(positional)>len(match_args): raise TypeError("클래스 패턴의 위치 패턴이 너무 많습니다.")
                    positional_names=match_args[:len(positional)]
                    if not all(isinstance(name,str) for name in positional_names): raise TypeError("사용되는 __match_args__ 항목은 문자열이어야 합니다.")
            keyword_names=[item["name"] for item in spec["keywords"]]
            seen_attributes=set()
            for attribute in (*positional_names,*keyword_names):
                if attribute is None: continue
                if attribute in seen_attributes: raise TypeError(f"클래스 패턴 속성 중복: {attribute}")
                seen_attributes.add(attribute)
            for attribute,pattern in zip(positional_names,positional):
                if attribute is None: value=subject
                else:
                    try: value=getattr(subject,attribute)
                    except AttributeError: return False
                if not self.match_pattern(value,pattern,bindings,environment): return False
            for item in spec["keywords"]:
                try: value=getattr(subject,item["name"])
                except AttributeError: return False
                if not self.match_pattern(value,item["pattern"],bindings,environment): return False
            return True
        return False

    def resolve_pattern_value(self,path,environment):
        parts=path.split(".")
        if parts[0] in environment: value=environment[parts[0]]
        elif parts[0] in self.globals: value=self.globals[parts[0]]
        else: raise NameError(parts[0])
        for part in parts[1:]: value=getattr(value,part)
        return value

    def apply_pattern_bindings(self,scope,bindings):
        for name,(value,storage) in bindings.items(): self.assign_name(scope,name,value,storage)

    def generator_expression(self,arg,local):
        scope=ComprehensionScope(self.comprehension_parent(local),arg.get("bindings",()))
        first=arg["clauses"][0]
        outer_iterator=iter(self.run(CodeObject.from_dict(first["iter"]),scope))
        def generate(index):
            if index<len(arg["clauses"]):
                clause=arg["clauses"][index]
                iterable=outer_iterator if index==0 else self.run(CodeObject.from_dict(clause["iter"]),scope)
                iterator=iterable if index==0 else iter(iterable)
                while True:
                    try: item=next(iterator)
                    except StopIteration: break
                    self.assign_target(scope,clause["target"],item)
                    if all(self.run(CodeObject.from_dict(test),scope) for test in clause["filters"]):
                        yield from generate(index+1)
                return
            value=self.run(CodeObject.from_dict(arg["element"]),scope); self.commit_comprehension_bindings(arg,scope,local); yield value
        return generate(0)

    def async_generator_expression(self,arg,local,scope=None,outer=_MISSING,waiter=None):
        scope=ComprehensionScope(self.comprehension_parent(local),arg.get("bindings",())) if scope is None else scope
        first=arg["clauses"][0]
        if outer is _MISSING: outer=self.run(CodeObject.from_dict(first["iter"]),scope)
        outer_iterator=builtins.aiter(outer) if first.get("async",False) else iter(outer)
        async def evaluate(payload):
            coroutine=HythonCoroutine(self,CodeObject.from_dict(payload),scope)
            return await (waiter(coroutine) if waiter is not None else coroutine)
        async def generate(index):
            if index<len(arg["clauses"]):
                clause=arg["clauses"][index]; iterable=outer_iterator if index==0 else await evaluate(clause["iter"])
                async def accepted(item):
                    self.assign_target(scope,clause["target"],item)
                    for test in clause["filters"]:
                        if not await evaluate(test): return False
                    return True
                if clause.get("async",False):
                    iterator=iterable if index==0 else builtins.aiter(iterable)
                    while True:
                        try: item=await builtins.anext(iterator)
                        except StopAsyncIteration: break
                        if await accepted(item):
                            async for result in generate(index+1): yield result
                else:
                    iterator=iterable if index==0 else iter(iterable)
                    while True:
                        try: item=next(iterator)
                        except StopIteration: break
                        if await accepted(item):
                            async for result in generate(index+1): yield result
                return
            value=await evaluate(arg["element"]); self.commit_comprehension_bindings(arg,scope,local); yield value
        return generate(0)

    async def prepare_async_generator_expression(self,arg,local,waiter=None):
        scope=ComprehensionScope(self.comprehension_parent(local),arg.get("bindings",())); first=arg["clauses"][0]
        awaitable=HythonCoroutine(self,CodeObject.from_dict(first["iter"]),scope)
        outer=await (waiter(awaitable) if waiter is not None else awaitable)
        return self.async_generator_expression(arg,local,scope,outer)

    async def run_async_comprehension(self,arg,local,waiter=None):
        result={} if arg["kind"]=="dictcomp" else set() if arg["kind"]=="setcomp" else []
        scope=ComprehensionScope(self.comprehension_parent(local),arg.get("bindings",()))
        async def evaluate(payload):
            coroutine=HythonCoroutine(self,CodeObject.from_dict(payload),scope)
            return await (waiter(coroutine) if waiter is not None else coroutine)
        async def wait(awaitable): return await (waiter(awaitable) if waiter is not None else awaitable)
        async def collect(index):
            if index<len(arg["clauses"]):
                clause=arg["clauses"][index]; iterable=await evaluate(clause["iter"])
                async def visit(item):
                    self.assign_target(scope,clause["target"],item)
                    for test in clause["filters"]:
                        if not await evaluate(test): return
                    await collect(index+1)
                if clause.get("async",False):
                    iterator=builtins.aiter(iterable)
                    while True:
                        try: item=await wait(builtins.anext(iterator))
                        except StopAsyncIteration: break
                        await visit(item)
                else:
                    for item in iterable: await visit(item)
                return
            if arg["kind"]=="dictcomp": result[await evaluate(arg["key"])]=await evaluate(arg["value"])
            else:
                value=await evaluate(arg["element"]); result.add(value) if arg["kind"]=="setcomp" else result.append(value)
        await collect(0); self.commit_comprehension_bindings(arg,scope,local); return result

    @staticmethod
    def commit_comprehension_bindings(arg,scope,local):
        for name in arg.get("bindings",[]):
            if name in scope: local[name]=scope[name]

    def assign_target(self,scope,spec,value):
        if isinstance(spec,str): scope[spec]=value; return
        if spec["kind"]=="name": self.assign_name(scope,spec["name"],value,spec.get("scope","local")); return
        if spec["kind"]=="attribute": setattr(self.run(CodeObject.from_dict(spec["object"]),scope),spec["name"],value); return
        if spec["kind"]=="subscript":
            target=self.run(CodeObject.from_dict(spec["object"]),scope); index=self.run(CodeObject.from_dict(spec["index"]),scope); target[index]=value; return
        if spec["kind"]=="starred": self.assign_target(scope,spec["target"],list(value)); return
        items=spec["items"]; stars=[i for i,item in enumerate(items) if item["kind"]=="starred"]
        if len(stars)>1: raise VMError("구조 분해 별표 대상은 하나만 허용됩니다.")
        if not stars:
            assigned=self.unpack_exact(value,len(items))
        else:
            star=stars[0]; after=len(items)-star-1
            assigned=self.unpack_extended(value,star,after)
        for target,item in zip(items,assigned): self.assign_target(scope,target,item)

    @staticmethod
    def unpack_exact(value,expected):
        iterator=iter(value); values=[]
        for _ in range(expected):
            try: values.append(next(iterator))
            except StopIteration: raise ValueError(f"not enough values to unpack (expected {expected}, got {len(values)})") from None
        try: next(iterator)
        except StopIteration: return values
        raise ValueError(f"too many values to unpack (expected {expected})")

    @staticmethod
    def unpack_extended(value,before,after):
        values=list(value); minimum=before+after
        if len(values)<minimum: raise ValueError(f"not enough values to unpack (expected at least {minimum}, got {len(values)})")
        tail=values[len(values)-after:] if after else []
        return [*values[:before],values[before:len(values)-after if after else None],*tail]

    @staticmethod
    def compare_values(name,left,right):
        operations={"==":operator.eq,"!=":operator.ne,"<":operator.lt,"<=":operator.le,">":operator.gt,">=":operator.ge,
                    "in":lambda a,b:a in b,"is":operator.is_,"not in":lambda a,b:a not in b,"is not":operator.is_not}
        return operations[name](left,right)

    def run_compare_chain(self,arg,local):
        operands=arg["operands"]; operators=arg["operators"]; left=self.run(CodeObject.from_dict(operands[0]),local); result=True
        for index,(operator_name,payload) in enumerate(zip(operators,operands[1:])):
            right=self.run(CodeObject.from_dict(payload),local)
            result=self.compare_values(operator_name,left,right)
            if index<len(operators)-1 and not result: return result
            left=right
        return result

    def make_type_alias(self,arg,local):
        payloads=[]
        for payload in arg["parameters"]:
            if isinstance(payload,(list,tuple)): payload={"kind":payload[0],"name":payload[1],"bound":None,"default":None}
            payloads.append(payload)
        if arg.get("value_text") is not None:
            namespace=TypeExpressionNamespace(local,{"__name__":local.get("__name__",self.globals.get("__name__","__main__"))},self.globals)
            declarations=[]
            for payload in payloads:
                prefix={"typevar":"","typevartuple":"*","paramspec":"**"}[payload["kind"]]
                declaration=f'{prefix}{payload["name"]}'
                if payload.get("bound_text") is not None: declaration+=f': {payload["bound_text"]}'
                if payload.get("default_text") is not None: declaration+=f' = {payload["default_text"]}'
                declarations.append(declaration)
            parameters=f"[{', '.join(declarations)}]" if declarations else ""
            builtins.exec(f'type {arg["name"]}{parameters} = {arg["value_text"]}',namespace)
            return namespace[arg["name"]]
        namespace={"__name__":local.get("__name__",self.globals.get("__name__","__main__"))}
        previous=[]; declarations=[]
        def evaluator(code,names):
            def evaluate(*values):
                scope=dict(local); scope.update(zip(names,values))
                return self.run(CodeObject.from_dict(code),scope)
            return evaluate
        for index,payload in enumerate(payloads):
            prefix={"typevar":"","typevartuple":"*","paramspec":"**"}[payload["kind"]]
            declaration=f'{prefix}{payload["name"]}'
            arguments=','.join(previous)
            if payload.get("bound") is not None:
                helper=f"__hython_bound_{index}"; namespace[helper]=evaluator(payload["bound"],tuple(previous))
                declaration+=f": {helper}({arguments})"
            if payload.get("default") is not None:
                helper=f"__hython_default_{index}"; namespace[helper]=evaluator(payload["default"],tuple(previous))
                declaration+=f" = {helper}({arguments})"
            declarations.append(declaration); previous.append(payload["name"])
        value_helper="__hython_alias_value"
        namespace[value_helper]=evaluator(arg["value"],tuple(previous))
        parameters=f"[{', '.join(declarations)}]" if declarations else ""
        arguments=','.join(previous)
        builtins.exec(f'type {arg["name"]}{parameters} = {value_helper}({arguments})',namespace)
        return namespace[arg["name"]]

    def make_type_parameter(self,arg,local):
        group_names=arg.get("group_names",[arg["name"]]); group_index=arg.get("group_index",0)
        if group_index==0:
            group_scope={"$closure":local}
            local["$type_parameter_scope"]=group_scope
        else: group_scope=local.get("$type_parameter_scope",{"$closure":local})
        if arg.get("bound_text") is not None or arg.get("default_text") is not None:
            namespace=TypeExpressionNamespace(group_scope,{"__name__":local.get("__name__",self.globals.get("__name__","__main__"))},self.globals)
            prefix={"typevar":"","typevartuple":"*","paramspec":"**"}[arg["kind"]]
            declaration=f'{prefix}{arg["name"]}'
            if arg.get("bound_text") is not None: declaration+=f': {arg["bound_text"]}'
            if arg.get("default_text") is not None: declaration+=f' = {arg["default_text"]}'
            builtins.exec(f"type __HythonParameter[{declaration}] = object",namespace)
            parameter=namespace["__HythonParameter"].__type_params__[0]
        else:
            namespace={"__name__":local.get("__name__",self.globals.get("__name__","__main__"))}
            prefix={"typevar":"","typevartuple":"*","paramspec":"**"}[arg["kind"]]
            declaration=f'{prefix}{arg["name"]}'
            def evaluator(code):
                def evaluate(): return self.run(CodeObject.from_dict(code),dict(group_scope))
                return evaluate
            if arg.get("bound") is not None:
                namespace["__hython_bound"]=evaluator(arg["bound"]); declaration+=" : __hython_bound()"
            if arg.get("default") is not None:
                namespace["__hython_default"]=evaluator(arg["default"]); declaration+=" = __hython_default()"
            builtins.exec(f"type __HythonParameter[{declaration}] = object",namespace)
            parameter=namespace["__HythonParameter"].__type_params__[0]
        group_scope[arg["name"]]=parameter
        if group_index==len(group_names)-1: local.pop("$type_parameter_scope",None)
        return parameter

    def run(self, code: CodeObject, locals_: dict | None = None):
        try:
            return self._run(code,locals_)
        except (HythonReturn,HythonBreak,HythonContinue,HythonAwait,HythonAsyncDelegate):
            raise
        except BaseException as exc:
            self.restore_saved_names(self.globals if locals_ is None else locals_)
            index=self._last_instruction.get(id(code),0)
            line=code.lines[index] if code.lines and 0<=index<len(code.lines) else 0
            frame=(code.name,line,index)
            frames=getattr(exc,"__hython_frames__",None)
            if frames is None:
                frames=[]
                try: setattr(exc,"__hython_frames__",frames)
                except Exception: frames=None
            if frames is not None and (not frames or frames[-1]!=frame):
                frames.append(frame)
                location=f"{code.name}:{line}" if line else code.name
                try: exc.add_note(f"하이썬 위치: {location}")
                except (AttributeError,TypeError): pass
            raise

    def _run(self, code: CodeObject, locals_: dict | None = None):
        local = self.globals if locals_ is None else locals_
        stack=[]; ip=0; instructions=code.instructions
        binary={"ADD":operator.add,"SUB":operator.sub,"MUL":operator.mul,"DIV":operator.truediv,"FLOORDIV":operator.floordiv,"MOD":operator.mod,"POW":operator.pow,
                "EQ":operator.eq,"NE":operator.ne,"LT":operator.lt,"LE":operator.le,"GT":operator.gt,"GE":operator.ge,"IN":lambda a,b:a in b,"IS":operator.is_,
                "NOT_IN":lambda a,b:a not in b,"IS_NOT":operator.is_not}
        binary.update({"BIT_OR":operator.or_,"BIT_XOR":operator.xor,"BIT_AND":operator.and_,"LSHIFT":operator.lshift,"RSHIFT":operator.rshift,"MATMUL":operator.matmul})
        binary.update({"IADD":operator.iadd,"ISUB":operator.isub,"IMUL":operator.imul,"IDIV":operator.itruediv,"IFLOORDIV":operator.ifloordiv,"IMOD":operator.imod,"IPOW":operator.ipow,"IBIT_OR":operator.ior,"IBIT_XOR":operator.ixor,"IBIT_AND":operator.iand,"ILSHIFT":operator.ilshift,"IRSHIFT":operator.irshift,"IMATMUL":operator.imatmul})
        while ip < len(instructions):
            self._last_instruction[id(code)]=ip
            if self.instruction_hook is not None:
                self.instruction_hook(code,ip,local,stack)
            ins=instructions[ip]; op=ins[0]; arg=ins[1] if len(ins)>1 else None; ip+=1
            if op=="CONST": stack.append(code.constants[arg])
            elif op=="LOAD":
                if arg in local: stack.append(local[arg])
                elif arg in local.get("$local_names",()): raise UnboundLocalError(f"local variable '{arg}' referenced before assignment")
                elif arg in local.get("$free_names",()):
                    closure=self.nonlocal_scope(local,arg)
                    if arg not in closure: raise NameError(f"free variable '{arg}' is not defined in enclosing scope")
                    stack.append(closure[arg])
                elif (found:=self.lookup_closure(local,arg))[0]: stack.append(found[1])
                elif "$class_outer" in local and arg not in local.get("$class_local_names",()) and arg in local["$class_outer"]: stack.append(local["$class_outer"][arg])
                elif arg in self.globals: stack.append(self.globals[arg])
                else: raise NameError(f"name '{arg}' is not defined")
            elif op=="STORE": local[arg]=stack.pop()
            elif op=="SAVE_NAME": self.save_name(local,arg)
            elif op=="RESTORE_NAME": self.restore_name(local,arg)
            elif op=="ANNOTATE": local.setdefault("__annotations__",{})[arg]=stack.pop()
            elif op=="ANNOTATE_LAZY": self.register_annotation(local,arg)
            elif op=="SUPER": stack.append(self.zero_argument_super(local,arg))
            elif op=="MAKE_TYPE_ALIAS": stack.append(self.make_type_alias(arg,local))
            elif op=="MAKE_TYPE_PARAMETER": stack.append(self.make_type_parameter(arg,local))
            elif op=="UNPACK":
                values=self.unpack_exact(stack.pop(),arg)
                stack.extend(reversed(values))
            elif op=="UNPACK_EX":
                before=arg>>16; after=arg&0xFFFF
                stack.extend(reversed(self.unpack_extended(stack.pop(),before,after)))
            elif op=="STORE_GLOBAL": self.globals[arg]=stack.pop()
            elif op=="STORE_NONLOCAL":
                closure=self.nonlocal_scope(local,arg)
                closure[arg]=stack.pop()
            elif op=="DELETE":
                if arg not in local: raise self.missing_delete_error(local,arg)
                del local[arg]
            elif op=="DELETE_GLOBAL":
                if arg not in self.globals: raise NameError(f"name '{arg}' is not defined")
                del self.globals[arg]
            elif op=="DELETE_NONLOCAL":
                closure=self.nonlocal_scope(local,arg)
                if arg not in closure: raise NameError(f"free variable '{arg}' is not defined in enclosing scope")
                del closure[arg]
            elif op=="POP": stack.pop()
            elif op=="DUP": stack.append(stack[-1])
            elif op=="DUP2": stack.extend(stack[-2:])
            elif op in binary: b=stack.pop(); a=stack.pop(); stack.append(binary[op](a,b))
            elif op in ("NEG","POS","NOT","INVERT"): stack.append({"NEG":operator.neg,"POS":operator.pos,"NOT":operator.not_,"INVERT":operator.invert}[op](stack.pop()))
            elif op=="JUMP": ip=arg
            elif op=="JUMP_FALSE":
                if not stack.pop(): ip=arg
            elif op=="JUMP_IF_FALSE_OR_POP":
                if not stack[-1]: ip=arg
                else: stack.pop()
            elif op=="JUMP_IF_TRUE_OR_POP":
                if stack[-1]: ip=arg
                else: stack.pop()
            elif op=="ITER": stack.append(iter(stack.pop()))
            elif op=="FOR_ITER":
                try: stack.append(next(stack[-1]))
                except StopIteration: stack.pop(); ip=arg
            elif op in ("BUILD_LIST","BUILD_TUPLE","BUILD_SET"):
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(list(values) if op=="BUILD_LIST" else tuple(values) if op=="BUILD_TUPLE" else set(values))
            elif op=="BUILD_DICT":
                values=stack[-arg*2:] if arg else []
                if arg: del stack[-arg*2:]
                stack.append(dict(zip(values[::2],values[1::2])))
            elif op=="BUILD_UNPACK":
                count=len(arg["starred"]); values=stack[-count:] if count else []
                if count: del stack[-count:]
                merged=[]
                for value,starred in zip(values,arg["starred"]): merged.extend(value) if starred else merged.append(value)
                stack.append(tuple(merged) if arg["kind"]=="tuple" else set(merged) if arg["kind"]=="set" else merged)
            elif op=="BUILD_DICT_UNPACK":
                count=sum(2 if item=="pair" else 1 for item in arg); values=stack[-count:] if count else []
                if count: del stack[-count:]
                result={}; index=0
                for item in arg:
                    if item=="pair": result[values[index]]=values[index+1]; index+=2
                    else: result.update(values[index]); index+=1
                stack.append(result)
            elif op=="COLLECTION_BEGIN": stack.append(self.collection_builder(arg))
            elif op=="COLLECTION_ADD":
                value=stack.pop(); key=stack.pop() if arg=="pair" else None
                self.add_collection_item(stack[-1],arg,value,key)
            elif op=="COLLECTION_READY": stack.append(self.finish_collection(stack.pop()))
            elif op=="BUILD_SLICE":
                step=stack.pop(); stop=stack.pop(); start=stack.pop(); stack.append(slice(start,stop,step))
            elif op=="GET_ITEM":
                index=stack.pop(); container=stack.pop(); stack.append(container[index])
            elif op=="SET_ITEM":
                value=stack.pop(); index=stack.pop(); container=stack.pop(); container[index]=value
            elif op=="DELETE_ITEM":
                index=stack.pop(); container=stack.pop(); del container[index]
            elif op=="GET_ATTR": stack.append(getattr(stack.pop(),arg))
            elif op=="SET_ATTR":
                value=stack.pop(); target=stack.pop(); setattr(target,arg,value)
            elif op=="DELETE_ATTR": delattr(stack.pop(),arg)
            elif op=="IMPORT": stack.append(self.import_module(arg,code))
            elif op=="IMPORT_FROM": stack.append(self.import_from(arg["module"],arg["name"],code))
            elif op=="IMPORT_STAR": self.import_star(local,stack.pop())
            elif op=="FORMAT": stack.append(str(stack.pop()))
            elif op=="FORMAT_VALUE":
                spec=stack.pop() if arg["has_spec"] else ""; value=stack.pop()
                if arg["conversion"]=="r": value=repr(value)
                elif arg["conversion"]=="s": value=str(value)
                elif arg["conversion"]=="a": value=ascii(value)
                stack.append(format(value,spec))
            elif op=="BUILD_STRING":
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append("".join(values))
            elif op=="MAKE_INTERPOLATION":
                spec=stack.pop(); conversion=stack.pop(); expression=stack.pop(); value=stack.pop(); stack.append(Interpolation(value,expression,conversion,spec))
            elif op=="BUILD_TEMPLATE":
                values=stack[-arg:] if arg else []
                if arg: del stack[-arg:]
                stack.append(Template(*values))
            elif op=="ASSERT":
                message=stack.pop(); condition=stack.pop()
                if not condition: raise AssertionError(message) if message is not None else AssertionError()
            elif op=="MATCH_PATTERN":
                bindings={}; matched=self.match_pattern(stack.pop(),arg,bindings,local)
                if matched: self.apply_pattern_bindings(local,bindings)
                stack.append(matched)
            elif op=="CHAIN_COMPARE": stack.append(self.run_compare_chain(arg,local))
            elif op=="RAISE": raise stack.pop()
            elif op=="RAISE_FROM":
                cause=stack.pop(); error=stack.pop(); raise error from cause
            elif op=="RERAISE":
                self.reraise(local)
            elif op=="TRY":
                failure=None; control=None
                try:
                    self.run(CodeObject.from_dict(arg["body"]),local)
                except (HythonBreak,HythonContinue) as signal:
                    control=signal
                except HythonReturn:
                    raise
                except BaseException as exc:
                    if arg["handlers"] and arg["handlers"][0].get("star",False):
                        original=exc if isinstance(exc,BaseExceptionGroup) else BaseExceptionGroup("",[exc]); remaining=original; raised=[]; reraised=[]
                        for handler in arg["handlers"]:
                            expected=self.run(CodeObject.from_dict(handler["type"]),local)
                            matched,remaining=remaining.split(expected)
                            if matched is None: continue
                            if handler["alias"]: self.assign_name(local,handler["alias"],matched,handler.get("alias_scope","local"))
                            previous=self.push_active_exception(local,matched)
                            try: self.run(CodeObject.from_dict(handler["code"]),local)
                            except BaseException as failure:
                                (reraised if failure is matched else raised).append(failure)
                            finally:
                                self.pop_active_exception(local,previous)
                                if handler["alias"]: self.delete_name(local,handler["alias"],handler.get("alias_scope","local"))
                        failure=_merge_except_star(original,reraised,raised,remaining)
                        if failure is not None: raise failure
                        failure=None; continue
                    failure=exc; handled=False
                    for handler in arg["handlers"]:
                        expected=self.run(CodeObject.from_dict(handler["type"]),local) if handler["type"] else BaseException
                        if isinstance(exc,expected):
                            if handler["alias"]: self.assign_name(local,handler["alias"],exc,handler.get("alias_scope","local"))
                            previous=self.push_active_exception(local,exc)
                            try: self.run(CodeObject.from_dict(handler["code"]),local)
                            finally:
                                self.pop_active_exception(local,previous)
                                if handler["alias"]: self.delete_name(local,handler["alias"],handler.get("alias_scope","local"))
                            handled=True; failure=None; break
                    if not handled: raise
                else:
                    if arg["else"]: self.run(CodeObject.from_dict(arg["else"]),local)
                finally:
                    if arg["finally"]:
                        active=sys.exception(); previous=_MISSING; pushed=False
                        if active is not None and not isinstance(active,(HythonReturn,HythonBreak,HythonContinue)):
                            previous=self.push_active_exception(local,active); pushed=True
                        try: self.run(CodeObject.from_dict(arg["finally"]),local)
                        finally:
                            if pushed: self.pop_active_exception(local,previous)
                if isinstance(control,HythonBreak): ip=arg["break_target"]
                elif isinstance(control,HythonContinue): ip=arg["continue_target"]
            elif op=="COMPREHENSION":
                if any(clause.get("async",False) for clause in arg["clauses"]):
                    if arg["kind"]=="generatorexpr": stack.append(self.async_generator_expression(arg,local)); continue
                    raise VMError("비동기 컴프리헨션은 비동기 함수 안에서만 사용할 수 있습니다.")
                if arg["kind"]=="generatorexpr": stack.append(self.generator_expression(arg,local)); continue
                scope=ComprehensionScope(self.comprehension_parent(local),arg.get("bindings",()))
                result={} if arg["kind"]=="dictcomp" else set() if arg["kind"]=="setcomp" else []
                def collect(index):
                    if index<len(arg["clauses"]):
                        clause=arg["clauses"][index]
                        iterable=self.run(CodeObject.from_dict(clause["iter"]),scope)
                        for item in iterable:
                            self.assign_target(scope,clause["target"],item)
                            if all(self.run(CodeObject.from_dict(test),scope) for test in clause["filters"]): collect(index+1)
                        return
                    if arg["kind"]=="dictcomp":
                        key=self.run(CodeObject.from_dict(arg["key"]),scope)
                        value=self.run(CodeObject.from_dict(arg["value"]),scope); result[key]=value
                    else:
                        value=self.run(CodeObject.from_dict(arg["element"]),scope)
                        result.add(value) if arg["kind"]=="setcomp" else result.append(value)
                collect(0); self.commit_comprehension_bindings(arg,scope,local)
                stack.append(result)
            elif op=="WITH":
                exits=[]; failure=None
                try:
                    for manager in arg["managers"]:
                        context=self.run(CodeObject.from_dict(manager["code"]),local)
                        enter_method,exit_method=self.context_methods(context,False)
                        entered=enter_method()
                        exits.append(exit_method)
                        if manager["alias"]: self.assign_target(local,manager["alias"],entered)
                    self.run(CodeObject.from_dict(arg["body"]),local)
                except BaseException as caught:
                    failure=caught
                try: self.unwind_exits(exits,failure)
                except HythonBreak: ip=arg["break_target"]
                except HythonContinue: ip=arg["continue_target"]
            elif op=="MAKE_FUNCTION":
                stack.append(self.create_function(arg,local,stack))
            elif op=="MAKE_CLASS":
                stack.append(self.create_class(arg,local,stack))
            elif op=="CALL":
                args=stack[-arg:] if arg else []; 
                if arg: del stack[-arg:]
                function=stack.pop(); stack.append(self.call_value(function,args,{},local))
            elif op=="CALL_EX":
                values=stack[-len(arg):] if arg else []
                if arg: del stack[-len(arg):]
                function=stack.pop(); positional,keywords=self.expand_call_arguments(arg,values)
                stack.append(self.call_value(function,positional,keywords,local))
            elif op=="CALL_BEGIN": stack.append(CallArguments([],{}))
            elif op=="CALL_ARG": self.add_call_argument(stack[-2],arg,stack.pop())
            elif op=="CALL_READY":
                arguments=stack.pop(); function=stack.pop()
                stack.append(self.call_value(function,arguments.positional,arguments.keywords,local))
            elif op=="CLASS_BEGIN": stack.append(CallArguments([],{}))
            elif op=="CLASS_ARG": self.add_class_argument(stack[-2],arg,stack.pop())
            elif op=="RETURN": return stack.pop()
            elif op=="SIGNAL_RETURN": raise HythonReturn(stack.pop())
            elif op=="SIGNAL_BREAK": raise HythonBreak()
            elif op=="SIGNAL_CONTINUE": raise HythonContinue()
            elif op=="NOP": pass
            else: raise VMError(f"알 수 없는 HBC 명령어: {op}")
        return None
    @staticmethod
    def lookup_closure(scope,name):
        seen=set(); current=scope.get("$closure") if isinstance(scope,dict) else None
        while isinstance(current,dict) and id(current) not in seen:
            seen.add(id(current))
            if name in current: return True,current[name]
            current=current.get("$closure")
        return False,None

    @staticmethod
    def nonlocal_scope(scope,name):
        seen=set(); current=scope.get("$closure",scope.get("$class_outer")) if isinstance(scope,dict) else None
        while isinstance(current,dict) and id(current) not in seen:
            seen.add(id(current))
            if "$class_outer" in current:
                current=current["$class_outer"]
                continue
            if name in current or name in current.get("$local_names",()): return current
            current=current.get("$closure")
        raise NameError(f"free variable '{name}' is not defined in enclosing scope")

    @staticmethod
    def bind_class_functions(namespace,owner):
        for name in namespace:
            value=namespace[name]
            if isinstance(value,(staticmethod,classmethod)):
                targets=(value.__func__,)
            elif isinstance(value,property):
                targets=(value.fget,value.fset,value.fdel)
            else:
                targets=(value,)
            for target in targets:
                VM.bind_class_function(target,owner)

    @staticmethod
    def bind_class_function(target,owner):
        expected=f"{owner.__qualname__}.{target.__name__}" if isinstance(target,Function) else None
        if isinstance(target,Function) and target.__qualname__==expected:
            target.class_owner=owner
            target.module_name=owner.__module__

    @staticmethod
    def code_needs_class_cell(value):
        if isinstance(value,(list,tuple)):
            direct=bool(value and (value[0]=="SUPER" or len(value)>1 and value[0]=="LOAD" and value[1]=="__class__"))
            return direct or any(VM.code_needs_class_cell(item) for item in value)
        if isinstance(value,dict): return any(VM.code_needs_class_cell(item) for item in value.values())
        return False

    @staticmethod
    def code_loads_name(value,name):
        if isinstance(value,(list,tuple)):
            direct=len(value)>1 and value[0]=="LOAD" and value[1]==name
            return direct or any(VM.code_loads_name(item,name) for item in value)
        if isinstance(value,dict): return any(VM.code_loads_name(item,name) for item in value.values())
        return False

    @staticmethod
    def comprehension_parent(scope):
        return scope.get("$class_outer",scope) if isinstance(scope,dict) else scope

    @staticmethod
    def missing_delete_error(scope,name):
        if name in scope.get("$local_names",()):
            return UnboundLocalError(f"local variable '{name}' referenced before assignment")
        return NameError(f"name '{name}' is not defined")

    @staticmethod
    def visible_locals(scope):
        hidden=scope.get("$class_type_parameters",{}) if isinstance(scope,dict) else {}
        visible={name:value for name,value in scope.items() if not name.startswith("$") and not (name in hidden and value is hidden[name])}
        if isinstance(scope,dict) and "$closure" in scope and "$class_outer" not in scope:
            for name in scope.get("$free_names",()):
                if name in visible: continue
                found,value=VM.lookup_closure(scope,name)
                if found: visible[name]=value
        return visible

    @staticmethod
    def qualified_name(scope,name):
        prefix=scope.get("$qualname_prefix") if isinstance(scope,dict) else None
        return f"{prefix}.{name}" if prefix else name

    def assign_name(self,scope,name,value,storage="local"):
        if storage=="global": self.globals[name]=value
        elif storage=="nonlocal": self.nonlocal_scope(scope,name)[name]=value
        else: scope[name]=value

    def delete_name(self,scope,name,storage="local"):
        target=self.globals if storage=="global" else self.nonlocal_scope(scope,name) if storage=="nonlocal" else scope
        target.pop(name,None)
