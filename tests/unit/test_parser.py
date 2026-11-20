import pytest

from transpilador import ast
from transpilador.erros import TranspileError
from transpilador.lexer import JavaLexer, collect_type_names
from transpilador.parser import JavaParser


def parse(source: str) -> ast.Program:
    lexer = JavaLexer(collect_type_names(source))
    return JavaParser().parse(source, lexer)


def test_class_members() -> None:
    program = parse(
        """
        public class A {
            int x = 1;
            A() { this.x = 0; }
            int soma(int a, int b) { return a + b; }
        }
        """
    )
    cls = program.classes[0]
    assert cls.name == "A"
    assert [type(member).__name__ for member in cls.members] == [
        "FieldDecl",
        "ConstructorDecl",
        "MethodDecl",
    ]


def test_array_access_is_not_confused_with_array_type() -> None:
    program = parse(
        """
        class A {
            void m() {
                int[] a = new int[2];
                a[0] = 1;
            }
        }
        """
    )
    method = program.classes[0].members[0]
    local = method.body.stmts[0]
    assign = method.body.stmts[1]
    assert isinstance(local, ast.LocalVarDecl)
    assert local.type.dims == 1
    assert isinstance(assign.expr.target, ast.ArrayAccess)


def test_for_each() -> None:
    program = parse(
        """
        class A {
            void m() {
                int[] a = new int[2];
                for (int x : a) { }
            }
        }
        """
    )
    stmt = program.classes[0].members[0].body.stmts[1]
    assert isinstance(stmt, ast.ForEach)
    assert stmt.name == "x"


def test_do_while() -> None:
    program = parse(
        """
        class A {
            void m() {
                int x = 0;
                do { x++; } while (x < 3);
            }
        }
        """
    )
    stmt = program.classes[0].members[0].body.stmts[1]
    assert isinstance(stmt, ast.DoWhile)


def test_inheritance_and_super_syntax() -> None:
    program = parse(
        """
        class A { }
        class B extends A {
            B() { super(); }
            void m() { super.m(); }
        }
        """
    )
    cls = program.classes[1]
    assert cls.extends == "A"
    ctor = cls.members[0]
    assert isinstance(ctor.body.stmts[0].expr.callee, ast.Super)
    method = cls.members[1]
    call = method.body.stmts[0].expr
    assert isinstance(call.callee, ast.FieldAccess)
    assert isinstance(call.callee.target, ast.Super)
    assert call.callee.name == "m"


def test_interface_and_abstract_method_syntax() -> None:
    program = parse(
        """
        interface I { int f(); }
        abstract class A implements I {
            abstract int g();
        }
        """
    )
    iface = program.classes[0]
    assert iface.is_interface
    assert iface.members[0].body is None

    abstract = program.classes[1]
    assert "abstract" in abstract.modifiers
    assert abstract.implements == ["I"]
    assert abstract.members[0].body is None


def test_generics_and_arraylist_syntax() -> None:
    program = parse(
        """
        class A {
            void m() {
                List<String> nomes = new ArrayList<>();
                nomes.add("Ana");
            }
        }
        """
    )
    local = program.classes[0].members[0].body.stmts[0]
    assert local.type.name == "List"
    assert local.type.args == (ast.STRING,)
    assert local.init.class_name == "ArrayList"
    assert local.init.type_args == ()


def test_map_and_set_syntax() -> None:
    program = parse(
        """
        class A {
            void m() {
                Map<String, Conta> mapa = new HashMap<>();
                Set<String> nomes = new HashSet<>();
            }
        }
        class Conta { }
        """
    )
    mapa = program.classes[0].members[0].body.stmts[0]
    nomes = program.classes[0].members[0].body.stmts[1]
    assert mapa.type.name == "Map"
    assert mapa.type.args == (ast.STRING, ast.JavaType("Conta"))
    assert mapa.init.class_name == "HashMap"
    assert nomes.type.name == "Set"
    assert nomes.type.args == (ast.STRING,)
    assert nomes.init.class_name == "HashSet"


def test_try_catch_finally_and_throw_syntax() -> None:
    program = parse(
        """
        class A {
            void m() throws RuntimeException {
                try {
                    throw new RuntimeException("x");
                } catch (RuntimeException e) {
                    System.out.println(e.getMessage());
                } finally {
                    System.out.println("fim");
                }
            }
        }
        """
    )
    stmt = program.classes[0].members[0].body.stmts[0]
    assert isinstance(stmt, ast.Try)
    assert len(stmt.catches) == 1
    assert stmt.catches[0].type.name == "RuntimeException"
    assert stmt.catches[0].name == "e"
    assert stmt.finally_ is not None
    assert isinstance(stmt.body.stmts[0], ast.Throw)


def test_record_syntax() -> None:
    program = parse(
        """
        record Ponto(int x, int y) implements Rotulo {
            public int soma() { return x + y; }
        }
        record Vazio() { }
        interface Rotulo { int soma(); }
        """
    )
    ponto = program.classes[0]
    assert ponto.is_record
    assert [component.name for component in ponto.components] == ["x", "y"]
    assert ponto.implements == ["Rotulo"]
    assert isinstance(ponto.members[0], ast.MethodDecl)
    assert program.classes[1].is_record
    assert program.classes[1].components == []


def test_try_with_resources_syntax() -> None:
    program = parse(
        """
        class A {
            void m() {
                try (Recurso r = new Recurso();
                     var s = new Recurso();) {
                    System.out.println(r);
                }
            }
        }
        class Recurso implements AutoCloseable {
            public void close() { }
        }
        """
    )
    stmt = program.classes[0].members[0].body.stmts[0]
    assert isinstance(stmt, ast.Try)
    assert [resource.name for resource in stmt.resources] == ["r", "s"]
    assert stmt.resources[0].type.name == "Recurso"
    assert stmt.resources[1].type is None


def test_multi_catch_syntax() -> None:
    program = parse(
        """
        class A {
            void m() {
                try {
                    System.out.println("x");
                } catch (RuntimeException | Error e) {
                    System.out.println(e.getMessage());
                }
            }
        }
        """
    )
    stmt = program.classes[0].members[0].body.stmts[0]
    assert isinstance(stmt, ast.Try)
    assert [t.name for t in stmt.catches[0].types] == ["RuntimeException", "Error"]
    assert stmt.catches[0].name == "e"


def test_switch_syntax() -> None:
    program = parse(
        """
        class A {
            void m(int x) {
                switch (x) {
                    case 1:
                        break;
                    case 2:
                    case 3:
                        break;
                    default:
                        break;
                }
            }
        }
        """
    )
    stmt = program.classes[0].members[0].body.stmts[0]
    assert isinstance(stmt, ast.Switch)
    assert len(stmt.cases) == 4
    assert isinstance(stmt.cases[0].value, ast.Literal)
    assert stmt.cases[1].stmts == []
    assert stmt.cases[3].value is None


def test_enum_syntax() -> None:
    program = parse(
        """
        enum Status {
            ATIVO,
            BLOQUEADO
        }
        class A {
            void m() {
                Status s = Status.ATIVO;
            }
        }
        """
    )
    enum = program.classes[0]
    assert enum.is_enum
    assert enum.enum_constants == ["ATIVO", "BLOQUEADO"]
    local = program.classes[1].members[0].body.stmts[0]
    assert local.type.name == "Status"
    assert isinstance(local.init, ast.FieldAccess)


def test_lambda_syntax() -> None:
    program = parse(
        """
        class A {
            void m() {
                List<String> nomes = new ArrayList<>();
                nomes.forEach(n -> System.out.println(n));
                nomes.stream().filter(n -> n.length() > 2);
            }
        }
        """
    )
    stmts = program.classes[0].members[0].body.stmts
    for_each = stmts[1].expr
    assert isinstance(for_each.args[0], ast.Lambda)
    assert for_each.args[0].params == ["n"]
    stream = stmts[2].expr
    assert isinstance(stream.callee, ast.FieldAccess)
    assert stream.callee.name == "filter"
    assert isinstance(stream.args[0], ast.Lambda)


def test_annotations_with_arguments_are_ignored() -> None:
    program = parse(
        """
        class A {
            @SuppressWarnings({"unchecked", "rawtypes"})
            @Deprecated(since = "9", forRemoval = false)
            int valor = 1;
        }
        """
    )
    field = program.classes[0].members[0]
    assert field.name == "valor"
    assert field.init.value == 1


def test_cast_and_instanceof_syntax() -> None:
    program = parse(
        """
        class A {
            void m(A o) {
                int x = (int) 3.9;
                boolean b = o instanceof A;
                A a = (A) o;
            }
        }
        """
    )
    stmts = program.classes[0].members[0].body.stmts
    assert isinstance(stmts[0].init, ast.Cast)
    assert isinstance(stmts[1].init, ast.InstanceOf)
    assert isinstance(stmts[2].init, ast.Cast)


def test_class_literal_syntax() -> None:
    program = parse(
        """
        class Conta { }
        class A {
            void m() {
                Class c = Conta.class;
                Class i = int.class;
                Class s = String.class;
            }
        }
        """
    )
    stmts = program.classes[1].members[0].body.stmts
    assert all(isinstance(stmt.init, ast.ClassLiteral) for stmt in stmts)


def test_package_and_imports_syntax() -> None:
    program = parse(
        """
        package app;
        import java.util.ArrayList;
        import model.Conta;
        class Main {
            void m() {
                Conta c = new Conta();
            }
        }
        class Conta { }
        """
    )
    assert program.package == "app"
    assert "java.util.ArrayList" in program.imports
    assert "model.Conta" in program.imports
    assert program.classes[0].package == "app"
    assert "model.Conta" in program.classes[0].imports


def test_var_syntax() -> None:
    program = parse(
        """
        class A {
            void m() {
                var x = 1;
                for (var i = 0; i < 3; i++) { }
                for (var s : new String[2]) { }
            }
        }
        """
    )
    stmts = program.classes[0].members[0].body.stmts
    assert isinstance(stmts[0], ast.LocalVarDecl)
    assert stmts[0].type is None
    for_stmt = stmts[1]
    assert isinstance(for_stmt, ast.For)
    assert isinstance(for_stmt.init, ast.LocalVarDecl)
    assert for_stmt.init.type is None
    each = stmts[2]
    assert isinstance(each, ast.ForEach)
    assert each.type is None


def test_switch_arrow_and_expression_syntax() -> None:
    program = parse(
        """
        class A {
            void m(int x) {
                switch (x) {
                    case 1 -> System.out.println("um");
                    default -> System.out.println("outro");
                }
                String s = switch (x) {
                    case 1 -> "um";
                    default -> {
                        yield "outro";
                    }
                };
            }
        }
        """
    )
    stmts = program.classes[0].members[0].body.stmts
    switch_stmt = stmts[0]
    assert isinstance(switch_stmt, ast.Switch)
    assert switch_stmt.cases[0].arrow
    assert isinstance(switch_stmt.cases[0].arrow_body, ast.Expr)
    assert isinstance(stmts[1].init, ast.SwitchExpression)
    assert isinstance(stmts[1].init.cases[1].arrow_body, ast.Block)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("public @interface Foo { }", "@interface"),
        ("sealed class A { }", "sealed"),
    ],
)
def test_unsupported_java21_diagnostics(source: str, message: str) -> None:
    with pytest.raises(TranspileError, match=message):
        parse(source)


def test_pattern_instanceof_syntax() -> None:
    program = parse(
        """
        class A {
            void m(A o) {
                if (o instanceof A a) {
                    System.out.println(a);
                }
                if (o instanceof A b && b != null) {
                    System.out.println(b);
                }
            }
        }
        """
    )
    stmts = program.classes[0].members[0].body.stmts
    first = stmts[0].cond
    assert isinstance(first, ast.InstanceOf)
    assert first.binding == "a"
    second = stmts[1].cond
    assert isinstance(second, ast.Binary)
    assert isinstance(second.left, ast.InstanceOf)
    assert second.left.binding == "b"


def test_syntax_error_has_position() -> None:
    with pytest.raises(TranspileError) as exc:
        parse("class A { void m( { }")
    assert exc.value.line >= 1
    assert exc.value.col >= 1
