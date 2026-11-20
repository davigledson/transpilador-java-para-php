"""Análise semântica do subconjunto de Java.

Responsabilidades:
- montar a tabela de classes, campos, métodos e construtores;
- resolver nomes e escopos;
- inferir/checar tipos;
- anotar a AST com informações que o gerador de código precisa
  (``binding``, ``call_kind``, ``is_length``, ``is_static_field`` etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ast
from .erros import TranspileError


PRIMITIVES = {"int", "double", "boolean", "char"}
BUILTIN_CLASSES = {"System", "Math", "Integer", "Double", "Boolean", "Character"}
LIBRARY_TYPES = {
    "ArrayList",
    "List",
    "Scanner",
    "HashMap",
    "Map",
    "HashSet",
    "Set",
    "Stream",
    "Class",
}
LIST_TYPES = {"ArrayList", "List"}
MAP_TYPES = {"HashMap", "Map"}
SET_TYPES = {"HashSet", "Set"}
STREAM_TYPES = {"Stream"}
CLASS_TYPES = {"Class"}
BUILTIN_INTERFACES = {"AutoCloseable", "Closeable"}
EXCEPTION_TYPES = {
    "Throwable",
    "Error",
    "Exception",
    "RuntimeException",
    "IllegalArgumentException",
    "IllegalStateException",
    "ArithmeticException",
    "NullPointerException",
    "IndexOutOfBoundsException",
    "IOException",
}
EXCEPTION_PARENTS = {
    "Error": "Throwable",
    "Exception": "Throwable",
    "RuntimeException": "Exception",
    "IllegalArgumentException": "RuntimeException",
    "IllegalStateException": "RuntimeException",
    "ArithmeticException": "RuntimeException",
    "NullPointerException": "RuntimeException",
    "IndexOutOfBoundsException": "RuntimeException",
    "IOException": "Exception",
}
NUMERIC = {"int", "double", "char"}
INTEGRAL = {"int", "char"}

PRIMITIVE_MAP = {"long": "int", "float": "double", "byte": "int", "short": "int"}


@dataclass
class FieldInfo:
    name: str
    type: ast.JavaType
    is_static: bool
    node: ast.FieldDecl


@dataclass
class MethodInfo:
    name: str
    return_type: ast.JavaType
    params: list[ast.JavaType]
    is_static: bool
    node: ast.MethodDecl
    is_override: bool = False
    is_abstract: bool = False


@dataclass
class CtorInfo:
    params: list[ast.JavaType]
    node: ast.ConstructorDecl


@dataclass
class ClassInfo:
    name: str
    parent: str | None = None
    fields: dict[str, FieldInfo] = field(default_factory=dict)
    methods: dict[str, MethodInfo] = field(default_factory=dict)
    ctors: list[CtorInfo] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    permits: list[str] = field(default_factory=list)
    node: ast.ClassDecl | None = None
    has_main: bool = False
    is_interface: bool = False
    is_abstract: bool = False
    is_enum: bool = False
    is_record: bool = False
    enum_constants: list[str] = field(default_factory=list)
    package: str | None = None
    qualified_name: str = ""


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.classes: dict[str, ClassInfo] = {}
        self.program: ast.Program | None = None

        self.current_class: ClassInfo | None = None
        self.current_method: MethodInfo | None = None
        self.current_static = False
        self.current_return_type: ast.JavaType | None = None
        self.loop_depth = 0
        self.switch_depth = 0
        self.switch_expr_depth = 0
        self.yield_types_stack: list[list[ast.JavaType]] = []
        self.in_constructor = False

        self.scopes: list[dict[str, ast.JavaType]] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def analyze(self, program: ast.Program) -> None:
        self.program = program
        for cls in program.classes:
            self._predeclare_class(cls)
        self._validate_hierarchy()
        for cls in program.classes:
            self._declare_members(cls)
        for cls in program.classes:
            self._check_class(cls)
        self._check_mains()

    # ------------------------------------------------------------------
    # Auxiliares de erro e tipo
    # ------------------------------------------------------------------

    def _error(self, message: str, node: object) -> None:
        raise TranspileError(
            message,
            getattr(node, "line", 0),
            getattr(node, "col", 0),
            getattr(node, "source_file", ""),
        )

    def _norm(self, t: ast.JavaType) -> ast.JavaType:
        return ast.JavaType(
            PRIMITIVE_MAP.get(t.name, t.name),
            t.dims,
            t.line,
            t.col,
            t.args,
        )

    def _resolve_type(self, t: ast.JavaType, node: object, allow_void: bool = False) -> ast.JavaType:
        t = self._norm(t)
        if t.name == "void":
            if not allow_void:
                self._error("void não pode ser usado como tipo de variável", node)
            if t.args or t.dims:
                self._error("void não pode ter argumentos genéricos nem dimensões", node)
            return t

        if t.args and t.name not in (
            LIST_TYPES | MAP_TYPES | SET_TYPES | STREAM_TYPES | CLASS_TYPES
        ):
            self._error(
                f"o tipo '{t.name}' não aceita argumentos genéricos nesta versão",
                node,
            )
        if t.name in LIST_TYPES | SET_TYPES | STREAM_TYPES | CLASS_TYPES:
            if len(t.args) > 1:
                self._error(f"'{t.name}' espera no máximo um argumento genérico", node)
            for arg in t.args:
                if arg.dims == 0 and arg.name in PRIMITIVES:
                    self._error(
                        f"genéricos não aceitam o tipo primitivo '{arg.name}'",
                        node,
                    )
                self._resolve_type(arg, node, allow_void=False)
            return t
        if t.name in MAP_TYPES:
            if len(t.args) > 2:
                self._error(f"'{t.name}' espera no máximo dois argumentos genéricos", node)
            for arg in t.args:
                if arg.dims == 0 and arg.name in PRIMITIVES:
                    self._error(
                        f"genéricos não aceitam o tipo primitivo '{arg.name}'",
                        node,
                    )
                self._resolve_type(arg, node, allow_void=False)
            return t
        if t.name == "Scanner":
            if t.args:
                self._error("Scanner não aceita argumentos genéricos", node)
            return t

        if t.name in BUILTIN_INTERFACES:
            if t.args or t.dims:
                self._error(f"'{t.name}' não aceita argumentos nem dimensões", node)
            return t

        if t.dims > 0:
            base = ast.JavaType(t.name, 0, t.line, t.col, t.args)
            self._resolve_type(base, node, allow_void=False)
            return t
        if t.name in PRIMITIVES or t.name == "String":
            if t.args:
                self._error(f"'{t.name}' não aceita argumentos genéricos", node)
            return t
        if t.name in self.classes:
            if t.args:
                self._error(
                    f"a classe '{t.name}' não é genérica nesta versão",
                    node,
                )
            return t
        if t.name in EXCEPTION_TYPES:
            if t.args:
                self._error(f"'{t.name}' não aceita argumentos genéricos", node)
            return t
        if t.name in BUILTIN_CLASSES:
            self._error(f"o tipo {t.name} não pode ser declarado diretamente", node)
        self._error(f"tipo desconhecido: {t.name}", node)
        return t  # inalcançável

    def _is_numeric(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in NUMERIC

    def _is_integral(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in INTEGRAL

    def _is_reference(self, t: ast.JavaType) -> bool:
        return (
            t.dims > 0
            or t.name == "String"
            or t.name in LIBRARY_TYPES
            or t.name in EXCEPTION_TYPES
            or t.name in BUILTIN_INTERFACES
            or (t.dims == 0 and t.name in self.classes)
        )

    def _is_boolean(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name == "boolean"

    def _builtin_exception_subtype(self, child: str, parent: str) -> bool:
        if child == parent:
            return True
        current = child
        seen: set[str] = set()
        while current in EXCEPTION_PARENTS and current not in seen:
            seen.add(current)
            current = EXCEPTION_PARENTS[current]
            if current == parent:
                return True
        return False

    def _class_is_exception(self, class_name: str) -> bool:
        current: str | None = class_name
        seen: set[str] = set()
        while current and current not in seen:
            if current in EXCEPTION_TYPES:
                return True
            seen.add(current)
            info = self.classes.get(current)
            if info is None:
                return False
            current = info.parent
        return False

    def _is_exception_type(self, t: ast.JavaType) -> bool:
        if t.dims > 0:
            return False
        if t.name in EXCEPTION_TYPES:
            return True
        if t.name in self.classes:
            return self._class_is_exception(t.name)
        return False

    def _is_closeable(self, t: ast.JavaType) -> bool:
        if t.dims > 0:
            return False
        if t.name == "Scanner":
            return True
        if t.name in BUILTIN_INTERFACES:
            return True
        if t.name in self.classes:
            return self._is_subtype(t.name, "AutoCloseable")
        return False

    def _exception_supertypes(self, name: str) -> list[str]:
        chain: list[str] = []
        current: str | None = name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            chain.append(current)
            if current in EXCEPTION_TYPES:
                current = EXCEPTION_PARENTS.get(current)
            else:
                info = self.classes.get(current)
                current = info.parent if info is not None else None
        return chain

    def _common_exception_type(
        self,
        types: list[ast.JavaType],
        node: object,
    ) -> ast.JavaType:
        common = self._exception_supertypes(types[0].name)
        for other in types[1:]:
            ancestors = set(self._exception_supertypes(other.name))
            common = [name for name in common if name in ancestors]
        if not common:
            self._error("tipos do multi-catch não têm supertipo comum", node)
        return ast.JavaType(common[0])

    def _is_list_type(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in LIST_TYPES

    def _list_element_type(self, t: ast.JavaType) -> ast.JavaType:
        return t.args[0] if t.args else ast.JavaType("Object")

    def _is_map_type(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in MAP_TYPES

    def _is_set_type(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in SET_TYPES

    def _is_enum_type(self, t: ast.JavaType) -> bool:
        return (
            t.dims == 0
            and t.name in self.classes
            and self.classes[t.name].is_enum
        )

    def _is_stream_type(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in STREAM_TYPES

    def _stream_element_type(self, t: ast.JavaType) -> ast.JavaType:
        return t.args[0] if t.args else ast.JavaType("Object")

    def _is_class_type(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in CLASS_TYPES

    def _map_key_type(self, t: ast.JavaType) -> ast.JavaType:
        return t.args[0] if len(t.args) > 0 else ast.JavaType("Object")

    def _map_value_type(self, t: ast.JavaType) -> ast.JavaType:
        return t.args[1] if len(t.args) > 1 else ast.JavaType("Object")

    def _set_element_type(self, t: ast.JavaType) -> ast.JavaType:
        return t.args[0] if t.args else ast.JavaType("Object")

    def _is_null(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name == "null"

    def _compatible(self, target: ast.JavaType, source: ast.JavaType) -> bool:
        if self._is_null(source):
            return self._is_reference(target)
        if target == source:
            return True
        if self._is_list_type(target) and self._is_list_type(source):
            if not target.args or not source.args:
                return True
            return target.args == source.args
        if self._is_map_type(target) and self._is_map_type(source):
            if not target.args or not source.args:
                return True
            return target.args == source.args
        if self._is_set_type(target) and self._is_set_type(source):
            if not target.args or not source.args:
                return True
            return target.args == source.args
        if self._is_stream_type(target) and self._is_stream_type(source):
            if not target.args or not source.args:
                return True
            return target.args == source.args
        if self._is_class_type(target) and self._is_class_type(source):
            if not target.args or not source.args:
                return True
            return target.args == source.args
        if target.dims == 0 and source.dims == 0:
            if target.name == "double" and source.name in {"int", "char"}:
                return True
            if target.name == "int" and source.name == "char":
                return True
            if target.name in BUILTIN_INTERFACES and source.name in self.classes:
                return self._is_subtype(source.name, target.name)
            if target.name in self.classes and source.name in self.classes:
                return self._is_subtype(source.name, target.name)
        if (
            target.dims > 0
            and target.dims == source.dims
            and target.name in self.classes
            and source.name in self.classes
        ):
            return self._is_subtype(source.name, target.name)
        return False

    def _common_numeric(self, a: ast.JavaType, b: ast.JavaType, node: object) -> ast.JavaType:
        if not (self._is_numeric(a) and self._is_numeric(b)):
            self._error(f"operador numérico aplicado a {a} e {b}", node)
        if a.name == "double" or b.name == "double":
            return ast.DOUBLE
        return ast.INT

    def _common_type(self, a: ast.JavaType, b: ast.JavaType, node: object) -> ast.JavaType:
        if a == b:
            return a
        if self._is_null(a) and self._is_reference(b):
            return b
        if self._is_null(b) and self._is_reference(a):
            return a
        if self._is_numeric(a) and self._is_numeric(b):
            return self._common_numeric(a, b, node)
        self._error(f"tipos incompatíveis: {a} e {b}", node)
        return a  # inalcançável

    def _type_name(self, t: ast.JavaType) -> str:
        return str(t)

    # ------------------------------------------------------------------
    # Escopos
    # ------------------------------------------------------------------

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _declare(self, name: str, t: ast.JavaType, node: object) -> None:
        scope = self.scopes[-1]
        if name in scope:
            self._error(f"variável '{name}' já declarada neste escopo", node)
        scope[name] = t

    def _lookup(self, name: str) -> ast.JavaType | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _is_subtype(self, child: str, parent: str) -> bool:
        if child == parent:
            return True
        seen: set[str] = set()

        def visit(name: str) -> bool:
            if name == parent:
                return True
            if name == "Closeable" and parent == "AutoCloseable":
                return True
            if name in EXCEPTION_TYPES:
                return self._builtin_exception_subtype(name, parent)
            if name in seen:
                return False
            seen.add(name)
            info = self.classes.get(name)
            if info is None:
                return False
            if info.parent and visit(info.parent):
                return True
            for iface in info.interfaces:
                if visit(iface):
                    return True
            return False

        return visit(child)

    def _find_method_in_interface(
        self,
        interface_name: str,
        name: str,
        seen: set[str],
    ) -> tuple[MethodInfo, str] | None:
        if interface_name in seen:
            return None
        seen.add(interface_name)
        info = self.classes.get(interface_name)
        if info is None:
            return None
        if name in info.methods:
            return info.methods[name], interface_name
        if info.parent:
            found = self._find_method_in_interface(info.parent, name, seen)
            if found is not None:
                return found
        for iface in info.interfaces:
            found = self._find_method_in_interface(iface, name, seen)
            if found is not None:
                return found
        return None

    def _find_field(self, class_name: str, name: str) -> tuple[FieldInfo, str] | None:
        current: str | None = class_name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            info = self.classes.get(current)
            if info is None:
                return None
            if name in info.fields:
                return info.fields[name], current
            current = info.parent
        return None

    def _find_method(self, class_name: str, name: str) -> tuple[MethodInfo, str] | None:
        current: str | None = class_name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            info = self.classes.get(current)
            if info is None:
                return None
            if name in info.methods:
                return info.methods[name], current
            current = info.parent

        current = class_name
        seen = set()
        while current and current not in seen:
            seen.add(current)
            info = self.classes.get(current)
            if info is None:
                return None
            for iface in info.interfaces:
                found = self._find_method_in_interface(iface, name, set())
                if found is not None:
                    return found
            current = info.parent
        return None

    def _has_any_constructor(self, class_name: str) -> bool:
        current: str | None = class_name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            info = self.classes.get(current)
            if info is None:
                return False
            if info.ctors:
                return True
            current = info.parent
        return False

    def _find_concrete_method(self, class_name: str, name: str) -> MethodInfo | None:
        current: str | None = class_name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            info = self.classes.get(current)
            if info is None:
                return None
            if name in info.methods:
                method = info.methods[name]
                return None if method.is_abstract else method
            current = info.parent
        return None

    def _collect_interface_names(self, class_name: str) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        def visit(name: str) -> None:
            info = self.classes.get(name)
            if info is None:
                return
            parent_info = self.classes.get(info.parent) if info.parent else None
            if parent_info is not None and parent_info.is_interface:
                if info.parent not in seen:
                    seen.add(info.parent)
                    result.append(info.parent)
                visit(info.parent)
            for iface in info.interfaces:
                if iface in seen:
                    continue
                seen.add(iface)
                result.append(iface)
                visit(iface)
            if parent_info is not None and not parent_info.is_interface:
                visit(info.parent)

        visit(class_name)
        return result

    def _check_signature(
        self,
        child: MethodInfo,
        parent: MethodInfo,
        owner: str,
        node: object,
    ) -> None:
        if parent.is_static != child.is_static:
            self._error(
                f"método '{child.name}' muda entre static e instância em relação a '{owner}'",
                node,
            )
        if len(parent.params) != len(child.params):
            self._error(
                f"método '{child.name}' tem quantidade de parâmetros diferente de '{owner}'",
                node,
            )
        for expected, actual in zip(parent.params, child.params):
            if not self._compatible(expected, actual) or not self._compatible(actual, expected):
                self._error(
                    f"parâmetros incompatíveis em '{child.name}': {expected} vs {actual}",
                    node,
                )
        if not self._compatible(parent.return_type, child.return_type):
            self._error(
                f"retorno incompatível em '{child.name}': "
                f"{parent.return_type} vs {child.return_type}",
                node,
            )

    def _check_implementation(self, info: ClassInfo) -> None:
        if info.is_interface or info.is_enum:
            return

        required: dict[str, tuple[MethodInfo, str]] = {}
        current: str | None = info.name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            class_info = self.classes.get(current)
            if class_info is None:
                break
            for name, method in class_info.methods.items():
                if method.is_abstract and name not in required:
                    required[name] = (method, current)
            current = class_info.parent

        for iface in self._collect_interface_names(info.name):
            if iface in BUILTIN_INTERFACES:
                if (
                    not info.is_abstract
                    and self._find_concrete_method(info.name, "close") is None
                ):
                    self._error(
                        f"classe concreta '{info.name}' não implementa o método "
                        f"'close()' exigido por '{iface}'",
                        info.node,
                    )
                continue
            interface_info = self.classes[iface]
            for name, method in interface_info.methods.items():
                if name not in required:
                    required[name] = (method, iface)

        for name, (required_method, owner) in required.items():
            concrete = self._find_concrete_method(info.name, name)
            if concrete is None:
                if not info.is_abstract:
                    self._error(
                        f"classe concreta '{info.name}' não implementa o método "
                        f"'{name}' exigido por '{owner}'",
                        info.node,
                    )
                continue
            self._check_signature(concrete, required_method, owner, concrete.node)

    def _is_super_ctor_stmt(self, stmt: ast.Node) -> bool:
        return (
            isinstance(stmt, ast.ExprStmt)
            and isinstance(stmt.expr, ast.Call)
            and isinstance(stmt.expr.callee, ast.Super)
        )

    # ------------------------------------------------------------------
    # Declaração de classes
    # ------------------------------------------------------------------

    def _predeclare_class(self, cls: ast.ClassDecl) -> None:
        if cls.name in self.classes:
            self._error(f"classe '{cls.name}' já declarada", cls)
        is_interface = cls.is_interface
        is_enum = cls.is_enum
        if is_enum and (cls.extends or cls.implements):
            self._error("enum não pode usar extends/implements nesta versão", cls)
        if is_enum and "abstract" in cls.modifiers:
            self._error("enum não pode ser abstract", cls)
        if cls.is_record:
            if is_interface or is_enum:
                self._error("record não pode ser interface nem enum", cls)
            if cls.extends:
                self._error("record não pode estender outra classe", cls)
            if "abstract" in cls.modifiers:
                self._error("record não pode ser abstract", cls)
            if {"sealed", "non-sealed"} & cls.modifiers:
                self._error("record não pode ser sealed nem non-sealed", cls)
        if is_enum and {"sealed", "non-sealed"} & cls.modifiers:
            self._error("sealed enum ainda não é suportado", cls)
        if is_enum and len(set(cls.enum_constants)) != len(cls.enum_constants):
            self._error("constante de enum duplicada", cls)
        is_abstract = is_interface or (not is_enum and "abstract" in cls.modifiers)
        if is_abstract and "final" in cls.modifiers:
            self._error(
                f"'{cls.name}' não pode ser final e abstract ao mesmo tempo",
                cls,
            )
        package = cls.package or None
        qualified_name = f"{package}.{cls.name}" if package else cls.name
        self.classes[cls.name] = ClassInfo(
            name=cls.name,
            parent=cls.extends,
            interfaces=list(cls.implements),
            permits=list(cls.permits),
            node=cls,
            is_interface=is_interface,
            is_abstract=is_abstract,
            is_enum=is_enum,
            is_record=cls.is_record,
            enum_constants=list(cls.enum_constants),
            package=package,
            qualified_name=qualified_name,
        )

    def _validate_hierarchy(self) -> None:
        for info in self.classes.values():
            parent_info = None
            if info.parent:
                if info.parent == info.name:
                    self._error(f"'{info.name}' não pode herdar de si mesmo", info.node)
                if info.parent in EXCEPTION_TYPES:
                    if info.is_interface:
                        self._error(
                            f"interface '{info.name}' não pode estender uma exceção",
                            info.node,
                        )
                elif (
                    info.parent not in self.classes
                    and info.parent not in BUILTIN_INTERFACES
                ):
                    self._error(
                        f"superclasse '{info.parent}' de '{info.name}' não encontrada",
                        info.node,
                    )
                else:
                    parent_info = self.classes[info.parent]
                    if info.is_interface and not parent_info.is_interface:
                        self._error(
                            f"interface '{info.name}' só pode estender outra interface",
                            info.node,
                        )
                    if not info.is_interface and parent_info.is_interface:
                        self._error(
                            f"classe '{info.name}' não pode estender a interface '{info.parent}'",
                            info.node,
                        )

            if info.is_interface and info.interfaces:
                self._error("interface não pode usar implements", info.node)

            if len(set(info.interfaces)) != len(info.interfaces):
                self._error(f"interface repetida em '{info.name}'", info.node)

            for iface in info.interfaces:
                if iface == info.name:
                    self._error(f"'{info.name}' não pode implementar a si mesma", info.node)
                if iface in BUILTIN_INTERFACES:
                    continue
                if iface not in self.classes:
                    self._error(
                        f"interface '{iface}' implementada por '{info.name}' não encontrada",
                        info.node,
                    )
                if not self.classes[iface].is_interface:
                    self._error(
                        f"'{iface}' não é uma interface e não pode ser implementada por '{info.name}'",
                        info.node,
                    )

            # Ciclos via extends/implements.
            def visit(name: str, path: list[str]) -> None:
                if name in path:
                    self._error(f"ciclo de herança envolvendo '{name}'", info.node)
                current = self.classes.get(name)
                if current is None:
                    return
                if current.parent:
                    visit(current.parent, path + [name])
                for iface in current.interfaces:
                    visit(iface, path + [name])

            visit(info.name, [])

        self._validate_sealed()

    def _direct_subtypes(self, name: str) -> list[ClassInfo]:
        return [
            info
            for info in self.classes.values()
            if info.parent == name or name in info.interfaces
        ]

    def _validate_sealed(self) -> None:
        effective: dict[str, set[str]] = {}

        for info in self.classes.values():
            modifiers = info.node.modifiers if info.node is not None else set()
            sealed = "sealed" in modifiers
            non_sealed = "non-sealed" in modifiers

            if sealed and non_sealed:
                self._error(
                    f"'{info.name}' não pode ser sealed e non-sealed ao mesmo tempo",
                    info.node,
                )
            if info.permits and not sealed:
                self._error(
                    f"'{info.name}' usa permits, mas não é sealed",
                    info.node,
                )
            if not sealed:
                continue
            if "final" in modifiers:
                self._error(f"'{info.name}' não pode ser sealed e final", info.node)
            if len(set(info.permits)) != len(info.permits):
                self._error(f"permits repetido em '{info.name}'", info.node)

            direct = self._direct_subtypes(info.name)
            direct_names = {sub.name for sub in direct}

            if info.permits:
                for permitted in info.permits:
                    if permitted == info.name:
                        self._error(
                            f"'{info.name}' não pode permitir a si mesmo",
                            info.node,
                        )
                    if permitted not in self.classes:
                        self._error(
                            f"tipo permitido '{permitted}' de '{info.name}' não encontrado",
                            info.node,
                        )
                    if permitted not in direct_names:
                        self._error(
                            f"'{permitted}' não é subtipo direto de '{info.name}'",
                            info.node,
                        )
                effective[info.name] = set(info.permits)
            else:
                if not direct:
                    self._error(
                        f"sealed '{info.name}' precisa de permits ou de subtipos",
                        info.node,
                    )
                effective[info.name] = set(direct_names)

        for info in self.classes.values():
            supertypes = []
            if info.parent:
                supertypes.append(info.parent)
            supertypes.extend(info.interfaces)

            for super_name in supertypes:
                super_info = self.classes.get(super_name)
                if super_info is None:
                    continue
                if "sealed" in (super_info.node.modifiers if super_info.node else set()):
                    if info.name not in effective.get(super_name, set()):
                        self._error(
                            f"'{info.name}' não é permitido por '{super_name}'",
                            info.node,
                        )

            modifiers = info.node.modifiers if info.node is not None else set()
            if "non-sealed" in modifiers:
                has_sealed_super = any(
                    self.classes.get(name) is not None
                    and "sealed"
                    in (
                        self.classes[name].node.modifiers
                        if self.classes[name].node is not None
                        else set()
                    )
                    for name in supertypes
                )
                if not has_sealed_super:
                    self._error(
                        f"'{info.name}' é non-sealed, mas não herda de tipo sealed",
                        info.node,
                    )

        for name, permitted_names in effective.items():
            sealed_info = self.classes[name]
            for permitted_name in permitted_names:
                permitted = self.classes[permitted_name]
                sub_modifiers = (
                    permitted.node.modifiers if permitted.node is not None else set()
                )
                if not (
                    permitted.is_record
                    or ({"final", "sealed", "non-sealed"} & sub_modifiers)
                ):
                    self._error(
                        f"subtipo permitido '{permitted_name}' de '{name}' precisa "
                        f"ser final, sealed ou non-sealed",
                        permitted.node,
                    )
                if permitted.package != sealed_info.package:
                    self._error(
                        f"subtipo permitido '{permitted_name}' de '{name}' "
                        f"deve estar no mesmo pacote",
                        permitted.node,
                    )

    def _declare_members(self, cls: ast.ClassDecl) -> None:
        info = self.classes[cls.name]

        if info.is_enum:
            if cls.members:
                self._error(
                    "enum com campos/métodos ainda não é suportado",
                    cls.members[0],
                )
            return

        if info.is_record:
            self._declare_record_components(cls, info)

        for member in cls.members:
            if isinstance(member, ast.FieldDecl):
                if info.is_interface:
                    self._error(
                        "constantes/campos de interface ainda não são suportados",
                        member,
                    )
                if info.is_record and "static" not in member.modifiers:
                    self._error(
                        "record não pode declarar campos de instância; "
                        "use componentes do record",
                        member,
                    )
                field_type = self._resolve_type(member.type, member)
                if member.name in info.fields:
                    self._error(f"campo '{member.name}' duplicado em {cls.name}", member)
                info.fields[member.name] = FieldInfo(
                    name=member.name,
                    type=field_type,
                    is_static="static" in member.modifiers,
                    node=member,
                )
            elif isinstance(member, ast.MethodDecl):
                if member.name == cls.name:
                    self._error(
                        f"'{member.name}' parece construtor, mas tem tipo de retorno",
                        member,
                    )
                if member.name in info.methods:
                    self._error(
                        f"sobrecarga do método '{member.name}' ainda não é suportada",
                        member,
                    )
                return_type = self._resolve_type(member.return_type, member, allow_void=True)
                params = [self._resolve_type(param.type, param) for param in member.params]
                explicit_abstract = "abstract" in member.modifiers

                if info.is_interface:
                    if member.body is not None:
                        self._error(
                            f"método '{member.name}' de interface não pode ter corpo",
                            member,
                        )
                    if "static" in member.modifiers:
                        self._error(
                            "métodos static em interface ainda não são suportados",
                            member,
                        )
                    if "private" in member.modifiers:
                        self._error(
                            "métodos private em interface ainda não são suportados",
                            member,
                        )
                    if "final" in member.modifiers:
                        self._error(
                            "método de interface não pode ser final",
                            member,
                        )
                    is_abstract = True
                elif member.body is None:
                    if "static" in member.modifiers:
                        self._error(
                            f"método abstrato '{member.name}' não pode ser static",
                            member,
                        )
                    if "private" in member.modifiers:
                        self._error(
                            f"método abstrato '{member.name}' não pode ser private",
                            member,
                        )
                    if "final" in member.modifiers:
                        self._error(
                            f"método abstrato '{member.name}' não pode ser final",
                            member,
                        )
                    if not explicit_abstract:
                        self._error(
                            f"método '{member.name}' sem corpo precisa ser abstract",
                            member,
                        )
                    if not info.is_abstract:
                        self._error(
                            f"método abstrato '{member.name}' em classe não abstrata",
                            member,
                        )
                    is_abstract = True
                else:
                    if explicit_abstract:
                        self._error(
                            f"método abstrato '{member.name}' não pode ter corpo",
                            member,
                        )
                    is_abstract = False

                info.methods[member.name] = MethodInfo(
                    name=member.name,
                    return_type=return_type,
                    params=params,
                    is_static="static" in member.modifiers,
                    node=member,
                    is_abstract=is_abstract,
                )
            elif isinstance(member, ast.ConstructorDecl):
                if info.is_interface:
                    self._error("interface não pode ter construtor", member)
                if member.name != cls.name:
                    self._error(
                        f"construtor '{member.name}' não corresponde à classe '{cls.name}'",
                        member,
                    )
                params = [self._resolve_type(param.type, param) for param in member.params]
                info.ctors.append(CtorInfo(params=params, node=member))
            else:
                self._error("membro de classe não suportado", member)

        if info.is_record:
            self._validate_record_accessors(cls, info)
            self._validate_record_constructor(cls, info)

    def _declare_record_components(
        self,
        cls: ast.ClassDecl,
        info: ClassInfo,
    ) -> None:
        user_accessors = {
            member.name
            for member in cls.members
            if isinstance(member, ast.MethodDecl) and not member.params
        }

        for component in cls.components:
            if component.name in info.fields:
                self._error(
                    f"componente '{component.name}' duplicado no record {cls.name}",
                    component,
                )
            component_type = self._resolve_type(component.type, component)
            field_node = ast.FieldDecl(
                name=component.name,
                type=component_type,
                init=None,
                modifiers={"private", "final"},
                line=component.line,
                col=component.col,
            )
            info.fields[component.name] = FieldInfo(
                name=component.name,
                type=component_type,
                is_static=False,
                node=field_node,
            )
            if component.name in user_accessors:
                continue
            method_node = ast.MethodDecl(
                name=component.name,
                return_type=component_type,
                params=[],
                body=None,
                modifiers={"public"},
                line=component.line,
                col=component.col,
            )
            info.methods[component.name] = MethodInfo(
                name=component.name,
                return_type=component_type,
                params=[],
                is_static=False,
                node=method_node,
            )

    def _validate_record_accessors(
        self,
        cls: ast.ClassDecl,
        info: ClassInfo,
    ) -> None:
        for component in cls.components:
            method = info.methods.get(component.name)
            if method is None:
                continue
            field_type = info.fields[component.name].type
            if method.params or method.return_type != field_type:
                self._error(
                    f"acessador '{component.name}()' do record {cls.name} "
                    f"deve devolver {field_type}",
                    method.node,
                )

    def _validate_record_constructor(
        self,
        cls: ast.ClassDecl,
        info: ClassInfo,
    ) -> None:
        expected = [info.fields[component.name].type for component in cls.components]

        if len(info.ctors) > 1:
            self._error(
                f"record {cls.name} permite apenas o construtor canônico",
                cls,
            )
        if not info.ctors:
            params = [
                ast.Param(
                    name=component.name,
                    type=info.fields[component.name].type,
                    line=component.line,
                    col=component.col,
                )
                for component in cls.components
            ]
            node = ast.ConstructorDecl(
                name=cls.name,
                params=params,
                body=ast.Block(stmts=[], line=cls.line, col=cls.col),
                modifiers={"public"},
                line=cls.line,
                col=cls.col,
            )
            info.ctors.append(CtorInfo(params=expected, node=node))
            return

        actual = info.ctors[0].params
        if actual != expected:
            self._error(
                f"construtor de {cls.name} deve receber os componentes "
                f"({', '.join(str(t) for t in expected)})",
                info.ctors[0].node,
            )

    # ------------------------------------------------------------------
    # Checagem de classes
    # ------------------------------------------------------------------

    def _check_class(self, cls: ast.ClassDecl) -> None:
        info = self.classes[cls.name]
        if info.is_enum:
            return
        self.current_class = info
        self.current_method = None
        self.current_return_type = None
        self.in_constructor = False

        parent_info = self.classes.get(info.parent) if info.parent else None
        if parent_info is not None:
            for field in info.fields.values():
                inherited = self._find_field(info.parent, field.name)
                if inherited is not None:
                    self._error(
                        f"campo '{field.name}' já existe na superclasse '{inherited[1]}'",
                        field.node,
                    )
            for method in info.methods.values():
                inherited = self._find_method(info.parent, method.name)
                if inherited is None:
                    continue
                parent_method, owner = inherited
                if "final" in parent_method.node.modifiers:
                    self._error(
                        f"método '{method.name}' é final em '{owner}' e não pode ser sobrescrito",
                        method.node,
                    )
                self._check_signature(method, parent_method, owner, method.node)
                method.is_override = True

            # Um método declarado na classe também precisa respeitar as
            # assinaturas das interfaces implementadas.
            for iface in self._collect_interface_names(info.name):
                for method in info.methods.values():
                    found = self._find_method_in_interface(iface, method.name, set())
                    if found is None:
                        continue
                    interface_method, interface_owner = found
                    self._check_signature(
                        method,
                        interface_method,
                        interface_owner,
                        method.node,
                    )

        if not info.ctors and parent_info is not None:
            if parent_info.ctors and not any(len(ctor.params) == 0 for ctor in parent_info.ctors):
                self._error(
                    f"'{info.name}' precisa de um construtor que chame super(...), "
                    f"pois '{parent_info.name}' não tem construtor sem argumentos",
                    cls,
                )

        for member in cls.members:
            if isinstance(member, ast.FieldDecl):
                self.current_static = "static" in member.modifiers
                self.current_method = None
                self.current_return_type = None
                self.in_constructor = False
                self.scopes = []
                if member.init is not None:
                    self._push_scope()
                    init_type = self.analyze_expr(member.init)
                    self._pop_scope()
                    field_type = info.fields[member.name].type
                    if not self._compatible(field_type, init_type):
                        self._error(
                            f"não é possível inicializar campo {field_type} com {init_type}",
                            member.init,
                        )
            elif isinstance(member, ast.MethodDecl):
                method = info.methods[member.name]
                self.current_method = method
                self.current_static = method.is_static
                self.current_return_type = method.return_type
                self.in_constructor = False
                self.scopes = []
                if member.body is not None:
                    self._push_scope()
                    for param, param_type in zip(member.params, method.params):
                        self._declare(param.name, param_type, param)
                    self._check_stmt(member.body)
                    self._pop_scope()
            elif isinstance(member, ast.ConstructorDecl):
                self.current_method = None
                self.current_static = False
                self.current_return_type = ast.VOID
                self.in_constructor = True
                self.scopes = []

                stmts = member.body.stmts if isinstance(member.body, ast.Block) else []
                super_positions = [
                    index
                    for index, stmt in enumerate(stmts)
                    if self._is_super_ctor_stmt(stmt)
                ]
                if len(super_positions) > 1:
                    self._error(
                        "construtor não pode chamar super(...) mais de uma vez",
                        member,
                    )
                if super_positions and super_positions[0] != 0:
                    self._error(
                        "super(...) deve ser a primeira instrução do construtor",
                        stmts[super_positions[0]],
                    )
                if (
                    not super_positions
                    and parent_info is not None
                    and parent_info.ctors
                    and not any(len(ctor.params) == 0 for ctor in parent_info.ctors)
                ):
                    self._error(
                        f"construtor de '{info.name}' deve chamar super(...) explicitamente",
                        member,
                    )

                self._push_scope()
                # Declara os parâmetros usando os tipos resolvidos na declaração.
                for param in member.params:
                    self._declare(param.name, self._resolve_type(param.type, param), param)
                self._check_stmt(member.body)
                self._pop_scope()
                self.in_constructor = False

        self._check_implementation(info)

        self.current_class = None
        self.current_method = None
        self.current_return_type = None
        self.in_constructor = False

    def _check_mains(self) -> None:
        for info in self.classes.values():
            if info.is_interface or info.is_enum:
                continue
            if "main" not in info.methods:
                continue
            method = info.methods["main"]
            ok = (
                method.is_static
                and method.return_type == ast.VOID
                and len(method.params) == 1
                and method.params[0] == ast.JavaType("String", 1)
            )
            if not ok:
                self._error(
                    "assinatura de main inválida; esperado: public static void main(String[] args)",
                    method.node,
                )
            info.has_main = True

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def _analyze_condition(self, node: ast.Expr) -> list[tuple[str, ast.JavaType]]:
        if isinstance(node, ast.Binary) and node.op == "&&":
            left_bindings = self._analyze_condition(node.left)
            self._push_scope()
            for name, binding_type in left_bindings:
                self._declare(name, binding_type, node.left)
            right_bindings = self._analyze_condition(node.right)
            self._pop_scope()
            return left_bindings + right_bindings

        if isinstance(node, ast.Binary) and node.op == "||":
            left = self.analyze_expr(node.left)
            if not self._is_boolean(left):
                self._error(
                    f"condição do if deve ser boolean, mas é {left}",
                    node.left,
                )
            right = self.analyze_expr(node.right)
            if not self._is_boolean(right):
                self._error(
                    f"condição do if deve ser boolean, mas é {right}",
                    node.right,
                )
            return []

        if isinstance(node, ast.InstanceOf) and node.binding:
            self.analyze_expr(node)
            if not hasattr(node, "target_type"):
                self._error("pattern instanceof sem tipo resolvido", node)
            return [(node.binding, node.target_type)]

        cond = self.analyze_expr(node)
        if not self._is_boolean(cond):
            self._error(f"condição deve ser boolean, mas é {cond}", node)
        return []

    def _check_stmt(self, node: ast.Node) -> None:
        if isinstance(node, ast.Block):
            self._push_scope()
            for stmt in node.stmts:
                self._check_stmt(stmt)
            self._pop_scope()
        elif isinstance(node, ast.LocalVarDecl):
            if node.type is None:
                if node.init is None:
                    self._error(
                        "var exige um inicializador para inferir o tipo",
                        node,
                    )
                declared = self.analyze_expr(node.init)
                if self._is_null(declared):
                    self._error(
                        "var não pode ser inicializado com null",
                        node.init,
                    )
            else:
                declared = self._resolve_type(node.type, node)
                init_type = self.analyze_expr(node.init) if node.init is not None else None
                if init_type is not None and not self._compatible(declared, init_type):
                    self._error(
                        f"não é possível inicializar {declared} com {init_type}",
                        node.init,
                    )
            node.inferred_type = declared
            self._declare(node.name, declared, node)
        elif isinstance(node, ast.ExprStmt):
            self.analyze_expr(node.expr)
        elif isinstance(node, ast.If):
            self._push_scope()
            bindings = self._analyze_condition(node.cond)
            for name, binding_type in bindings:
                self._declare(name, binding_type, node.cond)
            self._check_stmt(node.then)
            self._pop_scope()
            if node.else_ is not None:
                self._check_stmt(node.else_)
        elif isinstance(node, ast.While):
            self._push_scope()
            bindings = self._analyze_condition(node.cond)
            for name, binding_type in bindings:
                self._declare(name, binding_type, node.cond)
            self.loop_depth += 1
            self._check_stmt(node.body)
            self.loop_depth -= 1
            self._pop_scope()
        elif isinstance(node, ast.DoWhile):
            self.loop_depth += 1
            self._check_stmt(node.body)
            self.loop_depth -= 1
            cond = self.analyze_expr(node.cond)
            if not self._is_boolean(cond):
                self._error(f"condição do do-while deve ser boolean, mas é {cond}", node.cond)
        elif isinstance(node, ast.Try):
            self._push_scope()
            for resource in node.resources:
                if resource.init is None:
                    self._error(
                        "recurso de try-with-resources exige inicializador",
                        resource,
                    )
                self._check_stmt(resource)
                resource_type = resource.inferred_type
                if not self._is_closeable(resource_type):
                    self._error(
                        f"recurso de try-with-resources precisa ser "
                        f"AutoCloseable, mas recebeu {resource_type}",
                        resource,
                    )
            self._check_stmt(node.body)
            self._pop_scope()

            for catch in node.catches:
                catch_types = [
                    self._resolve_type(catch_type, catch)
                    for catch_type in catch.types
                ]
                for catch_type in catch_types:
                    if not self._is_exception_type(catch_type):
                        self._error(
                            f"catch espera um tipo de exceção, mas recebeu {catch_type}",
                            catch,
                        )
                for index, first in enumerate(catch_types):
                    for second in catch_types[index + 1 :]:
                        if self._is_subtype(first.name, second.name) or self._is_subtype(
                            second.name, first.name
                        ):
                            self._error(
                                "multi-catch não pode combinar tipos relacionados: "
                                f"{first} e {second}",
                                catch,
                            )
                catch_type = self._common_exception_type(catch_types, catch)
                self._push_scope()
                self._declare(catch.name, catch_type, catch)
                self._check_stmt(catch.body)
                self._pop_scope()
            if node.finally_ is not None:
                self._check_stmt(node.finally_)
        elif isinstance(node, ast.Throw):
            value_type = self.analyze_expr(node.value)
            if not self._is_exception_type(value_type):
                self._error(
                    f"throw espera uma exceção, mas recebeu {value_type}",
                    node.value,
                )
        elif isinstance(node, ast.Yield):
            if self.switch_expr_depth == 0 or not self.yield_types_stack:
                self._error("yield só pode ser usado dentro de switch expression", node)
            value_type = self.analyze_expr(node.value)
            self.yield_types_stack[-1].append(value_type)
            node.inferred_type = value_type
        elif isinstance(node, ast.Switch):
            self._check_switch_statement(node)
        elif isinstance(node, ast.For):
            self._push_scope()
            if node.init is not None:
                if isinstance(node.init, ast.LocalVarDecl):
                    self._check_stmt(node.init)
                else:
                    self.analyze_expr(node.init.expr)
            if node.cond is not None:
                cond = self.analyze_expr(node.cond)
                if not self._is_boolean(cond):
                    self._error(f"condição do for deve ser boolean, mas é {cond}", node.cond)
            if node.update is not None:
                self.analyze_expr(node.update)
            self.loop_depth += 1
            self._check_stmt(node.body)
            self.loop_depth -= 1
            self._pop_scope()
        elif isinstance(node, ast.ForEach):
            iterable = self.analyze_expr(node.iterable)
            if self._is_list_type(iterable):
                element = self._list_element_type(iterable)
            elif self._is_set_type(iterable):
                element = self._set_element_type(iterable)
            elif iterable.dims > 0:
                element = ast.JavaType(iterable.name, iterable.dims - 1, args=iterable.args)
            else:
                self._error(
                    f"for-each espera um array ou ArrayList/List, mas recebeu {iterable}",
                    node.iterable,
                )
            if node.type is None:
                declared = element
            else:
                declared = self._resolve_type(node.type, node)
                if element.name != "Object" and not self._compatible(declared, element):
                    self._error(
                        f"não é possível iterar {iterable} como {declared}",
                        node,
                    )
            node.inferred_type = declared
            self._push_scope()
            self._declare(node.name, declared, node)
            self.loop_depth += 1
            self._check_stmt(node.body)
            self.loop_depth -= 1
            self._pop_scope()
        elif isinstance(node, ast.Return):
            if self.current_return_type is None:
                self._error("return fora de método/construtor", node)
            if self.current_return_type == ast.VOID:
                if node.value is not None:
                    self._error("método void não pode retornar valor", node.value)
            else:
                if node.value is None:
                    self._error(
                        f"método deve retornar {self.current_return_type}",
                        node,
                    )
                value_type = self.analyze_expr(node.value)
                if not self._compatible(self.current_return_type, value_type):
                    self._error(
                        f"retorno incompatível: esperado {self.current_return_type}, recebido {value_type}",
                        node.value,
                    )
        elif isinstance(node, (ast.Break, ast.Continue)):
            if isinstance(node, ast.Break):
                if self.loop_depth == 0 and self.switch_depth == 0:
                    self._error("break fora de laço/switch", node)
            else:
                if self.loop_depth == 0:
                    self._error("continue fora de laço", node)
                if self.switch_depth > 0:
                    self._error(
                        "continue dentro de switch ainda não é suportado",
                        node,
                    )
        else:
            self._error("comando não suportado", node)

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------

    def _switch_type(self, node: ast.Switch | ast.SwitchExpression) -> tuple[ast.JavaType, bool]:
        switch_type = self.analyze_expr(node.expr)
        is_enum = self._is_enum_type(switch_type)
        if not (
            self._is_integral(switch_type)
            or (switch_type.dims == 0 and switch_type.name == "String")
            or is_enum
        ):
            self._error(
                f"switch espera int, char, String ou enum, mas recebeu {switch_type}",
                node.expr,
            )
        return switch_type, is_enum

    def _check_switch_values(
        self,
        node: ast.Switch | ast.SwitchExpression,
        switch_type: ast.JavaType,
        is_enum: bool,
    ) -> tuple[bool, bool, bool]:
        seen_default = False
        has_arrow = False
        has_classic = False

        for case in node.cases:
            has_arrow = has_arrow or case.arrow
            has_classic = has_classic or not case.arrow
            if case.value is None:
                if seen_default:
                    self._error("switch com mais de um default", case)
                seen_default = True
            elif is_enum and isinstance(case.value, ast.Name):
                enum_info = self.classes[switch_type.name]
                if case.value.id not in enum_info.enum_constants:
                    self._error(
                        f"'{case.value.id}' não é constante do enum "
                        f"{switch_type.name}",
                        case.value,
                    )
                case.value.enum_owner = switch_type.name
                case.value.inferred_type = switch_type
            else:
                value_type = self.analyze_expr(case.value)
                if not self._compatible(switch_type, value_type):
                    self._error(
                        f"case incompatível com switch {switch_type}: {value_type}",
                        case.value,
                    )

        if has_arrow and has_classic:
            self._error(
                "não misture case clássico (:) com case arrow (->) no mesmo switch",
                node,
            )
        return seen_default, has_arrow, has_classic

    def _check_arrow_body(self, body: ast.Node | None, node: object) -> None:
        if body is None:
            self._error("case arrow sem corpo", node)
        if isinstance(body, ast.Block):
            self._check_stmt(body)
        elif isinstance(body, ast.Throw):
            self._check_stmt(body)
        elif isinstance(body, ast.Expr):
            self.analyze_expr(body)
        else:
            self._error("corpo de case arrow não suportado", body)

    def _check_switch_statement(self, node: ast.Switch) -> None:
        switch_type, is_enum = self._switch_type(node)
        _seen_default, has_arrow, _has_classic = self._check_switch_values(
            node, switch_type, is_enum
        )

        self.switch_depth += 1
        for case in node.cases:
            if has_arrow:
                self._check_arrow_body(case.arrow_body, case)
            else:
                for stmt in case.stmts:
                    self._check_stmt(stmt)
        self.switch_depth -= 1

    def _analyze_switch_expression(self, node: ast.SwitchExpression) -> ast.JavaType:
        switch_type, is_enum = self._switch_type(node)
        seen_default, _has_arrow, _has_classic = self._check_switch_values(
            node, switch_type, is_enum
        )
        if not seen_default:
            self._error(
                "switch expression exige default nesta versão",
                node,
            )

        self.switch_expr_depth += 1
        self.yield_types_stack.append([])
        try:
            for case in node.cases:
                if case.arrow:
                    body = case.arrow_body
                    if isinstance(body, ast.Block):
                        self._check_stmt(body)
                    elif isinstance(body, ast.Throw):
                        self._check_stmt(body)
                    elif isinstance(body, ast.Expr):
                        result_type = self.analyze_expr(body)
                        self.yield_types_stack[-1].append(result_type)
                    else:
                        self._error("corpo de case arrow inválido", case)
                else:
                    for stmt in case.stmts:
                        self._check_stmt(stmt)
            result_types = self.yield_types_stack[-1]
        finally:
            self.yield_types_stack.pop()
            self.switch_expr_depth -= 1

        if not result_types:
            self._error("switch expression não produz valor", node)
        result = result_types[0]
        for other in result_types[1:]:
            result = self._common_type(result, other, node)
        return result


        result = self._analyze_expr(node)
        node.inferred_type = result
        return result

    def analyze_expr(self, node: ast.Expr) -> ast.JavaType:
        result = self._analyze_expr(node)
        node.inferred_type = result
        return result

    def _analyze_expr(self, node: ast.Expr) -> ast.JavaType:
        if isinstance(node, ast.Literal):
            if node.kind == "int":
                return ast.INT
            if node.kind == "double":
                return ast.DOUBLE
            if node.kind == "boolean":
                return ast.BOOLEAN
            if node.kind == "char":
                if len(node.value) != 1:
                    self._error("literal char deve ter exatamente um caractere", node)
                return ast.CHAR
            if node.kind == "string":
                return ast.STRING
            if node.kind == "null":
                return ast.NULL
            self._error("literal não suportado", node)

        if isinstance(node, ast.Name):
            local = self._lookup(node.id)
            if local is not None:
                node.binding = ("local", node.id)
                return local
            if self.current_class is not None:
                found = self._find_field(self.current_class.name, node.id)
                if found is not None:
                    field, owner = found
                    if self.current_static and not field.is_static:
                        self._error(
                            f"campo de instância '{node.id}' não pode ser usado em contexto estático",
                            node,
                        )
                    node.binding = (
                        "field",
                        owner,
                        node.id,
                        field.is_static,
                    )
                    return field.type
            if node.id in self.classes or node.id in BUILTIN_CLASSES:
                node.binding = ("class", node.id)
                return ast.JavaType("__class__")
            self._error(f"símbolo não encontrado: {node.id}", node)

        if isinstance(node, ast.This):
            if self.current_static or self.current_class is None:
                self._error("'this' não pode ser usado em contexto estático", node)
            return ast.JavaType(self.current_class.name)

        if isinstance(node, ast.Super):
            if self.current_static or self.current_class is None:
                self._error("'super' não pode ser usado em contexto estático", node)
            if self.current_class.parent is None:
                self._error("'super' usado em classe sem superclasse", node)
            return ast.JavaType(self.current_class.parent)

        if isinstance(node, ast.FieldAccess):
            return self._analyze_field_access(node)

        if isinstance(node, ast.Call):
            return self._analyze_call(node)

        if isinstance(node, ast.NewObject):
            return self._analyze_new_object(node)

        if isinstance(node, ast.NewArray):
            element_type = self._resolve_type(node.element_type, node)
            if node.size is not None:
                size_type = self.analyze_expr(node.size)
                if not self._is_integral(size_type):
                    self._error("tamanho de array deve ser int", node.size)
            if node.init is not None:
                for item in node.init:
                    item_type = self.analyze_expr(item)
                    if not self._compatible(element_type, item_type):
                        self._error(
                            f"elemento {item_type} incompatível com array de {element_type}",
                            item,
                        )
            return ast.JavaType(element_type.name, element_type.dims + 1)

        if isinstance(node, ast.ArrayAccess):
            array_type = self.analyze_expr(node.array)
            if array_type.dims == 0:
                self._error(f"acesso a índice em tipo que não é array: {array_type}", node)
            index_type = self.analyze_expr(node.index)
            if not self._is_integral(index_type):
                self._error("índice de array deve ser int", node.index)
            return ast.JavaType(array_type.name, array_type.dims - 1)

        if isinstance(node, ast.Assign):
            target_type = self.analyze_expr(node.target)
            value_type = self.analyze_expr(node.value)
            if not isinstance(node.target, (ast.Name, ast.FieldAccess, ast.ArrayAccess)):
                self._error("lado esquerdo da atribuição não é atribuível", node.target)
            if isinstance(node.target, ast.Name) and getattr(node.target, "binding", ("",))[0] == "class":
                self._error("não é possível atribuir a uma classe", node.target)
            if node.op == "=":
                if not self._compatible(target_type, value_type):
                    self._error(
                        f"atribuição incompatível: {target_type} = {value_type}",
                        node,
                    )
            else:
                if target_type.name == "String" and target_type.dims == 0:
                    pass
                elif not (self._is_numeric(target_type) and self._is_numeric(value_type)):
                    self._error(
                        f"operador {node.op} exige operandos numéricos (ou String)",
                        node,
                    )
            return target_type

        if isinstance(node, ast.Binary):
            return self._analyze_binary(node)

        if isinstance(node, ast.Unary):
            operand = self.analyze_expr(node.operand)
            if node.op == "!":
                if not self._is_boolean(operand):
                    self._error("'!' exige boolean", node)
                return ast.BOOLEAN
            if node.op in {"++", "--"}:
                if not self._is_numeric(operand):
                    self._error(f"'{node.op}' exige operando numérico", node)
                if not isinstance(node.operand, (ast.Name, ast.FieldAccess, ast.ArrayAccess)):
                    self._error(f"'{node.op}' exige variável/campo/índice", node)
                return operand
            if node.op in {"+", "-"}:
                if not self._is_numeric(operand):
                    self._error(f"'{node.op}' exige operando numérico", node)
                return ast.INT if operand.name == "char" else operand
            self._error(f"operador unário não suportado: {node.op}", node)

        if isinstance(node, ast.Ternary):
            cond = self.analyze_expr(node.cond)
            if not self._is_boolean(cond):
                self._error("condição do ternário deve ser boolean", node.cond)
            then_type = self.analyze_expr(node.then)
            else_type = self.analyze_expr(node.else_)
            return self._common_type(then_type, else_type, node)

        if isinstance(node, ast.ClassLiteral):
            target = self._resolve_type(node.type, node, allow_void=True)
            node.target_type = target
            return ast.JavaType("Class", args=(target,))

        if isinstance(node, ast.SwitchExpression):
            return self._analyze_switch_expression(node)

        if isinstance(node, ast.Cast):
            return self._analyze_cast(node)

        if isinstance(node, ast.Lambda):
            self._error(
                "lambda só pode ser usada como argumento de forEach/removeIf/filter/map/..."
                ,
                node,
            )

        if isinstance(node, ast.InstanceOf):
            return self._analyze_instanceof(node)

        self._error("expressão não suportada", node)

    def _analyze_cast(self, node: ast.Cast) -> ast.JavaType:
        target = self._resolve_type(node.type, node)
        source = self.analyze_expr(node.expr)

        if target.dims > 0:
            if self._is_null(source):
                return target
            if source.dims != target.dims:
                self._error(
                    f"cast de array incompatível: {source} para {target}",
                    node,
                )
            return target

        if target.name == "String":
            if source == ast.STRING or self._is_null(source):
                return target
            self._error(f"cast para String exige String, mas recebeu {source}", node)

        if self._is_numeric(target) and self._is_numeric(source):
            return target

        if target.name in self.classes or target.name in EXCEPTION_TYPES:
            if self._is_null(source):
                return target
            if not self._is_reference(source) or source.dims > 0:
                self._error(f"cast de referência inválido: {source} para {target}", node)
            if target.name in self.classes and source.name in self.classes:
                related = (
                    target.name == source.name
                    or self._is_subtype(source.name, target.name)
                    or self._is_subtype(target.name, source.name)
                )
                if related:
                    return target
                if (
                    self.classes[target.name].is_interface
                    or self.classes[source.name].is_interface
                ):
                    return target
                self._error(f"cast impossível entre {source} e {target}", node)
            if self._is_exception_type(source) and self._is_exception_type(target):
                return target

        self._error(f"cast não suportado: {source} para {target}", node)

    def _analyze_instanceof(self, node: ast.InstanceOf) -> ast.JavaType:
        source = self.analyze_expr(node.expr)
        target = self._resolve_type(node.type, node)
        node.target_type = target

        if target.dims > 0:
            if not (self._is_reference(source) or self._is_null(source)):
                self._error(f"instanceof de array exige referência, mas recebeu {source}", node)
            return ast.BOOLEAN

        if target.name == "String":
            if not (self._is_reference(source) or self._is_null(source)):
                self._error(f"instanceof String exige referência, mas recebeu {source}", node)
            return ast.BOOLEAN

        if target.name in self.classes or target.name in EXCEPTION_TYPES:
            if not (self._is_reference(source) or self._is_null(source)):
                self._error(
                    f"instanceof exige referência, mas recebeu {source}",
                    node,
                )
            return ast.BOOLEAN

        self._error(f"instanceof não suportado para {target}", node)

    def _analyze_binary(self, node: ast.Binary) -> ast.JavaType:
        left = self.analyze_expr(node.left)
        right = self.analyze_expr(node.right)

        if node.op == "+":
            if left.name == "String" and left.dims == 0:
                return ast.STRING
            if right.name == "String" and right.dims == 0:
                return ast.STRING
            return self._common_numeric(left, right, node)

        if node.op in {"-", "*", "/", "%"}:
            return self._common_numeric(left, right, node)

        if node.op in {"<", "<=", ">", ">="}:
            if not (self._is_numeric(left) and self._is_numeric(right)):
                self._error(
                    f"comparação {node.op} exige operandos numéricos",
                    node,
                )
            return ast.BOOLEAN

        if node.op in {"==", "!="}:
            if self._is_numeric(left) and self._is_numeric(right):
                return ast.BOOLEAN
            if self._is_boolean(left) and self._is_boolean(right):
                return ast.BOOLEAN
            if (self._is_null(left) and self._is_reference(right)) or (
                self._is_null(right) and self._is_reference(left)
            ):
                return ast.BOOLEAN
            if left == right and self._is_reference(left):
                return ast.BOOLEAN
            self._error(f"comparação {node.op} entre {left} e {right}", node)

        if node.op in {"&&", "||"}:
            if not (self._is_boolean(left) and self._is_boolean(right)):
                self._error(f"operador {node.op} exige booleanos", node)
            return ast.BOOLEAN

        self._error(f"operador binário não suportado: {node.op}", node)

    def _analyze_field_access(self, node: ast.FieldAccess) -> ast.JavaType:
        target = node.target
        name = node.name

        if isinstance(target, ast.Name) and target.id == "System":
            if name == "out":
                return ast.JavaType("__System_out")
            if name == "in":
                node.php_constant = "STDIN"
                return ast.JavaType("__System_in")
            self._error(f"campo System.{name} não suportado", node)

        if isinstance(target, ast.Name) and target.id == "Math":
            if name in {"PI", "E"}:
                node.php_constant = "M_PI" if name == "PI" else "M_E"
                return ast.DOUBLE
            self._error(f"campo Math.{name} não suportado", node)

        if isinstance(target, ast.Name) and target.id == "Integer":
            if name in {"MAX_VALUE", "MIN_VALUE"}:
                node.php_constant = "PHP_INT_MAX" if name == "MAX_VALUE" else "PHP_INT_MIN"
                return ast.INT
            self._error(f"campo Integer.{name} não suportado", node)

        if isinstance(target, ast.Name) and target.id == "Double":
            constants = {
                "MAX_VALUE": "PHP_FLOAT_MAX",
                "MIN_VALUE": "PHP_FLOAT_MIN",
                "NaN": "NAN",
                "POSITIVE_INFINITY": "INF",
                "NEGATIVE_INFINITY": "-INF",
            }
            if name in constants:
                node.php_constant = constants[name]
                return ast.DOUBLE
            self._error(f"campo Double.{name} não suportado", node)

        if isinstance(target, ast.Name) and target.id in self.classes:
            info = self.classes[target.id]
            if info.is_enum:
                if name not in info.enum_constants:
                    self._error(
                        f"'{name}' não é constante do enum {target.id}",
                        node,
                    )
                node.enum_constant = True
                node.owner_class = target.id
                node.constant_name = name
                return ast.JavaType(target.id)
            found = self._find_field(target.id, name)
            if found is None:
                self._error(f"campo '{name}' não existe em {target.id}", node)
            field_info, owner = found
            node.is_static_field = True
            node.owner_class = owner
            return field_info.type

        target_type = self.analyze_expr(target)
        if target_type.dims > 0 and name == "length":
            node.is_length = True
            return ast.INT

        if target_type.dims == 0 and target_type.name in self.classes:
            found = self._find_field(target_type.name, name)
            if found is None:
                self._error(f"campo '{name}' não existe em {target_type.name}", node)
            field_info, owner = found
            if isinstance(target, ast.Super):
                node.super_field = True
            node.is_static_field = field_info.is_static
            node.owner_class = owner
            return field_info.type

        if target_type.name == "String" and target_type.dims == 0:
            self._error(
                f"'{name}' não é campo de String; use {name}() se for método",
                node,
            )

        self._error(f"acesso a campo '{name}' não suportado em {target_type}", node)

    # ------------------------------------------------------------------
    # Chamadas
    # ------------------------------------------------------------------

    def _analyze_call(self, node: ast.Call) -> ast.JavaType:
        callee = node.callee

        if isinstance(callee, ast.Super):
            return self._analyze_super_ctor(node)

        if not isinstance(callee, ast.FieldAccess):
            if isinstance(callee, ast.Name):
                return self._analyze_unqualified_call(node, callee.id)
            self._error("chamada não suportada", node)

        target = callee.target
        method = callee.name

        # System.out.println / System.out.print
        if (
            isinstance(target, ast.FieldAccess)
            and isinstance(target.target, ast.Name)
            and target.target.id == "System"
            and target.name == "out"
        ):
            if method not in {"println", "print"}:
                self._error(f"System.out.{method} não suportado", node)
            if len(node.args) > 1:
                self._error(f"System.out.{method} espera no máximo 1 argumento", node)
            for arg in node.args:
                self.analyze_expr(arg)
            node.call_kind = "system_out"
            node.method_name = method
            return ast.VOID

        # System.exit(int)
        if isinstance(target, ast.Name) and target.id == "System" and method == "exit":
            if len(node.args) != 1:
                self._error("System.exit espera 1 argumento", node)
            arg_type = self.analyze_expr(node.args[0])
            if not self._is_integral(arg_type):
                self._error("System.exit espera int", node.args[0])
            node.call_kind = "system_exit"
            return ast.VOID

        # String.valueOf(x)
        if isinstance(target, ast.Name) and target.id == "String" and method == "valueOf":
            if len(node.args) != 1:
                self._error("String.valueOf espera 1 argumento", node)
            self.analyze_expr(node.args[0])
            node.call_kind = "string_valueof"
            return ast.STRING

        # Integer.parseInt / Integer.toString
        if isinstance(target, ast.Name) and target.id == "Integer":
            if method == "parseInt":
                if len(node.args) != 1:
                    self._error("Integer.parseInt espera 1 argumento", node)
                arg_type = self.analyze_expr(node.args[0])
                if arg_type != ast.STRING:
                    self._error("Integer.parseInt espera String", node.args[0])
                node.call_kind = "integer_parseint"
                return ast.INT
            if method == "toString":
                if len(node.args) != 1:
                    self._error("Integer.toString espera 1 argumento", node)
                arg_type = self.analyze_expr(node.args[0])
                if not self._is_integral(arg_type):
                    self._error("Integer.toString espera int", node.args[0])
                node.call_kind = "integer_tostring"
                return ast.STRING
            self._error(f"Integer.{method} não suportado", node)

        # Double.parseDouble / Double.toString
        if isinstance(target, ast.Name) and target.id == "Double":
            if method == "parseDouble":
                if len(node.args) != 1:
                    self._error("Double.parseDouble espera 1 argumento", node)
                arg_type = self.analyze_expr(node.args[0])
                if arg_type != ast.STRING:
                    self._error("Double.parseDouble espera String", node.args[0])
                node.call_kind = "double_parsedouble"
                return ast.DOUBLE
            if method == "toString":
                if len(node.args) != 1:
                    self._error("Double.toString espera 1 argumento", node)
                arg_type = self.analyze_expr(node.args[0])
                if not self._is_numeric(arg_type):
                    self._error("Double.toString espera número", node.args[0])
                node.call_kind = "double_tostring"
                return ast.STRING
            self._error(f"Double.{method} não suportado", node)

        # Math.*
        if isinstance(target, ast.Name) and target.id == "Math":
            return self._analyze_math_call(node, method)

        # super.metodo(...)
        if isinstance(target, ast.Super):
            return self._analyze_super_call(node, method)

        # Chamada estática de classe do usuário: Classe.metodo(...)
        if isinstance(target, ast.Name) and target.id in self.classes:
            return self._analyze_static_call(node, target.id, method)

        # Chamada de instância ou método de String
        target_type = self.analyze_expr(target)

        if target_type.name == "String" and target_type.dims == 0:
            return self._analyze_string_call(node, method)

        if self._is_list_type(target_type):
            return self._analyze_list_call(node, method, target_type)

        if self._is_map_type(target_type):
            return self._analyze_map_call(node, method, target_type)

        if self._is_set_type(target_type):
            return self._analyze_set_call(node, method, target_type)

        if self._is_stream_type(target_type):
            return self._analyze_stream_call(node, method, target_type)

        if self._is_class_type(target_type):
            return self._analyze_class_call(node, method)

        if target_type.dims == 0 and target_type.name == "Scanner":
            return self._analyze_scanner_call(node, method)

        if self._is_exception_type(target_type):
            return self._analyze_exception_call(node, method)

        if target_type.dims == 0 and target_type.name in self.classes:
            found = self._find_method(target_type.name, method)
            if found is None:
                self._error(f"método '{method}' não existe em {target_type.name}", node)
            method_info, owner = found
            self._check_call_args(method, node.args, method_info.params, node)
            node.call_kind = "instance"
            node.method_name = method
            node.owner_class = owner
            return method_info.return_type

        self._error(f"chamada de método em tipo não suportado: {target_type}", node)

    def _analyze_super_ctor(self, node: ast.Call) -> ast.JavaType:
        if (
            not self.in_constructor
            or self.current_class is None
            or self.current_class.parent is None
        ):
            self._error(
                "super(...) só pode ser chamado no construtor de uma subclasse",
                node,
            )
        parent_name = self.current_class.parent
        arg_types = [self.analyze_expr(arg) for arg in node.args]

        if parent_name in EXCEPTION_TYPES:
            if len(arg_types) > 1:
                self._error(f"'{parent_name}' espera no máximo uma mensagem", node)
            if arg_types and arg_types[0] not in {ast.STRING, ast.INT}:
                self._error(
                    f"'{parent_name}' espera String (ou int para código)",
                    node.args[0],
                )
            node.call_kind = "super_ctor"
            node.owner_class = parent_name
            return ast.VOID

        parent_info = self.classes[parent_name]
        if not parent_info.ctors:
            if arg_types:
                self._error(
                    f"'{parent_info.name}' não declara construtor com "
                    f"{len(arg_types)} argumento(s)",
                    node,
                )
        else:
            matched = False
            for ctor in parent_info.ctors:
                if len(ctor.params) != len(arg_types):
                    continue
                if all(self._compatible(p, a) for p, a in zip(ctor.params, arg_types)):
                    matched = True
                    break
            if not matched:
                self._error(
                    f"nenhum construtor de '{parent_info.name}' aceita "
                    f"({', '.join(str(t) for t in arg_types)})",
                    node,
                )

        node.call_kind = "super_ctor"
        node.owner_class = parent_info.name
        return ast.VOID

    def _analyze_super_call(self, node: ast.Call, method: str) -> ast.JavaType:
        if self.current_static or self.current_class is None or self.current_class.parent is None:
            self._error("super.metodo(...) só pode ser usado em contexto de instância", node)
        found = self._find_method(self.current_class.parent, method)
        if found is None:
            self._error(
                f"método '{method}' não existe na superclasse "
                f"'{self.current_class.parent}'",
                node,
            )
        method_info, owner = found
        self._check_call_args(method, node.args, method_info.params, node)
        node.call_kind = "super_method"
        node.method_name = method
        node.owner_class = owner
        return method_info.return_type

    def _analyze_unqualified_call(self, node: ast.Call, method: str) -> ast.JavaType:
        if self.current_class is None:
            self._error(f"método '{method}' não encontrado", node)
        found = self._find_method(self.current_class.name, method)
        if found is None:
            self._error(f"método '{method}' não encontrado", node)
        method_info, owner = found
        self._check_call_args(method, node.args, method_info.params, node)
        if self.current_static and not method_info.is_static:
            self._error(
                f"método de instância '{method}' não pode ser chamado em contexto estático",
                node,
            )
        node.call_kind = "self_static" if method_info.is_static else "self_instance"
        node.method_name = method
        node.owner_class = owner
        return method_info.return_type

    def _analyze_static_call(self, node: ast.Call, class_name: str, method: str) -> ast.JavaType:
        found = self._find_method(class_name, method)
        if found is None:
            self._error(f"método '{method}' não existe em {class_name}", node)
        method_info, _owner = found
        if not method_info.is_static:
            self._error(f"método '{method}' não é estático", node)
        self._check_call_args(method, node.args, method_info.params, node)
        node.call_kind = "static"
        node.method_name = method
        node.owner_class = class_name
        return method_info.return_type

    def _analyze_math_call(self, node: ast.Call, method: str) -> ast.JavaType:
        arg_types = [self.analyze_expr(arg) for arg in node.args]
        for arg_type, arg in zip(arg_types, node.args):
            if not self._is_numeric(arg_type):
                self._error(f"Math.{method} espera número", arg)

        if method == "abs":
            if len(arg_types) != 1:
                self._error("Math.abs espera 1 argumento", node)
            node.call_kind = "math"
            node.method_name = method
            return ast.INT if arg_types[0].name == "char" else arg_types[0]

        if method in {"min", "max"}:
            if len(arg_types) != 2:
                self._error(f"Math.{method} espera 2 argumentos", node)
            node.call_kind = "math"
            node.method_name = method
            return self._common_numeric(arg_types[0], arg_types[1], node)

        if method in {"sqrt", "floor", "ceil"}:
            if len(arg_types) != 1:
                self._error(f"Math.{method} espera 1 argumento", node)
            node.call_kind = "math"
            node.method_name = method
            return ast.DOUBLE

        if method == "pow":
            if len(arg_types) != 2:
                self._error("Math.pow espera 2 argumentos", node)
            node.call_kind = "math"
            node.method_name = method
            return ast.DOUBLE

        if method == "round":
            if len(arg_types) != 1:
                self._error("Math.round espera 1 argumento", node)
            node.call_kind = "math"
            node.method_name = method
            return ast.INT

        if method == "random":
            if len(arg_types) != 0:
                self._error("Math.random não espera argumentos", node)
            node.call_kind = "math"
            node.method_name = method
            return ast.DOUBLE

        self._error(f"Math.{method} não suportado", node)

    def _analyze_string_call(self, node: ast.Call, method: str) -> ast.JavaType:
        arg_types = [self.analyze_expr(arg) for arg in node.args]

        def arity(expected: int) -> None:
            if len(arg_types) != expected:
                self._error(
                    f"String.{method} espera {expected} argumento(s), recebeu {len(arg_types)}",
                    node,
                )

        def expect(index: int, allowed: set[str], label: str) -> None:
            if index >= len(arg_types):
                return
            t = arg_types[index]
            if t.dims > 0 or t.name not in allowed:
                self._error(f"String.{method} espera {label}", node.args[index])

        if method == "length":
            arity(0)
            result = ast.INT
        elif method == "charAt":
            arity(1)
            expect(0, {"int", "char"}, "int")
            result = ast.CHAR
        elif method == "substring":
            if len(arg_types) not in {1, 2}:
                self._error("String.substring espera 1 ou 2 argumentos", node)
            for i in range(len(arg_types)):
                expect(i, {"int", "char"}, "int")
            result = ast.STRING
        elif method == "equals":
            arity(1)
            result = ast.BOOLEAN
        elif method == "equalsIgnoreCase":
            arity(1)
            expect(0, {"String"}, "String")
            result = ast.BOOLEAN
        elif method in {"toUpperCase", "toLowerCase", "trim"}:
            arity(0)
            result = ast.STRING
        elif method == "indexOf":
            arity(1)
            expect(0, {"String", "char"}, "String ou char")
            result = ast.INT
        elif method == "isEmpty":
            arity(0)
            result = ast.BOOLEAN
        elif method == "contains":
            arity(1)
            expect(0, {"String"}, "String")
            result = ast.BOOLEAN
        elif method in {"startsWith", "endsWith"}:
            arity(1)
            expect(0, {"String"}, "String")
            result = ast.BOOLEAN
        elif method == "replace":
            arity(2)
            expect(0, {"String", "char"}, "String ou char")
            expect(1, {"String", "char"}, "String ou char")
            result = ast.STRING
        elif method == "split":
            arity(1)
            expect(0, {"String"}, "String")
            result = ast.JavaType("String", 1)
        elif method == "toString":
            arity(0)
            result = ast.STRING
        elif method == "compareTo":
            arity(1)
            expect(0, {"String"}, "String")
            result = ast.INT
        else:
            self._error(f"método de String não suportado: {method}", node)

        node.call_kind = "string_method"
        node.method_name = method
        return result

    def _analyze_lambda(
        self,
        node: ast.Expr,
        param_types: list[ast.JavaType],
        expected_return: ast.JavaType | None = None,
    ) -> ast.JavaType:
        if not isinstance(node, ast.Lambda):
            self._error("esperava uma lambda", node)
        if len(node.params) != len(param_types):
            self._error(
                f"lambda espera {len(param_types)} parâmetro(s), "
                f"recebeu {len(node.params)}",
                node,
            )
        if isinstance(node.body, ast.Block):
            self._error(
                "lambda com bloco ainda não é suportada; use expressão",
                node,
            )

        self._push_scope()
        for name, param_type in zip(node.params, param_types):
            self._declare(name, param_type, node)
        body_type = self.analyze_expr(node.body)
        self._pop_scope()

        if expected_return is not None and not self._compatible(expected_return, body_type):
            self._error(
                f"lambda deve retornar {expected_return}, mas retorna {body_type}",
                node.body,
            )
        node.param_types = param_types
        node.body_type = body_type
        return body_type

    def _analyze_list_call(
        self,
        node: ast.Call,
        method: str,
        target_type: ast.JavaType,
    ) -> ast.JavaType:
        element = self._list_element_type(target_type)

        if method == "stream":
            if node.args:
                self._error("stream não espera argumentos", node)
            node.call_kind = "list_stream"
            node.method_name = "stream"
            return ast.JavaType("Stream", args=(element,))

        if method in {"forEach", "removeIf"}:
            if len(node.args) != 1:
                self._error(f"{target_type.name}.{method} espera 1 argumento", node)
            expected = ast.BOOLEAN if method == "removeIf" else None
            self._analyze_lambda(node.args[0], [element], expected)
            node.call_kind = "list_for_each" if method == "forEach" else "list_remove_if"
            node.method_name = method
            return ast.VOID if method == "forEach" else ast.BOOLEAN

        arg_types = [self.analyze_expr(arg) for arg in node.args]

        def arity(expected: int) -> None:
            if len(arg_types) != expected:
                self._error(
                    f"{target_type.name}.{method} espera {expected} argumento(s), "
                    f"recebeu {len(arg_types)}",
                    node,
                )

        def check_element(index: int) -> None:
            if index >= len(arg_types):
                return
            actual = arg_types[index]
            if element.name != "Object" and not self._compatible(element, actual):
                self._error(
                    f"{target_type.name}.{method} espera {element}, recebeu {actual}",
                    node.args[index],
                )

        if method == "add":
            if len(arg_types) == 1:
                check_element(0)
                node.call_kind = "list_add"
                node.method_name = "add"
                return ast.BOOLEAN
            if len(arg_types) == 2:
                if not self._is_integral(arg_types[0]):
                    self._error(f"{target_type.name}.add espera int no índice", node.args[0])
                check_element(1)
                node.call_kind = "list_add_at"
                node.method_name = "addAt"
                return ast.VOID
            self._error(f"{target_type.name}.add espera 1 ou 2 argumentos", node)

        if method == "get":
            arity(1)
            if not self._is_integral(arg_types[0]):
                self._error(f"{target_type.name}.get espera int", node.args[0])
            node.call_kind = "list_get"
            node.method_name = "get"
            return element

        if method == "set":
            arity(2)
            if not self._is_integral(arg_types[0]):
                self._error(f"{target_type.name}.set espera int no índice", node.args[0])
            check_element(1)
            node.call_kind = "list_set"
            node.method_name = "set"
            return element

        if method == "size":
            arity(0)
            node.call_kind = "list_size"
            node.method_name = "size"
            return ast.INT

        if method == "isEmpty":
            arity(0)
            node.call_kind = "list_is_empty"
            node.method_name = "isEmpty"
            return ast.BOOLEAN

        if method == "contains":
            arity(1)
            check_element(0)
            node.call_kind = "list_contains"
            node.method_name = "contains"
            return ast.BOOLEAN

        if method == "remove":
            arity(1)
            if self._is_integral(arg_types[0]):
                node.call_kind = "list_remove_at"
                node.method_name = "removeAt"
                return element
            check_element(0)
            node.call_kind = "list_remove_value"
            node.method_name = "removeValue"
            return ast.BOOLEAN

        if method == "clear":
            arity(0)
            node.call_kind = "list_clear"
            node.method_name = "clear"
            return ast.VOID

        if method == "indexOf":
            arity(1)
            check_element(0)
            node.call_kind = "list_index_of"
            node.method_name = "indexOf"
            return ast.INT

        if method == "toString":
            arity(0)
            node.call_kind = "list_to_string"
            node.method_name = "toString"
            return ast.STRING

        self._error(f"método {target_type.name}.{method} ainda não é suportado", node)

    def _analyze_map_call(
        self,
        node: ast.Call,
        method: str,
        target_type: ast.JavaType,
    ) -> ast.JavaType:
        key_type = self._map_key_type(target_type)
        value_type = self._map_value_type(target_type)
        arg_types = [self.analyze_expr(arg) for arg in node.args]

        def arity(expected: int) -> None:
            if len(arg_types) != expected:
                self._error(
                    f"{target_type.name}.{method} espera {expected} argumento(s), "
                    f"recebeu {len(arg_types)}",
                    node,
                )

        def check(index: int, expected: ast.JavaType) -> None:
            if index >= len(arg_types):
                return
            actual = arg_types[index]
            if expected.name != "Object" and not self._compatible(expected, actual):
                self._error(
                    f"{target_type.name}.{method} espera {expected}, recebeu {actual}",
                    node.args[index],
                )

        if method == "put":
            arity(2)
            check(0, key_type)
            check(1, value_type)
            node.call_kind = "map_put"
            node.method_name = "put"
            return value_type

        if method == "get":
            arity(1)
            check(0, key_type)
            node.call_kind = "map_get"
            node.method_name = "get"
            return value_type

        if method == "containsKey":
            arity(1)
            check(0, key_type)
            node.call_kind = "map_contains_key"
            node.method_name = "containsKey"
            return ast.BOOLEAN

        if method == "containsValue":
            arity(1)
            check(0, value_type)
            node.call_kind = "map_contains_value"
            node.method_name = "containsValue"
            return ast.BOOLEAN

        if method == "remove":
            arity(1)
            check(0, key_type)
            node.call_kind = "map_remove"
            node.method_name = "remove"
            return value_type

        if method == "size":
            arity(0)
            node.call_kind = "map_size"
            node.method_name = "size"
            return ast.INT

        if method == "isEmpty":
            arity(0)
            node.call_kind = "map_is_empty"
            node.method_name = "isEmpty"
            return ast.BOOLEAN

        if method == "clear":
            arity(0)
            node.call_kind = "map_clear"
            node.method_name = "clear"
            return ast.VOID

        if method == "keySet":
            arity(0)
            node.call_kind = "map_key_set"
            node.method_name = "keySet"
            return ast.JavaType("HashSet", args=(key_type,))

        if method == "values":
            arity(0)
            node.call_kind = "map_values"
            node.method_name = "values"
            return ast.JavaType("ArrayList", args=(value_type,))

        if method == "toString":
            arity(0)
            node.call_kind = "map_to_string"
            node.method_name = "toString"
            return ast.STRING

        self._error(f"método {target_type.name}.{method} ainda não é suportado", node)

    def _analyze_set_call(
        self,
        node: ast.Call,
        method: str,
        target_type: ast.JavaType,
    ) -> ast.JavaType:
        element = self._set_element_type(target_type)

        if method == "stream":
            if node.args:
                self._error("stream não espera argumentos", node)
            node.call_kind = "set_stream"
            node.method_name = "stream"
            return ast.JavaType("Stream", args=(element,))

        if method == "forEach":
            if len(node.args) != 1:
                self._error(f"{target_type.name}.forEach espera 1 argumento", node)
            self._analyze_lambda(node.args[0], [element])
            node.call_kind = "set_for_each"
            node.method_name = "forEach"
            return ast.VOID

        arg_types = [self.analyze_expr(arg) for arg in node.args]

        def arity(expected: int) -> None:
            if len(arg_types) != expected:
                self._error(
                    f"{target_type.name}.{method} espera {expected} argumento(s), "
                    f"recebeu {len(arg_types)}",
                    node,
                )

        def check(index: int) -> None:
            if index >= len(arg_types):
                return
            actual = arg_types[index]
            if element.name != "Object" and not self._compatible(element, actual):
                self._error(
                    f"{target_type.name}.{method} espera {element}, recebeu {actual}",
                    node.args[index],
                )

        if method == "add":
            arity(1)
            check(0)
            node.call_kind = "set_add"
            node.method_name = "add"
            return ast.BOOLEAN

        if method == "contains":
            arity(1)
            check(0)
            node.call_kind = "set_contains"
            node.method_name = "contains"
            return ast.BOOLEAN

        if method == "remove":
            arity(1)
            check(0)
            node.call_kind = "set_remove"
            node.method_name = "remove"
            return ast.BOOLEAN

        if method == "size":
            arity(0)
            node.call_kind = "set_size"
            node.method_name = "size"
            return ast.INT

        if method == "isEmpty":
            arity(0)
            node.call_kind = "set_is_empty"
            node.method_name = "isEmpty"
            return ast.BOOLEAN

        if method == "clear":
            arity(0)
            node.call_kind = "set_clear"
            node.method_name = "clear"
            return ast.VOID

        if method == "toString":
            arity(0)
            node.call_kind = "set_to_string"
            node.method_name = "toString"
            return ast.STRING

        self._error(f"método {target_type.name}.{method} ainda não é suportado", node)

    def _is_collectors_tolist(self, expr: ast.Expr) -> bool:
        return (
            isinstance(expr, ast.Call)
            and isinstance(expr.callee, ast.FieldAccess)
            and isinstance(expr.callee.target, ast.Name)
            and expr.callee.target.id == "Collectors"
            and expr.callee.name == "toList"
            and not expr.args
        )

    def _analyze_stream_call(
        self,
        node: ast.Call,
        method: str,
        target_type: ast.JavaType,
    ) -> ast.JavaType:
        element = self._stream_element_type(target_type)

        if method in {"filter", "forEach", "anyMatch", "allMatch", "noneMatch"}:
            if len(node.args) != 1:
                self._error(f"Stream.{method} espera 1 argumento", node)
            expected = ast.BOOLEAN if method != "forEach" else None
            self._analyze_lambda(node.args[0], [element], expected)
            node.call_kind = f"stream_{method}"
            node.method_name = method
            if method == "filter":
                return ast.JavaType("Stream", args=(element,))
            if method == "forEach":
                return ast.VOID
            return ast.BOOLEAN

        if method == "map":
            if len(node.args) != 1:
                self._error("Stream.map espera 1 argumento", node)
            result_type = self._analyze_lambda(node.args[0], [element], None)
            node.call_kind = "stream_map"
            node.method_name = "map"
            return ast.JavaType("Stream", args=(result_type,))

        if method == "collect":
            if len(node.args) != 1 or not self._is_collectors_tolist(node.args[0]):
                self._error(
                    "Stream.collect só suporta Collectors.toList()",
                    node,
                )
            node.call_kind = "stream_collect"
            node.method_name = "collect"
            return ast.JavaType("ArrayList", args=(element,))

        if method == "count":
            if node.args:
                self._error("Stream.count não espera argumentos", node)
            node.call_kind = "stream_count"
            node.method_name = "count"
            return ast.INT

        if method == "sorted":
            if node.args:
                self._error("Stream.sorted não espera argumentos", node)
            node.call_kind = "stream_sorted"
            node.method_name = "sorted"
            return ast.JavaType("Stream", args=(element,))

        if method == "limit":
            if len(node.args) != 1:
                self._error("Stream.limit espera 1 argumento", node)
            limit_type = self.analyze_expr(node.args[0])
            if not self._is_integral(limit_type):
                self._error("Stream.limit espera int", node.args[0])
            node.call_kind = "stream_limit"
            node.method_name = "limit"
            return ast.JavaType("Stream", args=(element,))

        if method == "toList":
            if node.args:
                self._error("Stream.toList não espera argumentos", node)
            node.call_kind = "stream_to_list"
            node.method_name = "toList"
            return ast.JavaType("ArrayList", args=(element,))

        self._error(f"método Stream.{method} ainda não é suportado", node)

    def _analyze_class_call(self, node: ast.Call, method: str) -> ast.JavaType:
        if method in {"getName", "getSimpleName", "getCanonicalName", "toString"}:
            if node.args:
                self._error(f"Class.{method} não espera argumentos", node)
            node.call_kind = "class_method"
            node.method_name = method
            return ast.STRING
        if method == "isInstance":
            if len(node.args) != 1:
                self._error("Class.isInstance espera 1 argumento", node)
            self.analyze_expr(node.args[0])
            node.call_kind = "class_method"
            node.method_name = method
            return ast.BOOLEAN
        self._error(f"método Class.{method} ainda não é suportado", node)

    def _analyze_exception_call(self, node: ast.Call, method: str) -> ast.JavaType:
        if node.args:
            self._error(f"método de exceção '{method}' não espera argumentos", node)
        returns = {
            "getMessage": ast.STRING,
            "getLocalizedMessage": ast.STRING,
            "getCode": ast.INT,
            "printStackTrace": ast.VOID,
            "toString": ast.STRING,
        }
        if method not in returns:
            self._error(f"método de exceção '{method}' ainda não é suportado", node)
        node.call_kind = "exception_method"
        node.method_name = method
        return returns[method]

    def _analyze_scanner_call(self, node: ast.Call, method: str) -> ast.JavaType:
        if node.args:
            self._error(f"Scanner.{method} não espera argumentos", node)
        returns = {
            "nextInt": ast.INT,
            "nextDouble": ast.DOUBLE,
            "next": ast.STRING,
            "nextLine": ast.STRING,
            "hasNext": ast.BOOLEAN,
            "hasNextInt": ast.BOOLEAN,
            "hasNextDouble": ast.BOOLEAN,
            "close": ast.VOID,
        }
        if method not in returns:
            self._error(f"método Scanner.{method} ainda não é suportado", node)
        node.call_kind = "scanner"
        node.method_name = method
        return returns[method]

    def _check_call_args(
        self,
        name: str,
        args: list[ast.Expr],
        expected: list[ast.JavaType],
        node: object,
    ) -> None:
        if len(args) != len(expected):
            self._error(
                f"método '{name}' espera {len(expected)} argumento(s), recebeu {len(args)}",
                node,
            )
        for i, (arg, expected_type) in enumerate(zip(args, expected)):
            actual = self.analyze_expr(arg)
            if not self._compatible(expected_type, actual):
                self._error(
                    f"argumento {i + 1} de '{name}': esperado {expected_type}, recebido {actual}",
                    arg,
                )

    # ------------------------------------------------------------------
    # new
    # ------------------------------------------------------------------

    def _analyze_new_object(self, node: ast.NewObject) -> ast.JavaType:
        class_name = node.class_name

        if class_name in LIST_TYPES:
            type_args = tuple(self._resolve_type(arg, node) for arg in node.type_args)
            arg_types = [self.analyze_expr(arg) for arg in node.args]
            if arg_types and not (
                len(arg_types) == 1 and self._is_integral(arg_types[0])
            ):
                self._error(
                    f"'{class_name}' espera nenhum argumento ou uma capacidade int",
                    node,
                )
            return ast.JavaType("ArrayList", args=type_args)

        if class_name in MAP_TYPES:
            type_args = tuple(self._resolve_type(arg, node) for arg in node.type_args)
            if node.args:
                self._error(f"'{class_name}' não espera argumentos neste subconjunto", node)
            return ast.JavaType("HashMap", args=type_args)

        if class_name in SET_TYPES:
            type_args = tuple(self._resolve_type(arg, node) for arg in node.type_args)
            if node.args:
                self._error(f"'{class_name}' não espera argumentos neste subconjunto", node)
            return ast.JavaType("HashSet", args=type_args)

        if class_name == "Scanner":
            if len(node.args) > 1:
                self._error("Scanner espera no máximo um argumento (System.in)", node)
            if node.args:
                source = self.analyze_expr(node.args[0])
                if source.name != "__System_in":
                    self._error("Scanner espera System.in", node.args[0])
            return ast.JavaType("Scanner")

        if class_name in EXCEPTION_TYPES:
            if len(node.args) > 1:
                self._error(f"'{class_name}' espera no máximo uma mensagem", node)
            if node.args:
                message_type = self.analyze_expr(node.args[0])
                if message_type not in {ast.STRING, ast.INT}:
                    self._error(
                        f"'{class_name}' espera String (ou int para código) como argumento",
                        node.args[0],
                    )
            return ast.JavaType(class_name)

        if class_name not in self.classes:
            self._error(f"classe '{class_name}' não encontrada", node)
        info = self.classes[class_name]
        if info.is_interface:
            self._error(f"não é possível instanciar a interface '{class_name}'", node)
        if info.is_enum:
            self._error(f"não é possível instanciar o enum '{class_name}'", node)
        if info.is_abstract:
            self._error(f"não é possível instanciar a classe abstrata '{class_name}'", node)
        arg_types = [self.analyze_expr(arg) for arg in node.args]

        if not info.ctors:
            if arg_types:
                self._error(
                    f"'{class_name}' não declara construtor com {len(arg_types)} argumento(s)",
                    node,
                )
            return ast.JavaType(class_name)

        for ctor in info.ctors:
            if len(ctor.params) != len(arg_types):
                continue
            if all(self._compatible(p, a) for p, a in zip(ctor.params, arg_types)):
                node.ctor_params = ctor.params
                return ast.JavaType(class_name)

        self._error(
            f"nenhum construtor de '{class_name}' aceita ({', '.join(str(t) for t in arg_types)})",
            node,
        )
        return ast.JavaType(class_name)
