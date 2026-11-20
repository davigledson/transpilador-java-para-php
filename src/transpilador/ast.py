"""AST do subconjunto de Java suportado pelo transpilador.

Os nós são dataclasses simples. A análise semântica anota tipos
dinamicamente nas expressões (``expr.inferred_type``) e resoluções
(``expr.binding``, ``expr.call_kind`` etc.) para o gerador de código.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any


class Node:
    """Marcador base para todos os nós."""


class Expr(Node):
    """Marcador base para expressões."""


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class JavaType(Node):
    name: str
    dims: int = 0
    line: int = 0
    col: int = 0
    args: tuple[JavaType, ...] = ()

    def __str__(self) -> str:
        base = self.name + "[]" * self.dims
        if self.args:
            base += "<" + ", ".join(str(arg) for arg in self.args) + ">"
        return base

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, JavaType)
            and self.name == other.name
            and self.dims == other.dims
            and self.args == other.args
        )

    def __hash__(self) -> int:
        return hash((self.name, self.dims, self.args))


INT = JavaType("int")
DOUBLE = JavaType("double")
BOOLEAN = JavaType("boolean")
CHAR = JavaType("char")
STRING = JavaType("String")
VOID = JavaType("void")
NULL = JavaType("null")


# ---------------------------------------------------------------------------
# Estrutura
# ---------------------------------------------------------------------------


@dataclass
class Program(Node):
    classes: list[ClassDecl]
    package: str | None = None
    imports: list[str] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class ClassDecl(Node):
    name: str
    extends: str | None
    members: list[Node]
    implements: list[str] = field(default_factory=list)
    permits: list[str] = field(default_factory=list)
    modifiers: set[str] = field(default_factory=set)
    is_interface: bool = False
    is_enum: bool = False
    is_record: bool = False
    is_annotation: bool = False
    enum_constants: list[str] = field(default_factory=list)
    components: list["RecordComponent"] = field(default_factory=list)
    annotation_elements: list["AnnotationElement"] = field(default_factory=list)
    package: str | None = None
    imports: list[str] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class AnnotationElement(Node):
    name: str
    type: JavaType
    default: Expr | None = None
    line: int = 0
    col: int = 0


@dataclass
class RecordComponent(Node):
    name: str
    type: JavaType
    line: int = 0
    col: int = 0


@dataclass
class FieldDecl(Node):
    name: str
    type: JavaType
    init: Expr | None
    modifiers: set[str] = field(default_factory=set)
    line: int = 0
    col: int = 0


@dataclass
class MethodDecl(Node):
    name: str
    return_type: JavaType
    params: list[Param]
    body: Block | None
    modifiers: set[str] = field(default_factory=set)
    line: int = 0
    col: int = 0


@dataclass
class ConstructorDecl(Node):
    name: str
    params: list[Param]
    body: Block
    modifiers: set[str] = field(default_factory=set)
    line: int = 0
    col: int = 0


@dataclass
class Param(Node):
    name: str
    type: JavaType
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


@dataclass
class Block(Node):
    stmts: list[Node]
    line: int = 0
    col: int = 0


@dataclass
class LocalVarDecl(Node):
    name: str
    type: JavaType | None
    init: Expr | None
    line: int = 0
    col: int = 0


@dataclass
class ExprStmt(Node):
    expr: Expr
    line: int = 0
    col: int = 0


@dataclass
class If(Node):
    cond: Expr
    then: Node
    else_: Node | None
    line: int = 0
    col: int = 0


@dataclass
class While(Node):
    cond: Expr
    body: Node
    line: int = 0
    col: int = 0


@dataclass
class DoWhile(Node):
    body: Node
    cond: Expr
    line: int = 0
    col: int = 0


@dataclass
class For(Node):
    init: Node | None
    cond: Expr | None
    update: Expr | None
    body: Node
    line: int = 0
    col: int = 0


@dataclass
class ForEach(Node):
    name: str
    type: JavaType | None
    iterable: Expr
    body: Node
    line: int = 0
    col: int = 0


@dataclass
class Return(Node):
    value: Expr | None
    line: int = 0
    col: int = 0


@dataclass
class Break(Node):
    line: int = 0
    col: int = 0


@dataclass
class Continue(Node):
    line: int = 0
    col: int = 0


@dataclass
class Catch(Node):
    types: list[JavaType]
    name: str
    body: Block
    line: int = 0
    col: int = 0

    @property
    def type(self) -> JavaType:
        """Primeiro tipo do catch (compatibilidade com catch simples)."""
        return self.types[0]


@dataclass
class Try(Node):
    body: Block
    catches: list[Catch]
    finally_: Block | None
    resources: list[LocalVarDecl] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class Throw(Node):
    value: Expr
    line: int = 0
    col: int = 0


@dataclass
class TypePattern(Node):
    type: JavaType
    name: str
    line: int = 0
    col: int = 0


@dataclass
class SwitchCase(Node):
    value: Expr | None
    stmts: list[Node] = field(default_factory=list)
    arrow_body: Node | None = None
    arrow: bool = False
    pattern: TypePattern | None = None
    guard: Expr | None = None
    line: int = 0
    col: int = 0


@dataclass
class Switch(Node):
    expr: Expr
    cases: list[SwitchCase]
    line: int = 0
    col: int = 0


@dataclass
class SwitchExpression(Expr):
    expr: Expr
    cases: list[SwitchCase]
    line: int = 0
    col: int = 0


@dataclass
class Yield(Node):
    value: Expr
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Expressões
# ---------------------------------------------------------------------------


@dataclass
class Literal(Expr):
    value: Any
    kind: str  # int | double | boolean | char | string | null
    line: int = 0
    col: int = 0


@dataclass
class Name(Expr):
    id: str
    line: int = 0
    col: int = 0


@dataclass
class This(Expr):
    line: int = 0
    col: int = 0


@dataclass
class Super(Expr):
    line: int = 0
    col: int = 0


@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr
    line: int = 0
    col: int = 0


@dataclass
class Unary(Expr):
    op: str
    operand: Expr
    prefix: bool = True
    line: int = 0
    col: int = 0


@dataclass
class Assign(Expr):
    op: str  # = | += | -= | *= | /=
    target: Expr
    value: Expr
    line: int = 0
    col: int = 0


@dataclass
class Ternary(Expr):
    cond: Expr
    then: Expr
    else_: Expr
    line: int = 0
    col: int = 0


@dataclass
class FieldAccess(Expr):
    target: Expr
    name: str
    line: int = 0
    col: int = 0


@dataclass
class Call(Expr):
    callee: Expr
    args: list[Expr]
    line: int = 0
    col: int = 0


@dataclass
class NewObject(Expr):
    class_name: str
    args: list[Expr]
    type_args: tuple[JavaType, ...] = ()
    line: int = 0
    col: int = 0


@dataclass
class NewArray(Expr):
    element_type: JavaType
    size: Expr | None
    init: list[Expr] | None
    line: int = 0
    col: int = 0


@dataclass
class ArrayAccess(Expr):
    array: Expr
    index: Expr
    line: int = 0
    col: int = 0


@dataclass
class Cast(Expr):
    type: JavaType
    expr: Expr
    line: int = 0
    col: int = 0


@dataclass
class InstanceOf(Expr):
    expr: Expr
    type: JavaType
    binding: str | None = None
    line: int = 0
    col: int = 0


@dataclass
class Lambda(Expr):
    params: list[str]
    body: Expr | Block
    line: int = 0
    col: int = 0


@dataclass
class ClassLiteral(Expr):
    type: JavaType
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Utilitário para debug/testes
# ---------------------------------------------------------------------------


def annotate_source(node: Any, filename: str) -> None:
    """Marca recursivamente os nós com o arquivo de origem."""

    if dataclasses.is_dataclass(node):
        setattr(node, "source_file", filename)
        for f in dataclasses.fields(node):
            if f.name in {"line", "col"}:
                continue
            annotate_source(getattr(node, f.name), filename)
    elif isinstance(node, (list, tuple)):
        for item in node:
            annotate_source(item, filename)


def ast_to_dict(node: Any) -> Any:
    """Converte a AST em uma estrutura serializável (para ``--dump-ast``)."""

    if isinstance(node, JavaType):
        return {"_type": "JavaType", "name": node.name, "dims": node.dims}
    if isinstance(node, list):
        return [ast_to_dict(item) for item in node]
    if isinstance(node, tuple):
        return [ast_to_dict(item) for item in node]
    if isinstance(node, set):
        return sorted(node)
    if dataclasses.is_dataclass(node):
        result: dict[str, Any] = {"_node": type(node).__name__}
        for f in dataclasses.fields(node):
            if f.name in {"line", "col"}:
                continue
            value = getattr(node, f.name)
            if value is None and f.name not in {"init", "size", "else_", "value"}:
                continue
            result[f.name] = ast_to_dict(value)
        return result
    return node
