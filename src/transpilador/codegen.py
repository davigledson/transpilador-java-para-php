"""Gerador de código PHP a partir da AST tipada."""

from __future__ import annotations

from . import ast
from .erros import TranspileError
from .semantico import EXCEPTION_TYPES, ClassInfo


TYPE_MAP = {
    "int": "int",
    "double": "float",
    "boolean": "bool",
    "char": "string",
    "String": "string",
    "void": "void",
    "ArrayList": "JArrayList",
    "List": "JArrayList",
    "Scanner": "JScanner",
    "HashMap": "JHashMap",
    "Map": "JHashMap",
    "HashSet": "JHashSet",
    "Set": "JHashSet",
    "Stream": "JStream",
    "Class": "JClass",
    "Throwable": "\\Throwable",
    "Exception": "\\Exception",
    "RuntimeException": "\\RuntimeException",
    "IllegalArgumentException": "\\InvalidArgumentException",
    "IllegalStateException": "\\RuntimeException",
    "ArithmeticException": "\\DivisionByZeroError",
    "NullPointerException": "\\Error",
    "IndexOutOfBoundsException": "\\OutOfRangeException",
    "IOException": "\\RuntimeException",
}

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

RUNTIME_USES = (
    "JSystem",
    "JString",
    "JArrayList",
    "JStream",
    "JHashMap",
    "JHashSet",
    "JScanner",
    "JCast",
    "JClass",
)


def php_name(qualified_name: str) -> str:
    return qualified_name.replace(".", "\\")


class PhpEmitter:
    def __init__(self, classes: dict[str, ClassInfo]) -> None:
        self.classes = classes
        self.lines: list[str] = []
        self.indent = 0
        self.current_class: str | None = None
        self.switch_counter = 0
        self.current_package: str | None = None
        self.current_imports: list[str] = []
        self.switch_result_vars: list[str] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def emit(self, program: ast.Program) -> str:
        self.lines = []
        self.current_package = program.package
        self.current_imports = list(program.imports)
        self._emit_header(program, "require_once __DIR__ . '/runtime/bootstrap.php';")

        for cls in self.ordered_classes(program.classes):
            self.emit_class(cls)

        main_class = next(
            (cls for cls in program.classes if self.classes[cls.name].has_main),
            None,
        )
        if main_class is not None:
            self.emit_entrypoint(main_class)

        return "\n".join(self.lines).rstrip() + "\n"

    def emit_module(self, program: ast.Program, bootstrap_depth: int = 0) -> str:
        """Gera um arquivo PHP de módulo para o modo projeto.

        ``bootstrap_depth`` é a quantidade de diretórios entre o arquivo e a
        raiz de saída (onde fica ``bootstrap.php``).
        """

        self.lines = []
        self.switch_counter = 0
        self.current_package = program.package
        self.current_imports = list(program.imports)
        if bootstrap_depth <= 0:
            require_line = "require_once __DIR__ . '/bootstrap.php';"
        else:
            require_line = (
                f"require_once dirname(__DIR__, {bootstrap_depth}) . '/bootstrap.php';"
            )
        self._emit_header(program, require_line)

        for cls in self.ordered_classes(program.classes):
            self.emit_class(cls)

        return "\n".join(self.lines).rstrip() + "\n"

    def _emit_header(self, program: ast.Program, require_line: str) -> None:
        self.line("<?php")
        self.line("declare(strict_types=1);")
        if program.package:
            self.line(f"namespace {php_name(program.package)};")

        uses = set(self.php_uses(program))
        if program.package:
            uses.update(RUNTIME_USES)
        if uses:
            self.line()
            for item in sorted(uses):
                self.line(f"use {item};")

        self.line()
        self.line(require_line)
        self.line()

    def php_uses(self, program: ast.Program) -> list[str]:
        current_package = program.package
        result: list[str] = []
        for imported in program.imports:
            if imported.endswith(".*"):
                prefix = imported[:-2]
                for info in self.classes.values():
                    if info.package == prefix and info.package != current_package:
                        result.append(php_name(info.qualified_name))
                continue
            simple = imported.rsplit(".", 1)[-1]
            info = self.classes.get(simple)
            if (
                info is not None
                and info.qualified_name == imported
                and info.package != current_package
            ):
                result.append(php_name(info.qualified_name))
        return sorted(set(result))

    def ordered_classes(self, classes: list[ast.ClassDecl]) -> list[ast.ClassDecl]:
        """Emite dependências antes: pai/interface antes do filho.

        O PHP declara classes/interfaces na ordem do arquivo; inverter a ordem
        pode gerar "class not found" em tempo de carga.
        """

        by_name = {cls.name: cls for cls in classes}
        result: list[ast.ClassDecl] = []
        seen: set[str] = set()
        visiting: set[str] = set()

        def visit(cls: ast.ClassDecl) -> None:
            if cls.name in seen or cls.name in visiting:
                return
            visiting.add(cls.name)
            if cls.extends and cls.extends in by_name:
                visit(by_name[cls.extends])
            for iface in cls.implements:
                if iface in by_name:
                    visit(by_name[iface])
            visiting.remove(cls.name)
            seen.add(cls.name)
            result.append(cls)

        for cls in classes:
            visit(cls)
        return result

    # ------------------------------------------------------------------
    # Saída e indentação
    # ------------------------------------------------------------------

    def line(self, text: str = "") -> None:
        self.lines.append(("    " * self.indent + text) if text else "")

    def error(self, message: str, node: object) -> None:
        raise TranspileError(
            message,
            getattr(node, "line", 0),
            getattr(node, "col", 0),
            getattr(node, "source_file", ""),
        )

    # ------------------------------------------------------------------
    # Tipos e valores padrão
    # ------------------------------------------------------------------

    def php_type(self, t: ast.JavaType, nullable: bool = True) -> str:
        if t.dims > 0:
            base = "array"
        elif t.name in TYPE_MAP:
            base = TYPE_MAP[t.name]
        elif t.name == "null":
            base = "mixed"
        elif t.name in self.classes:
            base = self.php_class_name(t.name)
        else:
            base = t.name

        if not nullable or base in {"void", "mixed"}:
            return base

        is_ref = (
            t.dims > 0
            or t.name == "String"
            or t.name in self.classes
            or t.name in LIBRARY_TYPES
            or t.name in EXCEPTION_TYPES
        )
        return f"?{base}" if is_ref else base

    def php_exception_name(self, name: str) -> str:
        return TYPE_MAP.get(name, "\\" + name)

    def php_class_name(self, name: str) -> str:
        if name in EXCEPTION_TYPES:
            return self.php_exception_name(name)
        info = self.classes.get(name)
        if info is None or not info.package:
            return name
        if info.package == self.current_package:
            return name
        if info.qualified_name in self.current_imports:
            return name
        for imported in self.current_imports:
            if imported.endswith(".*") and imported[:-2] == info.package:
                return name
        return "\\" + php_name(info.qualified_name)

    def default_value(self, t: ast.JavaType) -> str:
        if t.dims > 0:
            return "null"
        if t.name == "int":
            return "0"
        if t.name == "double":
            return "0.0"
        if t.name == "boolean":
            return "false"
        if t.name == "char":
            return '"\\0"'
        return "null"

    # ------------------------------------------------------------------
    # Classes
    # ------------------------------------------------------------------

    def emit_class(self, cls: ast.ClassDecl) -> None:
        self.current_class = cls.name
        if cls.is_enum:
            self.line(f"enum {cls.name}")
            self.line("{")
            self.indent += 1
            for constant in cls.enum_constants:
                self.line(f"case {constant};")
            self.indent -= 1
            self.line("}")
            self.line()
            self.current_class = None
            return
        if cls.is_interface:
            kind = "interface"
        elif "abstract" in cls.modifiers:
            kind = "abstract class"
        else:
            kind = "class"
        extends_name = cls.extends
        if extends_name in EXCEPTION_TYPES:
            extends_name = self.php_exception_name(extends_name)
        elif extends_name in self.classes:
            extends_name = self.php_class_name(extends_name)
        extends = f" extends {extends_name}" if extends_name else ""
        implements_list = ", ".join(self.php_class_name(i) for i in cls.implements)
        implements = f" implements {implements_list}" if implements_list else ""
        self.line(f"{kind} {cls.name}{extends}{implements}")
        self.line("{")
        self.indent += 1

        for member in cls.members:
            if isinstance(member, ast.FieldDecl):
                self.emit_field(member)
            elif isinstance(member, ast.ConstructorDecl):
                self.emit_constructor(member)
            elif isinstance(member, ast.MethodDecl):
                self.emit_method(member)

        self.indent -= 1
        self.line("}")
        self.line()
        self.current_class = None

    def emit_field(self, field: ast.FieldDecl) -> None:
        if "private" in field.modifiers:
            visibility = "private"
        elif "protected" in field.modifiers:
            visibility = "protected"
        else:
            visibility = "public"

        static = "static " if "static" in field.modifiers else ""
        type_str = self.php_type(field.type)
        init = self.emit_expr(field.init) if field.init is not None else self.default_value(field.type)
        self.line(f"{visibility} {static}{type_str} ${field.name} = {init};")

    def emit_constructor(self, ctor: ast.ConstructorDecl) -> None:
        if "private" in ctor.modifiers:
            visibility = "private"
        elif "protected" in ctor.modifiers:
            visibility = "protected"
        else:
            visibility = "public"

        params = ", ".join(
            f"{self.php_type(param.type)} ${param.name}" for param in ctor.params
        )
        self.line(f"{visibility} function __construct({params})")
        self.line("{")
        self.indent += 1
        if self.current_class is not None:
            info = self.classes[self.current_class]
            has_explicit_super = any(
                isinstance(stmt, ast.ExprStmt)
                and isinstance(stmt.expr, ast.Call)
                and isinstance(stmt.expr.callee, ast.Super)
                for stmt in ctor.body.stmts
            )
            if (
                not has_explicit_super
                and info.parent is not None
                and self.has_any_constructor(info.parent)
            ):
                self.line("parent::__construct();")
            for stmt in ctor.body.stmts:
                if (
                    self.is_super_ctor_stmt(stmt)
                    and info.parent is not None
                    and not self.has_any_constructor(info.parent)
                ):
                    # super() é válido em Java mesmo quando o pai tem o
                    # construtor implícito, mas o PHP não tem __construct
                    # para chamar.
                    continue
                self.emit_stmt(stmt)
        else:
            self.emit_block_contents(ctor.body)
        self.indent -= 1
        self.line("}")

    def is_super_ctor_stmt(self, stmt: ast.Node) -> bool:
        return (
            isinstance(stmt, ast.ExprStmt)
            and isinstance(stmt.expr, ast.Call)
            and isinstance(stmt.expr.callee, ast.Super)
        )

    def emit_method(self, method: ast.MethodDecl) -> None:
        if "private" in method.modifiers:
            visibility = "private"
        elif "protected" in method.modifiers:
            visibility = "protected"
        else:
            visibility = "public"

        static = "static " if "static" in method.modifiers else ""
        params = ", ".join(
            f"{self.php_type(param.type)} ${param.name}" for param in method.params
        )
        return_type = self.php_type(method.return_type, nullable=True)

        is_interface = (
            self.current_class is not None
            and self.classes[self.current_class].is_interface
        )
        if method.body is None:
            if is_interface:
                self.line(f"public function {method.name}({params}): {return_type};")
            else:
                self.line(f"abstract public function {method.name}({params}): {return_type};")
            self.line()
            return

        self.line(f"{visibility} {static}function {method.name}({params}): {return_type}")
        self.line("{")
        self.indent += 1
        self.emit_block_contents(method.body)
        self.indent -= 1
        self.line("}")

        # Facilita JString::valueOf/println de objetos.
        if method.name == "toString" and not method.params and method.return_type == ast.STRING:
            self.line()
            self.line(f"{visibility} function __toString(): string")
            self.line("{")
            self.indent += 1
            self.line("return $this->toString();")
            self.indent -= 1
            self.line("}")
        self.line()

    def emit_entrypoint(self, cls: ast.ClassDecl) -> None:
        self.line(
            "if (PHP_SAPI === 'cli' && isset($_SERVER['SCRIPT_FILENAME']) "
            "&& realpath($_SERVER['SCRIPT_FILENAME']) === __FILE__) {"
        )
        self.indent += 1
        self.line(f"{cls.name}::main(array_slice($argv, 1));")
        self.indent -= 1
        self.line("}")

    def has_any_constructor(self, class_name: str) -> bool:
        if class_name in EXCEPTION_TYPES:
            return True
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

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def emit_block_contents(self, block: ast.Block) -> None:
        for stmt in block.stmts:
            self.emit_stmt(stmt)

    def emit_stmt(self, node: ast.Node) -> None:
        if isinstance(node, ast.Block):
            self.line("{")
            self.indent += 1
            self.emit_block_contents(node)
            self.indent -= 1
            self.line("}")
        elif isinstance(node, ast.LocalVarDecl):
            init = self.emit_expr(node.init) if node.init is not None else "null"
            self.line(f"${node.name} = {init};")
        elif isinstance(node, ast.ExprStmt):
            self.line(f"{self.emit_expr(node.expr)};")
        elif isinstance(node, ast.If):
            self.line(f"if ({self.emit_expr(node.cond)}) {{")
            self.indent += 1
            self.emit_nested_body(node.then)
            self.indent -= 1
            if node.else_ is not None:
                self.line("} else {")
                self.indent += 1
                self.emit_nested_body(node.else_)
                self.indent -= 1
            self.line("}")
        elif isinstance(node, ast.While):
            self.line(f"while ({self.emit_expr(node.cond)}) {{")
            self.indent += 1
            self.emit_nested_body(node.body)
            self.indent -= 1
            self.line("}")
        elif isinstance(node, ast.DoWhile):
            self.line("do {")
            self.indent += 1
            self.emit_nested_body(node.body)
            self.indent -= 1
            self.line(f"}} while ({self.emit_expr(node.cond)});")
        elif isinstance(node, ast.Try):
            self.line("try {")
            self.indent += 1
            self.emit_block_contents(node.body)
            self.indent -= 1
            for catch in node.catches:
                catch_type = self.php_class_name(catch.type.name)
                self.line(f"}} catch ({catch_type} ${catch.name}) {{")
                self.indent += 1
                self.emit_block_contents(catch.body)
                self.indent -= 1
            if node.finally_ is not None:
                self.line("} finally {")
                self.indent += 1
                self.emit_block_contents(node.finally_)
                self.indent -= 1
            self.line("}")
        elif isinstance(node, ast.Throw):
            self.line(f"throw {self.emit_expr(node.value)};")
        elif isinstance(node, ast.Switch):
            if any(case.arrow for case in node.cases):
                self.emit_arrow_switch_statement(node)
            else:
                temp = f"$__switch{self.switch_counter}"
                self.switch_counter += 1
                self.line(f"{temp} = {self.emit_expr(node.expr)};")
                self.line("switch (true) {")
                self.indent += 1
                for case in node.cases:
                    if case.value is None:
                        self.line("default:")
                    else:
                        value = self.emit_expr(case.value)
                        self.line(f"case ({temp} === {value}):")
                    self.indent += 1
                    for stmt in case.stmts:
                        self.emit_stmt(stmt)
                    self.indent -= 1
                self.indent -= 1
                self.line("}")
        elif isinstance(node, ast.Yield):
            if not self.switch_result_vars:
                self.error("yield fora de switch expression no gerador", node)
            self.line(f"{self.switch_result_vars[-1]} = {self.emit_expr(node.value)};")
            self.line("break;")
        elif isinstance(node, ast.For):
            init = self.emit_for_init(node.init)
            cond = self.emit_expr(node.cond) if node.cond is not None else "true"
            update = self.emit_expr(node.update) if node.update is not None else ""
            self.line(f"for ({init}; {cond}; {update}) {{")
            self.indent += 1
            self.emit_nested_body(node.body)
            self.indent -= 1
            self.line("}")
        elif isinstance(node, ast.ForEach):
            iterable = self.emit_expr(node.iterable)
            self.line(f"foreach ({iterable} as ${node.name}) {{")
            self.indent += 1
            self.emit_nested_body(node.body)
            self.indent -= 1
            self.line("}")
        elif isinstance(node, ast.Return):
            if node.value is None:
                self.line("return;")
            else:
                self.line(f"return {self.emit_expr(node.value)};")
        elif isinstance(node, ast.Break):
            self.line("break;")
        elif isinstance(node, ast.Continue):
            self.line("continue;")
        else:
            self.error("comando não suportado pelo gerador", node)

    def emit_nested_body(self, node: ast.Node) -> None:
        if isinstance(node, ast.Block):
            self.emit_block_contents(node)
        else:
            self.emit_stmt(node)

    def emit_arrow_switch_statement(self, node: ast.Switch) -> None:
        temp = f"$__switch{self.switch_counter}"
        self.switch_counter += 1
        self.line(f"{temp} = {self.emit_expr(node.expr)};")

        value_cases = [case for case in node.cases if case.value is not None]
        default_case = next((case for case in node.cases if case.value is None), None)

        for index, case in enumerate(value_cases):
            value = self.emit_expr(case.value)
            prefix = "if" if index == 0 else "} else if"
            self.line(f"{prefix} ({temp} === {value}) {{")
            self.indent += 1
            self.emit_arrow_body(case.arrow_body)
            self.indent -= 1

        if default_case is not None:
            if value_cases:
                self.line("} else {")
                self.indent += 1
                self.emit_arrow_body(default_case.arrow_body)
                self.indent -= 1
                self.line("}")
            else:
                self.emit_arrow_body(default_case.arrow_body)
        elif value_cases:
            self.line("}")

    def emit_arrow_body(self, body: ast.Node | None) -> None:
        if isinstance(body, ast.Block):
            self.emit_stmt(body)
        elif isinstance(body, ast.Expr):
            self.line(f"{self.emit_expr(body)};")
        elif isinstance(body, ast.Throw):
            self.emit_stmt(body)
        else:
            self.error("corpo de case arrow não suportado no gerador", body)

    def emit_switch_expression(self, node: ast.SwitchExpression) -> str:
        temp = f"$__switch{self.switch_counter}"
        self.switch_counter += 1
        result = f"$__switchResult{self.switch_counter}"
        self.switch_counter += 1

        self.line(f"{temp} = {self.emit_expr(node.expr)};")
        self.line(f"{result} = null;")
        self.line("switch (true) {")
        self.indent += 1
        for case in node.cases:
            if case.value is None:
                self.line("default:")
            else:
                value = self.emit_expr(case.value)
                self.line(f"case ({temp} === {value}):")
            self.indent += 1
            self.switch_result_vars.append(result)
            if case.arrow:
                body = case.arrow_body
                if isinstance(body, ast.Expr):
                    self.line(f"{result} = {self.emit_expr(body)};")
                elif isinstance(body, (ast.Block, ast.Throw)):
                    self.emit_stmt(body)
                else:
                    self.error("case arrow inválido no switch expression", case)
            else:
                for stmt in case.stmts:
                    self.emit_stmt(stmt)
            self.switch_result_vars.pop()
            self.line("break;")
            self.indent -= 1
        self.indent -= 1
        self.line("}")
        return result

    def emit_for_init(self, node: ast.Node | None) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.LocalVarDecl):
            init = self.emit_expr(node.init) if node.init is not None else "null"
            return f"${node.name} = {init}"
        if isinstance(node, ast.ExprStmt):
            return self.emit_expr(node.expr)
        return ""

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------

    def emit_expr(self, node: ast.Expr) -> str:
        if isinstance(node, ast.Literal):
            return self.emit_literal(node)
        if isinstance(node, ast.Name):
            return self.emit_name(node)
        if isinstance(node, ast.This):
            return "$this"
        if isinstance(node, ast.Super):
            self.error("'super' só pode ser usado em super(...) ou super.metodo(...)", node)
        if isinstance(node, ast.FieldAccess):
            return self.emit_field_access(node)
        if isinstance(node, ast.Call):
            return self.emit_call(node)
        if isinstance(node, ast.NewObject):
            if node.class_name in EXCEPTION_TYPES:
                args = ", ".join(self.emit_expr(arg) for arg in node.args)
                return f"new {self.php_exception_name(node.class_name)}({args})"
            if node.class_name in {"ArrayList", "List"}:
                return "new JArrayList()"
            if node.class_name in {"HashMap", "Map"}:
                return "new JHashMap()"
            if node.class_name in {"HashSet", "Set"}:
                return "new JHashSet()"
            if node.class_name == "Scanner":
                return "new JScanner()"
            args = ", ".join(self.emit_expr(arg) for arg in node.args)
            return f"new {self.php_class_name(node.class_name)}({args})"
        if isinstance(node, ast.NewArray):
            if node.init is not None:
                items = ", ".join(self.emit_expr(item) for item in node.init)
                return f"[{items}]"
            if node.size is None:
                self.error("array sem tamanho nem inicializador", node)
            size = self.emit_expr(node.size)
            return f"array_fill(0, {size}, {self.default_value(node.element_type)})"
        if isinstance(node, ast.ArrayAccess):
            array = self.emit_expr(node.array)
            index = self.emit_expr(node.index)
            return f"{self.wrap_member_target(array)}[{index}]"
        if isinstance(node, ast.Binary):
            return self.emit_binary(node)
        if isinstance(node, ast.Assign):
            return self.emit_assign(node)
        if isinstance(node, ast.Unary):
            return self.emit_unary(node)
        if isinstance(node, ast.Ternary):
            cond = self.emit_expr(node.cond)
            then = self.emit_expr(node.then)
            otherwise = self.emit_expr(node.else_)
            return f"({cond} ? {then} : {otherwise})"
        if isinstance(node, ast.SwitchExpression):
            return self.emit_switch_expression(node)
        if isinstance(node, ast.ClassLiteral):
            target = node.type
            if target.dims > 0:
                return 'JClass::of("array")'
            if target.name in self.classes:
                return f"JClass::of({self.php_class_name(target.name)}::class)"
            if target.name in EXCEPTION_TYPES:
                return f"JClass::of({self.php_exception_name(target.name)}::class)"
            return f'JClass::of("{target.name}")'
        if isinstance(node, ast.Cast):
            return self.emit_cast(node)
        if isinstance(node, ast.Lambda):
            if isinstance(node.body, ast.Block):
                self.error("lambda com bloco não suportada no gerador", node)
            params = ", ".join(f"${param}" for param in node.params)
            return f"fn({params}) => {self.emit_expr(node.body)}"
        if isinstance(node, ast.InstanceOf):
            return self.emit_instanceof(node)
        self.error("expressão não suportada pelo gerador", node)
        return ""

    def emit_literal(self, node: ast.Literal) -> str:
        if node.kind == "int":
            return str(node.value)
        if node.kind == "double":
            value = float(node.value)
            if value != value:
                return "NAN"
            if value == float("inf"):
                return "INF"
            if value == float("-inf"):
                return "-INF"
            text = repr(value)
            if "e" not in text and "E" not in text and "." not in text:
                text += ".0"
            return text
        if node.kind == "boolean":
            return "true" if node.value else "false"
        if node.kind == "null":
            return "null"
        if node.kind in {"string", "char"}:
            return self.php_string(str(node.value))
        self.error("literal não suportado", node)
        return "null"

    def emit_name(self, node: ast.Name) -> str:
        enum_owner = getattr(node, "enum_owner", None)
        if enum_owner:
            return f"{enum_owner}::{node.id}"
        binding = getattr(node, "binding", None)
        if binding is None:
            return f"${node.id}"
        kind = binding[0]
        if kind == "local":
            return f"${node.id}"
        if kind == "class":
            return node.id
        if kind == "field":
            _kind, owner, name, is_static = binding
            if is_static:
                owner_ref = "self" if owner == self.current_class else self.php_class_name(owner)
                return f"{owner_ref}::${name}"
            return f"$this->{name}"
        return f"${node.id}"

    def emit_field_access(self, node: ast.FieldAccess) -> str:
        if getattr(node, "is_length", False):
            return f"count({self.emit_expr(node.target)})"
        if getattr(node, "enum_constant", False):
            return f"{self.php_class_name(node.owner_class)}::{node.constant_name}"
        if getattr(node, "php_constant", None):
            return node.php_constant
        if isinstance(node.target, ast.Super):
            if getattr(node, "is_static_field", False):
                return f"parent::${node.name}"
            return f"$this->{node.name}"
        if getattr(node, "is_static_field", False):
            owner = getattr(node, "owner_class", None)
            owner_ref = "self" if owner == self.current_class else self.php_class_name(owner)
            return f"{owner_ref}::${node.name}"
        target = self.emit_expr(node.target)
        return f"{self.wrap_member_target(target)}->{node.name}"

    def emit_call(self, node: ast.Call) -> str:
        kind = getattr(node, "call_kind", None)
        method = getattr(node, "method_name", "")
        callee = node.callee

        if kind == "stream_collect" or kind == "stream_to_list":
            target = self.emit_expr(callee.target)
            return f"{self.wrap_member_target(target)}->toList()"

        args = ", ".join(self.emit_expr(arg) for arg in node.args)

        if kind == "system_out":
            return f"JSystem::{method}({args})"
        if kind == "exception_method":
            target = self.emit_expr(callee.target)
            t = self.wrap_member_target(target)
            if method in {"getMessage", "getLocalizedMessage"}:
                return f"{t}->getMessage()"
            if method == "getCode":
                return f"{t}->getCode()"
            if method == "printStackTrace":
                return f"fwrite(STDERR, (string) {t} . PHP_EOL)"
            if method == "toString":
                return f"(string) {t}"
            self.error(f"método de exceção '{method}' não suportado no gerador", node)
        if kind is not None and kind.startswith(("list_", "map_", "set_", "stream_")):
            target = self.emit_expr(callee.target)
            return f"{self.wrap_member_target(target)}->{method}({args})"
        if kind == "scanner":
            target = self.emit_expr(callee.target)
            return f"{self.wrap_member_target(target)}->{method}({args})"
        if kind == "class_method":
            target = self.emit_expr(callee.target)
            return f"{self.wrap_member_target(target)}->{method}({args})"
        if kind == "super_ctor":
            return f"parent::__construct({args})"
        if kind == "super_method":
            return f"parent::{method}({args})"
        if kind == "system_exit":
            return f"exit({args})"
        if kind == "string_valueof":
            return f"JString::valueOf({args})"
        if kind == "integer_parseint":
            return f"(int) ({args})"
        if kind == "integer_tostring":
            return f"(string) ({args})"
        if kind == "double_parsedouble":
            return f"(float) ({args})"
        if kind == "double_tostring":
            return f"JString::valueOf({args})"
        if kind == "string_method":
            return self.emit_string_method(node, method, args)
        if kind == "math":
            if method == "random":
                return "(mt_rand() / mt_getrandmax())"
            if method == "round":
                return f"(int) round({args})"
            if method in {"abs", "sqrt", "floor", "ceil", "min", "max"}:
                return f"{method}({args})"
            if method == "pow":
                return f"pow({args})"
            self.error(f"Math.{method} não suportado no gerador", node)
        if kind == "static":
            owner = getattr(node, "owner_class", None)
            return f"{self.php_class_name(owner)}::{method}({args})"
        if kind == "instance":
            target = self.emit_expr(callee.target)
            return f"{self.wrap_member_target(target)}->{method}({args})"
        if kind == "self_static":
            return f"self::{method}({args})"
        if kind == "self_instance":
            return f"$this->{method}({args})"

        self.error("chamada sem resolução semântica", node)
        return ""

    def emit_string_method(self, node: ast.Call, method: str, args: str) -> str:
        target = self.emit_expr(node.callee.target)
        if method == "length":
            return f"strlen({target})"
        if method == "charAt":
            return f"JString::charAt({target}, {args})"
        if method == "substring":
            return f"JString::substring({target}, {args})"
        if method == "equals":
            return f"({target} === {args})"
        if method == "equalsIgnoreCase":
            return f"(strcasecmp({target}, {args}) === 0)"
        if method == "toUpperCase":
            return f"strtoupper({target})"
        if method == "toLowerCase":
            return f"strtolower({target})"
        if method == "trim":
            return f"trim({target})"
        if method == "indexOf":
            return f"JString::indexOf({target}, {args})"
        if method == "isEmpty":
            return f"({target} === '')"
        if method == "contains":
            return f"str_contains({target}, {args})"
        if method == "startsWith":
            return f"str_starts_with({target}, {args})"
        if method == "endsWith":
            return f"str_ends_with({target}, {args})"
        if method == "replace":
            first, second = self.split_args(args)
            return f"str_replace({first}, {second}, {target})"
        if method == "split":
            return f"JString::split({target}, {args})"
        if method == "toString":
            return target
        if method == "compareTo":
            return f"strcmp({target}, {args})"
        self.error(f"método String.{method} não suportado no gerador", node)
        return ""

    def split_args(self, args: str) -> tuple[str, str]:
        depth = 0
        in_string = False
        quote = ""
        escaped = False
        for i, char in enumerate(args):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    in_string = False
                continue
            if char in {'"', "'"}:
                in_string = True
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0:
                return args[:i].strip(), args[i + 1 :].strip()
        return args.strip(), ""

    def php_class_ref(self, name: str) -> str:
        return self.php_class_name(name)

    def emit_cast(self, node: ast.Cast) -> str:
        target = node.type
        source = getattr(node.expr, "inferred_type", None)
        expr = self.emit_expr(node.expr)

        if target.dims > 0:
            return f"JCast::toArray({expr})"
        if target.name == "String":
            return f"JCast::toString({expr})"
        if target.name == "char":
            numeric = f"ord({expr})" if source is not None and source.name == "char" else expr
            return f"chr((int) ({numeric}))"
        if target.name == "int":
            if source is not None and source.name == "char":
                return f"ord({expr})"
            return f"((int) ({expr}))"
        if target.name == "double":
            if source is not None and source.name == "char":
                return f"((float) ord({expr}))"
            return f"((float) ({expr}))"
        if target.name in self.classes or target.name in EXCEPTION_TYPES:
            return f"JCast::to({expr}, {self.php_class_ref(target.name)}::class)"
        self.error(f"cast não suportado no gerador: {target}", node)
        return ""

    def emit_instanceof(self, node: ast.InstanceOf) -> str:
        target = node.type
        expr = self.emit_expr(node.expr)
        binding = getattr(node, "binding", None)
        variable = f"${binding}" if binding else None

        if target.dims > 0:
            if variable:
                return f"(({variable} = {expr}) !== null && is_array({variable}))"
            return f"is_array({expr})"
        if target.name == "String":
            if variable:
                return f"(({variable} = {expr}) !== null && is_string({variable}))"
            return f"is_string({expr})"
        if target.name in self.classes or target.name in EXCEPTION_TYPES:
            class_ref = self.php_class_ref(target.name)
            if variable:
                return f"(({variable} = {expr}) instanceof {class_ref})"
            return f"({expr} instanceof {class_ref})"
        self.error(f"instanceof não suportado no gerador: {target}", node)
        return ""

    def emit_binary(self, node: ast.Binary) -> str:
        left = self.emit_expr(node.left)
        right = self.emit_expr(node.right)
        left_type = getattr(node.left, "inferred_type", None)
        right_type = getattr(node.right, "inferred_type", None)
        result_type = getattr(node, "inferred_type", None)

        if node.op == "+" and result_type is not None and result_type.name == "String" and result_type.dims == 0:
            return f"JString::concat({left}, {right})"

        left_num = self.emit_numeric_operand(node.left, left)
        right_num = self.emit_numeric_operand(node.right, right)

        if node.op == "/":
            if (
                left_type is not None
                and right_type is not None
                and left_type.dims == 0
                and right_type.dims == 0
                and left_type.name in {"int", "char"}
                and right_type.name in {"int", "char"}
            ):
                return f"intdiv({left_num}, {right_num})"
            return f"({left_num} / {right_num})"

        if node.op == "%":
            if (
                left_type is not None
                and right_type is not None
                and left_type.dims == 0
                and right_type.dims == 0
                and (left_type.name == "double" or right_type.name == "double")
            ):
                return f"fmod({left_num}, {right_num})"
            return f"({left_num} % {right_num})"

        if node.op in {"==", "!="}:
            php_op = "===" if node.op == "==" else "!=="
            if left_type is not None and right_type is not None:
                if self.is_numeric_type(left_type) and self.is_numeric_type(right_type):
                    php_op = "==" if node.op == "==" else "!="
                elif left_type.name == "boolean" and right_type.name == "boolean":
                    php_op = "===" if node.op == "==" else "!=="
            return f"({left} {php_op} {right})"

        return f"({left_num} {node.op} {right_num})"

    def emit_assign(self, node: ast.Assign) -> str:
        target = self.emit_expr(node.target)
        value = self.emit_expr(node.value)
        target_type = getattr(node.target, "inferred_type", None)
        if node.op == "+=" and target_type is not None and target_type.name == "String":
            return f"{target} = JString::concat({target}, {value})"
        return f"{target} {node.op} {value}"

    def emit_unary(self, node: ast.Unary) -> str:
        operand = self.emit_expr(node.operand)
        operand_type = getattr(node.operand, "inferred_type", None)
        if node.op in {"-", "+"} and operand_type is not None and operand_type.name == "char":
            operand = f"ord({operand})"
        if node.prefix:
            return f"{node.op}{operand}"
        return f"{operand}{node.op}"

    def emit_numeric_operand(self, expr: ast.Expr, text: str) -> str:
        t = getattr(expr, "inferred_type", None)
        if t is not None and t.dims == 0 and t.name == "char":
            return f"ord({text})"
        return text

    def is_numeric_type(self, t: ast.JavaType) -> bool:
        return t.dims == 0 and t.name in {"int", "double", "char"}

    def wrap_member_target(self, text: str) -> str:
        # $obj->x, $a[$i], $this->m() já são expressões válidas para ->.
        if text.startswith("$"):
            return text
        return f"({text})"

    # ------------------------------------------------------------------
    # Strings PHP
    # ------------------------------------------------------------------

    def php_string(self, value: str) -> str:
        out = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
            .replace("\0", "\\0")
        )
        return f'"{out}"'
