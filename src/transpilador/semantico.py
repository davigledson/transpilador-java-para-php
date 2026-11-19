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


@dataclass
class CtorInfo:
    params: list[ast.JavaType]
    node: ast.ConstructorDecl


@dataclass
class ClassInfo:
    name: str
    fields: dict[str, FieldInfo] = field(default_factory=dict)
    methods: dict[str, MethodInfo] = field(default_factory=dict)
    ctors: list[CtorInfo] = field(default_factory=list)
    node: ast.ClassDecl | None = None
    has_main: bool = False


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.classes: dict[str, ClassInfo] = {}
        self.program: ast.Program | None = None

        self.current_class: ClassInfo | None = None
        self.current_method: MethodInfo | None = None
        self.current_static = False
        self.current_return_type: ast.JavaType | None = None
        self.loop_depth = 0

        self.scopes: list[dict[str, ast.JavaType]] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def analyze(self, program: ast.Program) -> None:
        self.program = program
        for cls in program.classes:
            self._predeclare_class(cls)
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
        )

    def _norm(self, t: ast.JavaType) -> ast.JavaType:
        return ast.JavaType(PRIMITIVE_MAP.get(t.name, t.name), t.dims)

    def _resolve_type(self, t: ast.JavaType, node: object, allow_void: bool = False) -> ast.JavaType:
        t = self._norm(t)
        if t.name == "void":
            if not allow_void:
                self._error("void não pode ser usado como tipo de variável", node)
            return t
        if t.dims > 0:
            base = ast.JavaType(t.name)
            self._resolve_type(base, node, allow_void=False)
            return t
        if t.name in PRIMITIVES or t.name == "String":
            return t
        if t.name in self.classes:
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
        return t.dims > 0 or t.name == "String" or (t.dims == 0 and t.name in self.classes)

    def _is_boolean(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name == "boolean"

    def _is_null(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name == "null"

    def _compatible(self, target: ast.JavaType, source: ast.JavaType) -> bool:
        if self._is_null(source):
            return self._is_reference(target)
        if target == source:
            return True
        if target.dims == 0 and source.dims == 0:
            if target.name == "double" and source.name in {"int", "char"}:
                return True
            if target.name == "int" and source.name == "char":
                return True
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

    # ------------------------------------------------------------------
    # Declaração de classes
    # ------------------------------------------------------------------

    def _predeclare_class(self, cls: ast.ClassDecl) -> None:
        if cls.name in self.classes:
            self._error(f"classe '{cls.name}' já declarada", cls)
        if cls.extends:
            self._error("herança (extends) ainda não é suportada nesta versão", cls)
        if cls.implements:
            self._error("interfaces (implements) ainda não são suportadas nesta versão", cls)
        if "abstract" in cls.modifiers:
            self._error("classes abstratas ainda não são suportadas nesta versão", cls)
        self.classes[cls.name] = ClassInfo(name=cls.name, node=cls)

    def _declare_members(self, cls: ast.ClassDecl) -> None:
        info = self.classes[cls.name]

        for member in cls.members:
            if isinstance(member, ast.FieldDecl):
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
                info.methods[member.name] = MethodInfo(
                    name=member.name,
                    return_type=return_type,
                    params=params,
                    is_static="static" in member.modifiers,
                    node=member,
                )
            elif isinstance(member, ast.ConstructorDecl):
                if member.name != cls.name:
                    self._error(
                        f"construtor '{member.name}' não corresponde à classe '{cls.name}'",
                        member,
                    )
                params = [self._resolve_type(param.type, param) for param in member.params]
                info.ctors.append(CtorInfo(params=params, node=member))
            else:
                self._error("membro de classe não suportado", member)

    # ------------------------------------------------------------------
    # Checagem de classes
    # ------------------------------------------------------------------

    def _check_class(self, cls: ast.ClassDecl) -> None:
        info = self.classes[cls.name]
        self.current_class = info
        self.current_method = None
        self.current_return_type = None

        for member in cls.members:
            if isinstance(member, ast.FieldDecl):
                self.current_static = "static" in member.modifiers
                self.current_method = None
                self.current_return_type = None
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
                self.scopes = []
                self._push_scope()
                for param, param_type in zip(member.params, method.params):
                    self._declare(param.name, param_type, param)
                self._check_stmt(member.body)
                self._pop_scope()
            elif isinstance(member, ast.ConstructorDecl):
                self.current_method = None
                self.current_static = False
                self.current_return_type = ast.VOID
                self.scopes = []
                self._push_scope()
                # Declara os parâmetros usando os tipos resolvidos na declaração.
                for param in member.params:
                    self._declare(param.name, self._resolve_type(param.type, param), param)
                self._check_stmt(member.body)
                self._pop_scope()

        self.current_class = None
        self.current_method = None
        self.current_return_type = None

    def _check_mains(self) -> None:
        for info in self.classes.values():
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

    def _check_stmt(self, node: ast.Node) -> None:
        if isinstance(node, ast.Block):
            self._push_scope()
            for stmt in node.stmts:
                self._check_stmt(stmt)
            self._pop_scope()
        elif isinstance(node, ast.LocalVarDecl):
            declared = self._resolve_type(node.type, node)
            init_type = self.analyze_expr(node.init) if node.init is not None else None
            if init_type is not None and not self._compatible(declared, init_type):
                self._error(
                    f"não é possível inicializar {declared} com {init_type}",
                    node.init,
                )
            self._declare(node.name, declared, node)
        elif isinstance(node, ast.ExprStmt):
            self.analyze_expr(node.expr)
        elif isinstance(node, ast.If):
            cond = self.analyze_expr(node.cond)
            if not self._is_boolean(cond):
                self._error(f"condição do if deve ser boolean, mas é {cond}", node.cond)
            self._check_stmt(node.then)
            if node.else_ is not None:
                self._check_stmt(node.else_)
        elif isinstance(node, ast.While):
            cond = self.analyze_expr(node.cond)
            if not self._is_boolean(cond):
                self._error(f"condição do while deve ser boolean, mas é {cond}", node.cond)
            self.loop_depth += 1
            self._check_stmt(node.body)
            self.loop_depth -= 1
        elif isinstance(node, ast.DoWhile):
            self.loop_depth += 1
            self._check_stmt(node.body)
            self.loop_depth -= 1
            cond = self.analyze_expr(node.cond)
            if not self._is_boolean(cond):
                self._error(f"condição do do-while deve ser boolean, mas é {cond}", node.cond)
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
            if iterable.dims == 0:
                self._error(
                    f"for-each espera um array, mas recebeu {iterable}",
                    node.iterable,
                )
            element = ast.JavaType(iterable.name, iterable.dims - 1)
            declared = self._resolve_type(node.type, node)
            if not self._compatible(declared, element):
                self._error(
                    f"não é possível iterar {iterable} como {declared}",
                    node,
                )
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
            if self.loop_depth == 0:
                self._error("break/continue fora de laço", node)
        else:
            self._error("comando não suportado", node)

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------

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
                field = self.current_class.fields.get(node.id)
                if field is not None:
                    if self.current_static and not field.is_static:
                        self._error(
                            f"campo de instância '{node.id}' não pode ser usado em contexto estático",
                            node,
                        )
                    node.binding = (
                        "field",
                        self.current_class.name,
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

        if isinstance(node, ast.Cast):
            target = self._resolve_type(node.type, node)
            self.analyze_expr(node.expr)
            return target

        if isinstance(node, ast.InstanceOf):
            self.analyze_expr(node.expr)
            self._resolve_type(node.type, node)
            return ast.BOOLEAN

        self._error("expressão não suportada", node)

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
            field_info = info.fields.get(name)
            if field_info is None:
                self._error(f"campo '{name}' não existe em {target.id}", node)
            node.is_static_field = True
            node.owner_class = target.id
            return field_info.type

        target_type = self.analyze_expr(target)
        if target_type.dims > 0 and name == "length":
            node.is_length = True
            return ast.INT

        if target_type.dims == 0 and target_type.name in self.classes:
            info = self.classes[target_type.name]
            field_info = info.fields.get(name)
            if field_info is None:
                self._error(f"campo '{name}' não existe em {target_type.name}", node)
            node.is_static_field = field_info.is_static
            node.owner_class = target_type.name
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

        # Chamada estática de classe do usuário: Classe.metodo(...)
        if isinstance(target, ast.Name) and target.id in self.classes:
            return self._analyze_static_call(node, target.id, method)

        # Chamada de instância ou método de String
        target_type = self.analyze_expr(target)

        if target_type.name == "String" and target_type.dims == 0:
            return self._analyze_string_call(node, method)

        if target_type.dims == 0 and target_type.name in self.classes:
            info = self.classes[target_type.name]
            method_info = info.methods.get(method)
            if method_info is None:
                self._error(f"método '{method}' não existe em {target_type.name}", node)
            self._check_call_args(method, node.args, method_info.params, node)
            node.call_kind = "instance"
            node.method_name = method
            node.owner_class = target_type.name
            return method_info.return_type

        self._error(f"chamada de método em tipo não suportado: {target_type}", node)

    def _analyze_unqualified_call(self, node: ast.Call, method: str) -> ast.JavaType:
        if self.current_class is None:
            self._error(f"método '{method}' não encontrado", node)
        method_info = self.current_class.methods.get(method)
        if method_info is None:
            self._error(f"método '{method}' não encontrado", node)
        self._check_call_args(method, node.args, method_info.params, node)
        if self.current_static and not method_info.is_static:
            self._error(
                f"método de instância '{method}' não pode ser chamado em contexto estático",
                node,
            )
        node.call_kind = "self_static" if method_info.is_static else "self_instance"
        node.method_name = method
        node.owner_class = self.current_class.name
        return method_info.return_type

    def _analyze_static_call(self, node: ast.Call, class_name: str, method: str) -> ast.JavaType:
        info = self.classes[class_name]
        method_info = info.methods.get(method)
        if method_info is None:
            self._error(f"método '{method}' não existe em {class_name}", node)
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
        if class_name not in self.classes:
            self._error(f"classe '{class_name}' não encontrada", node)
        info = self.classes[class_name]
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
