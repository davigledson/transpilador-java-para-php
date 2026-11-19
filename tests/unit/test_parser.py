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


def test_syntax_error_has_position() -> None:
    with pytest.raises(TranspileError) as exc:
        parse("class A { void m( { }")
    assert exc.value.line >= 1
    assert exc.value.col >= 1
