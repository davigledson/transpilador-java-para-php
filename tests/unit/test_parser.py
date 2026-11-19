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


def test_syntax_error_has_position() -> None:
    with pytest.raises(TranspileError) as exc:
        parse("class A { void m( { }")
    assert exc.value.line >= 1
    assert exc.value.col >= 1
