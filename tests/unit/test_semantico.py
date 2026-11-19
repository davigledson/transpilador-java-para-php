import pytest

from transpilador import ast
from transpilador.erros import TranspileError
from transpilador.lexer import JavaLexer, collect_type_names
from transpilador.parser import JavaParser
from transpilador.semantico import SemanticAnalyzer


def analyze(source: str) -> tuple[ast.Program, SemanticAnalyzer]:
    lexer = JavaLexer(collect_type_names(source))
    program = JavaParser().parse(source, lexer)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    return program, analyzer


def test_valid_program_and_main() -> None:
    _program, analyzer = analyze(
        """
        public class A {
            private String nome;
            A(String nome) { this.nome = nome; }
            public static void main(String[] args) {
                A a = new A("x");
                System.out.println(a.nome);
            }
        }
        """
    )
    assert "A" in analyzer.classes
    assert analyzer.classes["A"].has_main
    assert analyzer.classes["A"].fields["nome"].type == ast.STRING


def test_undefined_variable() -> None:
    with pytest.raises(TranspileError, match="símbolo não encontrado"):
        analyze(
            """
            class A {
                void m() { x = 1; }
            }
            """
        )


def test_type_mismatch() -> None:
    with pytest.raises(TranspileError, match="inicializar"):
        analyze(
            """
            class A {
                void m() { String s = 1; }
            }
            """
        )


def test_invalid_main_signature() -> None:
    with pytest.raises(TranspileError, match="main"):
        analyze(
            """
            class A {
                public static void main() { }
            }
            """
        )


def test_instance_call_from_static_is_allowed_with_object() -> None:
    analyze(
        """
        class A {
            void m() { }
            public static void main(String[] args) {
                A a = new A();
                a.m();
            }
        }
        """
    )


def test_int_division_and_string_concat_types() -> None:
    program, _analyzer = analyze(
        """
        class A {
            public static void main(String[] args) {
                int x = 7 / 2;
                System.out.println("x=" + x);
            }
        }
        """
    )
    method = program.classes[0].members[0]
    division = method.body.stmts[0].init
    concat = method.body.stmts[1].expr.args[0]
    assert division.inferred_type == ast.INT
    assert concat.inferred_type == ast.STRING
